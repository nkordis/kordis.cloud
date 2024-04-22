import boto3
from botocore.exceptions import ClientError
import json

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Specify the DynamoDB table
    table = dynamodb.Table('kordis-cloud')

    try:
        # Attempt to retrieve the item from the table
        response = table.get_item(
            Key={'id': 'visits'}
        )
        # Check if the item was found
        if 'Item' in response:
            visit_count = int(response['Item'].get('visitsCount', 0))
            return {
                'statusCode': 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",  
                    "Access-Control-Allow-Methods": "GET,OPTIONS",  
                    "Access-Control-Allow-Headers": "Content-Type" 
                },
                'body': json.dumps({"message": "Success", "visitsCount": visit_count})
            }
        else:
            # If the item is not found, return a message indicating no visits are recorded
            return {
                'statusCode': 404,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,OPTIONS",  
                    "Access-Control-Allow-Headers": "Content-Type"  
                },
                'body': json.dumps({"message": "No visits recorded yet"})
            }
    except ClientError as e:
        # Handle potential errors
        print(f"An error occurred: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            "headers": {
            "Access-Control-Allow-Origin": "*",  
            "Access-Control-Allow-Methods": "GET,OPTIONS",  
            "Access-Control-Allow-Headers": "Content-Type"  
            },
            'body': json.dumps({"message": "AWS service error"})
        } 
