import json
import pytest
from moto import mock_aws
import boto3
from visitor_put_function import app as put_function
from visitor_get_function import app as get_function


@pytest.fixture(scope="function")
def dynamo_table():
    """Setup DynamoDB table for testing."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        # Create DynamoDB table for testing
        table = dynamodb.create_table(
            TableName='kordis-cloud',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
        )

        # Wait for table to be created
        table.wait_until_exists()

        # Prepopulate the table with initial count
        table.put_item(Item={'id': 'visits', 'visitsCount': 10})
        
        yield table  # This allows the table to be used in tests

        # Cleanup actions after tests are done
        table.delete()
        dynamodb.meta.client.get_waiter('table_not_exists').wait(TableName='kordis-cloud')

@pytest.fixture()
def apigw_event_put():
    """Generates API GW Event for PUT request"""
    return {
        "body": json.dumps({}),  # Assuming no specific body is required
        "httpMethod": "PUT",
        "path": "/visits",
        "requestContext": {
            "identity": {
                "sourceIp": "123.123.123.123"
            }
        }
    }

@pytest.fixture()
def apigw_event_get():
    """Generates API GW Event for GET request"""
    return {
        "body": None,  # GET requests typically don't have a body
        "httpMethod": "GET",
        "path": "/visits",
        "requestContext": {
            "identity": {
                "sourceIp": "123.123.123.123"
            }
        }
    }

def test_visitor_count_put_function(apigw_event_put, dynamo_table):
    """Test the VisitorCountPutFunction to ensure it increments the count."""
    # Get initial count
    initial_response = dynamo_table.get_item(Key={'id': 'visits'})
    initial_count = int(initial_response['Item']['visitsCount'])

    # Invoke the PUT Lambda function
    response = put_function.lambda_handler(apigw_event_put, {})
    data = json.loads(response["body"])

    # Check response status code
    assert response["statusCode"] == 200

    # Get updated count
    updated_response = dynamo_table.get_item(Key={'id': 'visits'})
    updated_count = updated_response['Item']['visitsCount']

    # Assert the count was incremented by 1
    assert updated_count == initial_count + 1, "Count should increment by 1"


def test_visitor_count_get_function(apigw_event_get, dynamo_table):
    """Test the VisitorCountGetFunction to ensure it correctly fetches the current count."""
    # Initially set a known count value
    dynamo_table.put_item(Item={'id': 'visits', 'visitsCount': 15})

    # Invoke the GET Lambda function
    response = get_function.lambda_handler(apigw_event_get, {})
    data = json.loads(response["body"])

    # Check response status code
    assert response["statusCode"] == 200, "HTTP Status code should be 200"

    # Validate the count fetched is as expected
    assert data['visitsCount'] == 15, "Should return the correct visits count of 15"

    # Optionally, you can check for the structure of the response if it's consistent
    assert 'visitsCount' in data, "Response body must include visitsCount"

