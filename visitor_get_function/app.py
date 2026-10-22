import json
import os

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

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')


def cors_headers(event):
    """Allow only the portfolio origins; other sites get no CORS header."""
    headers = {'Vary': 'Origin'}
    origin = (event.get('headers') or {}).get('origin') or (event.get('headers') or {}).get('Origin')
    if origin in ALLOWED_ORIGINS:
        headers['Access-Control-Allow-Origin'] = origin
    return headers


@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    headers = cors_headers(event)

    try:
        with xray_recorder.capture('get_item'):
            response = table.get_item(Key={'id': 'visits'})
        # Check if the item was found
        if 'Item' in response:
            visit_count = int(response['Item'].get('visitsCount', 0))
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({"message": "Success", "visitsCount": visit_count})
            }
        # If the item is not found, return a message indicating no visits are recorded
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({"message": "No visits recorded yet"})
        }
    except ClientError as e:
        print(f"An error occurred: {e.response['Error']['Code']}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"message": "AWS service error"})
        }
