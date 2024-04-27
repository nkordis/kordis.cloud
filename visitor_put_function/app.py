import boto3
from botocore.exceptions import ClientError
import json
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch the supported libraries (e.g., boto3) to enable tracing
patch_all()

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')
@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):

    # Capture log event information for monitoring and analysis
    source_ip = event['requestContext']['identity']['sourceIp']
    user_agent = event.get('headers', {}).get('User-Agent', 'Unknown User-Agent')
    # Print these details to CloudWatch Logs
    print(f"Source IP: {source_ip}, User-Agent: {user_agent}")

    # Specify the DynamoDB table
    table = dynamodb.Table('kordis-cloud')

    try:
        with xray_recorder.capture('put_item'):
        # Attempt to update the item in the table
            response = table.update_item(
                Key={
                    'id': 'visits'
                },
                UpdateExpression='SET visitsCount = if_not_exists(visitsCount, :start) + :inc',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':start': 0
                },
                ReturnValues='UPDATED_NEW'
            )
            # Return the updated value
        return {
            'statusCode': 200,
            "headers": {
            "Access-Control-Allow-Origin": "*",  
            "Access-Control-Allow-Methods": "PUT,OPTIONS",  
            "Access-Control-Allow-Headers": "Content-Type"  
            },
            'body': json.dumps({"message": "Updated visit count", "visitsCount": int(response['Attributes']['visitsCount'])})
        }
    except ClientError as e:
        # Handle potential errors
        print(e.response['Error']['Message'])
        return {
            'statusCode': 500,
            "headers": {
            "Access-Control-Allow-Origin": "*",  
            "Access-Control-Allow-Methods": "PUT,OPTIONS",  
            "Access-Control-Allow-Headers": "Content-Type"  
            },
            'body': json.dumps({"message": "AWS service error"})
        }


