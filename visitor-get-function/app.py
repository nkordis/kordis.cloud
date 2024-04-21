import json

def lambda_handler(event, context):
    # Hardcoded count value
    count = 2

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",  
            "Access-Control-Allow-Methods": "GET,OPTIONS",  
            "Access-Control-Allow-Headers": "Content-Type"  
        },
        "body": json.dumps({
            "count": count
        }),
    }

