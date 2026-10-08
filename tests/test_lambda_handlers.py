import importlib
import json
import sys
import types
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAMBDA_PATH = str(PROJECT_ROOT / "lambda")
if LAMBDA_PATH not in sys.path:
    sys.path.insert(0, LAMBDA_PATH)


def load_handler(module_name):
    sys.modules.pop(module_name, None)
    resource = Mock()
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.resource = resource
    tables = {}

    def table_factory(table_name):
        tables.setdefault(table_name, Mock())
        return tables[table_name]

    resource.return_value.Table.side_effect = table_factory
    with patch.dict(sys.modules, {"boto3": fake_boto3}):
        module = importlib.import_module(module_name)
    return module


class LambdaHandlerTests(unittest.TestCase):
    def test_submit_request_rejects_missing_required_field(self):
        module = load_handler("submit_request")

        response = module.lambda_handler(
            {"body": json.dumps({"name": "Asha"})},
            None,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Missing required field", response["body"])
        module.requests_table.put_item.assert_not_called()

    def test_submit_request_rejects_invalid_urgency(self):
        module = load_handler("submit_request")

        response = module.lambda_handler(
            {
                "body": json.dumps(
                    {
                        "name": "Asha",
                        "location": "Patna",
                        "needType": "food",
                        "urgency": 5,
                        "description": "Needs food",
                    }
                )
            },
            None,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Urgency must be", response["body"])
        module.requests_table.put_item.assert_not_called()

    def test_submit_request_creates_pending_request(self):
        module = load_handler("submit_request")

        response = module.lambda_handler(
            {
                "body": json.dumps(
                    {
                        "name": "Asha",
                        "location": "Patna",
                        "needType": "food",
                        "urgency": 1,
                        "description": "Needs food",
                    }
                )
            },
            None,
        )

        self.assertEqual(response["statusCode"], 201)
        result = json.loads(response["body"])
        self.assertEqual(result["status"], "pending")
        module.requests_table.put_item.assert_called_once()
        item = module.requests_table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["urgencyLabel"], "critical")
        self.assertEqual(item["status"], "pending")

    def test_login_rejects_invalid_password(self):
        module = load_handler("login_user")
        module.users_table.get_item.return_value = {
            "Item": {
                "email": "staff@example.com",
                "passwordHash": module.hash_password("correct-password"),
                "role": "staff",
            }
        }

        response = module.lambda_handler(
            {
                "body": json.dumps(
                    {"email": "staff@example.com", "password": "wrong-password"}
                )
            },
            None,
        )

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Invalid email or password", response["body"])

    def test_login_returns_user_and_center_for_staff(self):
        module = load_handler("login_user")
        module.users_table.get_item.return_value = {
            "Item": {
                "email": "staff@example.com",
                "passwordHash": module.hash_password("correct-password"),
                "name": "Staff Member",
                "role": "staff",
                "centerId": "center-1",
            }
        }
        module.centers_table.get_item.return_value = {
            "Item": {"centerId": "center-1", "name": "Central Relief Center"}
        }

        response = module.lambda_handler(
            {
                "body": json.dumps(
                    {"email": "staff@example.com", "password": "correct-password"}
                )
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        result = json.loads(response["body"])
        self.assertEqual(result["user"]["role"], "staff")
        self.assertEqual(result["user"]["center"]["name"], "Central Relief Center")
        self.assertTrue(result["token"].startswith("mock-token-"))

    def test_update_inventory_marks_item_low_stock(self):
        module = load_handler("update_inventory")
        module.inventory_table.update_item.return_value = {
            "Attributes": {
                "centerId": "center-1",
                "resourceType": "water",
                "quantity": Decimal("20"),
                "threshold": Decimal("50"),
                "lowStock": "true",
            }
        }

        response = module.lambda_handler(
            {
                "pathParameters": {"centerId": "center-1"},
                "body": json.dumps(
                    {
                        "resourceType": "water",
                        "quantity": 20,
                        "unit": "liters",
                        "threshold": 50,
                    }
                ),
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        call = module.inventory_table.update_item.call_args.kwargs
        self.assertEqual(call["ExpressionAttributeValues"][":lowstock"], "true")
        result = json.loads(response["body"])
        self.assertEqual(result["inventory"]["lowStock"], "true")

    def test_get_low_stock_queries_index_and_enriches_center(self):
        module = load_handler("get_low_stock")
        module.inventory_table.query.return_value = {
            "Items": [
                {
                    "centerId": "center-1",
                    "resourceType": "food",
                    "quantity": 5,
                    "unit": "kg",
                    "threshold": 10,
                }
            ]
        }
        module.centers_table = Mock()
        module.dynamodb.Table.side_effect = lambda _: module.centers_table
        module.centers_table.get_item.return_value = {
            "Item": {"name": "Central Relief Center", "location": "Patna"}
        }

        response = module.lambda_handler({}, None)

        self.assertEqual(response["statusCode"], 200)
        result = json.loads(response["body"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["lowStockItems"][0]["centerName"], "Central Relief Center")
        module.inventory_table.query.assert_called_once()

    def test_update_request_status_updates_request(self):
        module = load_handler("update_request_status")
        module.requests_table.update_item.return_value = {
            "Attributes": {
                "requestId": "request-1",
                "status": "assigned",
                "assignedCenterId": "center-1",
            }
        }

        response = module.lambda_handler(
            {
                "pathParameters": {"requestId": "request-1"},
                "body": json.dumps(
                    {"status": "assigned", "assignedCenterId": "center-1"}
                ),
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        result = json.loads(response["body"])
        self.assertEqual(result["request"]["status"], "assigned")
        call = module.requests_table.update_item.call_args.kwargs
        self.assertEqual(call["Key"], {"requestId": "request-1"})
        self.assertEqual(call["ExpressionAttributeValues"][":status"], "assigned")

    def test_update_request_status_rejects_invalid_status(self):
        module = load_handler("update_request_status")

        response = module.lambda_handler(
            {
                "pathParameters": {"requestId": "request-1"},
                "body": json.dumps({"status": "cancelled"}),
            },
            None,
        )

        self.assertEqual(response["statusCode"], 400)
        module.requests_table.update_item.assert_not_called()

    def test_handlers_return_500_when_dynamodb_fails(self):
        cases = [
            (
                "submit_request",
                {"body": json.dumps({
                    "name": "Asha",
                    "location": "Patna",
                    "needType": "food",
                    "urgency": 1,
                    "description": "Needs food",
                })},
                "requests_table",
                "put_item",
            ),
            (
                "update_inventory",
                {
                    "pathParameters": {"centerId": "center-1"},
                    "body": json.dumps({"resourceType": "water", "quantity": 1}),
                },
                "inventory_table",
                "update_item",
            ),
            (
                "update_request_status",
                {
                    "pathParameters": {"requestId": "request-1"},
                    "body": json.dumps({"status": "assigned"}),
                },
                "requests_table",
                "update_item",
            ),
        ]

        for module_name, event, table_name, method_name in cases:
            with self.subTest(module=module_name):
                module = load_handler(module_name)
                getattr(getattr(module, table_name), method_name).side_effect = RuntimeError(
                    "database unavailable"
                )

                response = module.lambda_handler(event, None)

                self.assertEqual(response["statusCode"], 500)
                self.assertIn("Internal server error", response["body"])


if __name__ == "__main__":
    unittest.main()
