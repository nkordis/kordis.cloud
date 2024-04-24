import os

import boto3
import pytest
import requests

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test. 
"""


class TestApiGateway:

    @pytest.fixture()
    def api_gateway_url(self):
        """ Get the API Gateway URL from Cloudformation Stack outputs """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")

        if stack_name is None:
            raise ValueError('Please set the AWS_SAM_STACK_NAME environment variable to the name of your stack')

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n" f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [output for output in stack_outputs if output["OutputKey"] == "KordisCloudAPI"]

        if not api_outputs:
            raise KeyError(f"KordisCloudAPI not found in stack {stack_name}")

        return api_outputs[0]["OutputValue"]  # Extract url from stack outputs

    def test_get_visits_api_gateway(self, api_gateway_url):
        """ Call the API Gateway endpoint with a GET request and check the response """
        response = requests.get(api_gateway_url + "visits")
        response_data = response.json()

        assert response.status_code == 200
        assert response_data['message'] == 'Success' 
        assert isinstance(response_data['visitsCount'], int)

    def test_put_visits_api_gateway(self, api_gateway_url):
        """ Call the API Gateway endpoint with a PUT request and check the response """
        respone_get = requests.put(api_gateway_url + "visits")
        response = requests.put(api_gateway_url + "visits")

        response_data = response.json()
        response_get_data = respone_get.json()

        assert response.status_code == 200
        assert response_data['message'] == 'Updated visit count' 
        assert isinstance(response_data['visitsCount'], int)
        assert response_data['visitsCount'] >= response_get_data['visitsCount'] + 1