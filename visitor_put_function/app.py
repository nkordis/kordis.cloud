import boto3
from botocore.exceptions import ClientError
import json

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')
def lambda_handler(event, context):
    # Specify the DynamoDB table
    table = dynamodb.Table('kordis-cloud')

    try:
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


