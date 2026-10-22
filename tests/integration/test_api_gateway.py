import os

import boto3
import pytest
import requests

"""
Set KORDIS_API_URL to the API base URL (CI does), or AWS_SAM_STACK_NAME to read it from the stack outputs.
"""


class TestApiGateway:

    @pytest.fixture()
    def api_gateway_url(self):
        """ Use KORDIS_API_URL if set, otherwise read the URL from the Cloudformation Stack outputs """
        api_url = os.environ.get("KORDIS_API_URL")
        if api_url:
            return api_url if api_url.endswith("/") else api_url + "/"

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
        """ Call PUT twice: the count is returned, and the same visitor is counted at most once a day """
        first = requests.put(api_gateway_url + "visits")
        second = requests.put(api_gateway_url + "visits")

        first_data = first.json()
        second_data = second.json()

        assert first.status_code == 200
        assert second.status_code == 200
        assert isinstance(first_data['visitsCount'], int)
        assert isinstance(second_data['visitsCount'], int)
        assert second_data['counted'] is False
        assert second_data['message'] == 'Visit already counted today'
        assert second_data['visitsCount'] >= first_data['visitsCount']

    def test_cors_rejects_other_origins(self, api_gateway_url):
        """ Only the portfolio origins get a CORS header """
        allowed = requests.options(api_gateway_url + "visits", headers={"Origin": "https://kordis.cloud"})
        denied = requests.options(api_gateway_url + "visits", headers={"Origin": "https://example.com"})

        assert allowed.headers.get('Access-Control-Allow-Origin') == 'https://kordis.cloud'
        assert 'Access-Control-Allow-Origin' not in denied.headers
