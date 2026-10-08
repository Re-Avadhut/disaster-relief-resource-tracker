import json
import os
import re
import subprocess
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = PROJECT_ROOT / "frontend" / "js" / "api.js"


def deployed_api_url():
    configured_url = os.environ.get("AWS_TEST_API_BASE_URL")
    if configured_url:
        return configured_url.rstrip("/")

    source = API_SOURCE.read_text(encoding="utf-8")
    match = re.search(r"const API_BASE_URL\s*=\s*['\"]([^'\"]+)", source)
    if not match:
        raise RuntimeError("Set AWS_TEST_API_BASE_URL to the deployed API Gateway URL")
    return match.group(1).rstrip("/")


def request_json(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        deployed_api_url() + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        payload = error.read().decode("utf-8")
        return error.code, json.loads(payload) if payload else {}
    except URLError as error:
        raise AssertionError(f"Could not reach deployed API: {error}") from error


@unittest.skipUnless(
    os.environ.get("RUN_AWS_TESTS") == "1",
    "Set RUN_AWS_TESTS=1 to run tests against the deployed AWS API",
)
class DeployedApiTests(unittest.TestCase):
    def test_api_gateway_lists_centers(self):
        status, body = request_json("GET", "/centers")

        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)
        self.assertIn("centers", body)

    def test_api_gateway_returns_stats(self):
        status, body = request_json("GET", "/stats")

        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)

    def test_api_gateway_validates_invalid_help_request(self):
        status, body = request_json("POST", "/requests", {"name": "deployment-test"})

        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_api_gateway_returns_low_stock_response(self):
        status, body = request_json("GET", "/inventory/low-stock")

        self.assertEqual(status, 200)
        self.assertIsInstance(body, dict)
        self.assertIn("lowStockItems", body)
        self.assertIn("count", body)

    @unittest.skipUnless(
        os.environ.get("AWS_TEST_CREATE_DATA") == "1",
        "Set AWS_TEST_CREATE_DATA=1 to create a test help request in DynamoDB",
    )
    def test_api_gateway_creates_help_request(self):
        status, body = request_json(
            "POST",
            "/requests",
            {
                "name": "AWS deployment test",
                "location": "Test location",
                "needType": "other",
                "urgency": 4,
                "description": "Automated deployment smoke test",
            },
        )

        self.assertEqual(status, 201)
        self.assertIn("requestId", body)
        self.assertEqual(body["status"], "pending")


@unittest.skipUnless(
    os.environ.get("RUN_AWS_CLI_TESTS") == "1",
    "Set RUN_AWS_CLI_TESTS=1 to run AWS CLI deployment checks",
)
class AwsCliDeploymentTests(unittest.TestCase):
    region = os.environ.get("AWS_TEST_REGION", "ap-south-1")
    api_id = os.environ.get("AWS_TEST_API_ID", "qk6fhr7ko8")
    lambda_names = (
        "create_center",
        "get_center",
        "list_centers",
        "update_inventory",
        "get_inventory",
        "get_low_stock",
        "submit_request",
        "list_requests",
        "update_request_status",
        "login_user",
        "get_stats",
    )

    @staticmethod
    def run_aws(*arguments):
        result = subprocess.run(
            ["aws", *arguments],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise AssertionError(result.stderr.strip() or result.stdout.strip())
        return result.stdout

    def test_aws_identity_is_available(self):
        output = self.run_aws("sts", "get-caller-identity", "--output", "json")
        identity = json.loads(output)
        self.assertIn("Account", identity)

    def test_api_gateway_rest_api_exists(self):
        output = self.run_aws(
            "apigateway",
            "get-rest-api",
            "--rest-api-id",
            self.api_id,
            "--region",
            self.region,
            "--output",
            "json",
        )
        api = json.loads(output)
        self.assertEqual(api["id"], self.api_id)

    def test_lambda_functions_exist(self):
        for function_name in self.lambda_names:
            with self.subTest(function=function_name):
                output = self.run_aws(
                    "lambda",
                    "get-function",
                    "--function-name",
                    function_name,
                    "--region",
                    self.region,
                    "--output",
                    "json",
                )
                function = json.loads(output)
                self.assertEqual(function["Configuration"]["FunctionName"], function_name)


if __name__ == "__main__":
    unittest.main()
