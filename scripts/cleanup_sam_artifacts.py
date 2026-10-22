"""Remove obsolete SAM deployment artifacts from the SAM-managed S3 bucket.

Keeps every artifact the deployed stack still references, plus anything uploaded in
the last KEEP_DAYS days (so recent rollbacks still work). Older, unreferenced
packages are deleted. Because the managed bucket is versioned, a lifecycle rule is
also ensured that expires the deleted (noncurrent) versions after a few days.

Usage: python scripts/cleanup_sam_artifacts.py [--stack kordis-cloud] [--prefix kordis-cloud] [--dry-run]
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone

import boto3

KEEP_DAYS = 30
NONCURRENT_DAYS = 7
LIFECYCLE_RULE_ID = 'kordis-cloud-expire-old-sam-artifacts'
MANAGED_STACK = 'aws-sam-cli-managed-default'


def managed_bucket(cloudformation):
    stack = cloudformation.describe_stacks(StackName=MANAGED_STACK)['Stacks'][0]
    for output in stack.get('Outputs', []):
        if output['OutputKey'] == 'SourceBucket':
            return output['OutputValue']
    raise RuntimeError(f'No SourceBucket output on {MANAGED_STACK}')


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def referenced_keys(cloudformation, stack_name, bucket):
    """S3 keys in the managed bucket that the deployed stack still points at."""
    keys = set()
    # Original stage: the packaged SAM template, with CodeUri: s3://bucket/key
    original = cloudformation.get_template(StackName=stack_name, TemplateStage='Original')['TemplateBody']
    text = original if isinstance(original, str) else json.dumps(original)
    keys.update(re.findall(rf's3://{re.escape(bucket)}/([^\s"\',}}]+)', text))
    # Processed stage: plain CloudFormation, with Code: {S3Bucket, S3Key}
    processed = cloudformation.get_template(StackName=stack_name, TemplateStage='Processed')['TemplateBody']
    if isinstance(processed, str):
        processed = json.loads(processed)
    for node in _walk(processed):
        if node.get('S3Bucket') == bucket and isinstance(node.get('S3Key'), str):
            keys.add(node['S3Key'])
    return keys


def ensure_lifecycle_rule(s3, bucket, prefix, dry_run):
    try:
        rules = s3.get_bucket_lifecycle_configuration(Bucket=bucket)['Rules']
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchLifecycleConfiguration':
            raise
        rules = []
    if any(rule.get('ID') == LIFECYCLE_RULE_ID for rule in rules):
        return False
    rules.append({
        'ID': LIFECYCLE_RULE_ID,
        'Filter': {'Prefix': f'{prefix}/'},
        'Status': 'Enabled',
        'NoncurrentVersionExpiration': {'NoncurrentDays': NONCURRENT_DAYS},
        'Expiration': {'ExpiredObjectDeleteMarker': True},
        'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1},
    })
    if not dry_run:
        s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={'Rules': rules})
    return True


def obsolete_keys(s3, bucket, prefix, keep, now):
    cutoff = now - timedelta(days=KEEP_DAYS)
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=f'{prefix}/'):
        for obj in page.get('Contents', []):
            if obj['Key'] not in keep and obj['LastModified'] < cutoff:
                yield obj['Key']


def cleanup(stack_name, prefix, dry_run=False, session=None, now=None):
    session = session or boto3.session.Session()
    cloudformation = session.client('cloudformation')
    s3 = session.client('s3')
    now = now or datetime.now(timezone.utc)

    bucket = managed_bucket(cloudformation)
    keep = referenced_keys(cloudformation, stack_name, bucket)
    if not keep:
        # Never delete anything if the deployed template could not be matched to the bucket
        raise RuntimeError(f'No artifacts of {stack_name} found in {bucket}; refusing to clean up')

    added_rule = ensure_lifecycle_rule(s3, bucket, prefix, dry_run)
    doomed = list(obsolete_keys(s3, bucket, prefix, keep, now))
    if not dry_run:
        for start in range(0, len(doomed), 1000):
            batch = doomed[start:start + 1000]
            s3.delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': key} for key in batch], 'Quiet': True})

    action = 'Would delete' if dry_run else 'Deleted'
    print(f'{bucket}: kept {len(keep)} referenced artifact(s); {action} {len(doomed)} obsolete artifact(s)'
          f'{"; added lifecycle rule" if added_rule else ""}')
    return doomed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--stack', default='kordis-cloud')
    parser.add_argument('--prefix', default='kordis-cloud')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    cleanup(args.stack, args.prefix, args.dry_run)


if __name__ == '__main__':
    main()
