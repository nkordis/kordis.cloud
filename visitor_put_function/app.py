import hashlib
import json
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch the supported libraries (e.g., boto3) to enable tracing
patch_all()

TABLE_NAME = os.environ.get('TABLE_NAME', 'kordis-cloud')
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.environ.get('ALLOWED_ORIGINS', 'https://kordis.cloud,https://www.kordis.cloud').split(',')
    if origin.strip()
}
# A visitor (same IP and User-Agent) is counted at most once per UTC day.
# The marker item expires through DynamoDB TTL, so the hash is kept for at most two days.
DEDUP_TTL_SECONDS = 2 * 24 * 60 * 60

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')


def get_header(event, name):
    headers = event.get('headers') or {}
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.title())


def cors_headers(event):
    """Allow only the portfolio origins; other sites get no CORS header."""
    headers = {'Vary': 'Origin'}
    origin = get_header(event, 'origin')
    if origin in ALLOWED_ORIGINS:
        headers['Access-Control-Allow-Origin'] = origin
        headers['Access-Control-Allow-Methods'] = 'GET,PUT,OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type'
        headers['Access-Control-Max-Age'] = '86400'
    return headers


def visitor_key(event):
    """Daily visitor id (SHA-256 of day, IP and User-Agent); the raw values are never stored or logged."""
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', '')
    user_agent = get_header(event, 'User-Agent') or ''
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    digest = hashlib.sha256(f"{day}|{source_ip}|{user_agent}".encode()).hexdigest()
    return f"visitor#{digest}"


def is_duplicate_visit(error):
    """True only when the transaction was cancelled by the visitor marker's condition."""
    if error.response['Error']['Code'] != 'TransactionCanceledException':
        return False
    reasons = error.response.get('CancellationReasons') or []
    return bool(reasons) and reasons[0].get('Code') == 'ConditionalCheckFailed'


def response(status_code, headers, body):
    return {'statusCode': status_code, 'headers': headers, 'body': json.dumps(body)}


@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):
    headers = cors_headers(event)

    # CORS preflight for the PUT below
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 204, 'headers': headers, 'body': ''}

    table = dynamodb.Table(TABLE_NAME)
    client = table.meta.client

    try:
        with xray_recorder.capture('put_item'):
            # Record the visitor marker and increment the counter atomically;
            # the marker condition fails for a visitor already counted today.
            client.transact_write_items(
                TransactItems=[
                    {
                        'Put': {
                            'TableName': TABLE_NAME,
                            'Item': {
                                'id': visitor_key(event),
                                'expiresAt': int(time.time()) + DEDUP_TTL_SECONDS,
                            },
                            'ConditionExpression': 'attribute_not_exists(id)',
                        }
                    },
                    {
                        'Update': {
                            'TableName': TABLE_NAME,
                            'Key': {'id': 'visits'},
                            'UpdateExpression': 'SET visitsCount = if_not_exists(visitsCount, :start) + :inc',
                            'ExpressionAttributeValues': {':inc': 1, ':start': 0},
                        }
                    },
                ]
            )
        counted = True
    except ClientError as e:
        if not is_duplicate_visit(e):
            print(f"An error occurred: {e.response['Error']['Code']}")
            return response(500, headers, {"message": "AWS service error"})
        counted = False

    try:
        with xray_recorder.capture('get_item'):
            item = table.get_item(Key={'id': 'visits'}, ConsistentRead=True).get('Item', {})
    except ClientError as e:
        print(f"An error occurred: {e.response['Error']['Code']}")
        return response(500, headers, {"message": "AWS service error"})

    message = "Updated visit count" if counted else "Visit already counted today"
    return response(200, headers, {"message": message, "visitsCount": int(item.get('visitsCount', 0)), "counted": counted})
