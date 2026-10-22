import json
from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

from scripts import cleanup_sam_artifacts as cleanup_script

BUCKET = 'aws-sam-cli-managed-default-samclisourcebucket-test'
CURRENT_KEY = 'kordis-cloud/current-code-hash'


class FakeCloudFormation:
    """Stands in for the two stacks the script reads."""

    def __init__(self, original):
        self.original = original

    def describe_stacks(self, StackName):
        return {'Stacks': [{'Outputs': [{'OutputKey': 'SourceBucket', 'OutputValue': BUCKET}]}]}

    def get_template(self, StackName, TemplateStage):
        if TemplateStage == 'Original':
            return {'TemplateBody': self.original}
        return {'TemplateBody': {'Resources': {'Fn': {'Properties': {'Code': {'S3Bucket': BUCKET, 'S3Key': CURRENT_KEY}}}}}}


class FakeSession:
    def __init__(self, cloudformation):
        self.cloudformation = cloudformation

    def client(self, name):
        return self.cloudformation if name == 'cloudformation' else boto3.client('s3', region_name='us-east-1')


@pytest.fixture()
def bucket():
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=BUCKET)
        s3.put_bucket_versioning(Bucket=BUCKET, VersioningConfiguration={'Status': 'Enabled'})
        for key in (CURRENT_KEY, 'kordis-cloud/old-code-hash', 'kordis-cloud/old.template', 'other-project/old'):
            s3.put_object(Bucket=BUCKET, Key=key, Body=b'x')
        yield s3


def run(dry_run=False, original=f'CodeUri: s3://{BUCKET}/{CURRENT_KEY}\n', days_later=31):
    session = FakeSession(FakeCloudFormation(original))
    now = datetime.now(timezone.utc) + timedelta(days=days_later)
    return cleanup_script.cleanup('kordis-cloud', 'kordis-cloud', dry_run=dry_run, session=session, now=now)


def keys(s3):
    return {obj['Key'] for obj in s3.list_objects_v2(Bucket=BUCKET).get('Contents', [])}


def test_deletes_only_old_unreferenced_artifacts_under_prefix(bucket):
    deleted = run()

    assert sorted(deleted) == ['kordis-cloud/old-code-hash', 'kordis-cloud/old.template']
    assert keys(bucket) == {CURRENT_KEY, 'other-project/old'}


def test_keeps_recent_artifacts_for_rollback(bucket):
    assert run(days_later=0) == []
    assert len(keys(bucket)) == 4


def test_dry_run_changes_nothing(bucket):
    assert len(run(dry_run=True)) == 2
    assert len(keys(bucket)) == 4
    with pytest.raises(bucket.exceptions.ClientError):
        bucket.get_bucket_lifecycle_configuration(Bucket=BUCKET)


def test_adds_lifecycle_rule_once(bucket):
    run()
    run()
    rules = bucket.get_bucket_lifecycle_configuration(Bucket=BUCKET)['Rules']

    assert [rule['ID'] for rule in rules] == [cleanup_script.LIFECYCLE_RULE_ID]
    assert rules[0]['NoncurrentVersionExpiration']['NoncurrentDays'] == cleanup_script.NONCURRENT_DAYS


def test_refuses_when_nothing_is_referenced(bucket):
    session = FakeSession(FakeCloudFormation('CodeUri: s3://some-other-bucket/key\n'))
    session.cloudformation.get_template = lambda StackName, TemplateStage: {'TemplateBody': json.dumps({})}

    with pytest.raises(RuntimeError):
        cleanup_script.cleanup('kordis-cloud', 'kordis-cloud', session=session)
    assert len(keys(bucket)) == 4
