# IAM Permissions — Least Privilege per Lambda Function

Each Lambda function should have its own IAM execution role with only the permissions it needs.
Do not reuse a role between functions unless their required actions and resources are
identical. Every role also needs the Lambda logging permissions from
`AWSLambdaBasicExecutionRole` (or an equivalent custom policy limited to that function's
CloudWatch log group).

> **Note**: All resources below use the ARN format:
> `arn:aws:dynamodb:REGION:ACCOUNT_ID:table/TABLE_NAME`
> Replace `REGION` and `ACCOUNT_ID` with your actual values.

---

## 1. `create_center.py`
**Creates a new relief center and its staff user account.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:PutItem` | `ReliefCenters` | Insert the new center record |
| `dynamodb:PutItem` | `Users` | Create the staff user account |
| `dynamodb:PutItem` | `Inventory` | Initialize default inventory items for the new center |

---

## 2. `get_center.py`
**Retrieves a single relief center by ID.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:GetItem` | `ReliefCenters` | Fetch center record by partition key |

---

## 3. `list_centers.py`
**Lists all relief centers (admin overview).**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:Scan` | `ReliefCenters` | Scan all centers (no filter on partition key) |

---

## 4. `update_inventory.py`
**Updates a specific resource type in a center's inventory.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:UpdateItem` | `Inventory` | Update quantity/threshold/lowStock for a specific center+resource |

---

## 5. `get_inventory.py`
**Returns the full inventory for one center.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:Query` | `Inventory` | Query all resource types for a center (partition key = centerId) |

---

## 6. `get_low_stock.py`
**Returns all resources below their threshold across all centers.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:Query` | `Inventory:index/LowStock-index` | Query the GSI where lowStock = 'true' |
| `dynamodb:GetItem` | `ReliefCenters` | Look up center names for display (enrichment) |

---

## 7. `submit_request.py`
**Creates a new public help request.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:PutItem` | `HelpRequests` | Insert the new request record |

---

## 8. `list_requests.py`
**Lists help requests with optional filtering.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:Scan` | `HelpRequests` | Scan all requests (fallback) |
| `dynamodb:Query` | `HelpRequests:index/StatusUrgency-index` | Query by status, sorted by urgency |

---

## 9. `update_request_status.py`
**Updates a request's status (pending → assigned → resolved).**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:UpdateItem` | `HelpRequests` | Update status and assignedCenterId |

---

## 10. `login_user.py`
**Authenticates a user and returns their role/center info.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:GetItem` | `Users` | Look up user by email (partition key) |
| `dynamodb:GetItem` | `ReliefCenters` | Fetch center details for staff users |

---

## 11. `get_stats.py`
**Returns summary statistics for the admin dashboard.**

| Permission | Resource | Reason |
|---|---|---|
| `dynamodb:Scan` | `ReliefCenters` | Count total and active centers |
| `dynamodb:Query` | `HelpRequests:index/StatusUrgency-index` | Count requests by status and urgency |
| `dynamodb:Query` | `Inventory:index/LowStock-index` | Count low-stock items |

---

## Role assignment

Create one execution role per Lambda and attach only the policy for that function.
The role name should match the function, for example `create_center-execution-role`.
This prevents a read-only function from inheriting write permissions intended for another
function.

| Lambda | DynamoDB permissions |
|---|---|
| `create_center` | `PutItem` on `ReliefCenters`, `Users`, and `Inventory` |
| `get_center` | `GetItem` on `ReliefCenters` |
| `list_centers` | `Scan` on `ReliefCenters` |
| `update_inventory` | `UpdateItem` on `Inventory` |
| `get_inventory` | `Query` on `Inventory` |
| `get_low_stock` | `Query` on the `LowStock-index` and `GetItem` on `ReliefCenters` |
| `submit_request` | `PutItem` on `HelpRequests` |
| `list_requests` | `Scan` on `HelpRequests` and `Query` on the `StatusUrgency-index` |
| `update_request_status` | `UpdateItem` on `HelpRequests` |
| `login_user` | `GetItem` on `Users` and `ReliefCenters` |
| `get_stats` | `Scan`/`Query` only on the tables and indexes used by the handler |

Do not grant `dynamodb:*`, grant access to every table, or use `index/*`. The policy
resource must name the exact table or index required by that function.

---

## Example policy

The following is the complete DynamoDB policy for the `get_low_stock` function. Create
equivalent policies for the other functions using the role-assignment table above.
Replace both placeholders with the deployment region and account ID. The Lambda trust
policy must allow only `lambda.amazonaws.com`.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/Inventory/index/LowStock-index"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "dynamodb:GetItem",
            "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/ReliefCenters"
        }
    ]
}
```

For example, the `submit_request` policy should contain only:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "dynamodb:PutItem",
            "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/HelpRequests"
        }
    ]
}
```

Do not attach the example policy to every Lambda. Each function's role must contain
only its own required statements.
