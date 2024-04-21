import json

def lambda_handler(event, context):

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",  
            "Access-Control-Allow-Methods": "PUT,OPTIONS",  
            "Access-Control-Allow-Headers": "Content-Type"  
        },
        'body': json.dumps({
            'message': 'PUT request received'
        })

    }

