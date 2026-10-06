# IAM Permissions — Least Privilege per Lambda Function

Each Lambda function should have its own IAM execution role with only the permissions it needs.

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

## Summary: Create Two IAM Roles

For simplicity in a course project, you can create **two IAM roles**:

### Role 1: `LambdaReliefCenterRole`
Used by: `create_center`, `get_center`, `list_centers`, `update_inventory`, `get_inventory`, `get_low_stock`, `login_user`, `get_stats`

**Permissions:**
- `dynamodb:GetItem` on all tables
- `dynamodb:PutItem` on ReliefCenters, Users, Inventory
- `dynamodb:UpdateItem` on Inventory
- `dynamodb:Query` on Inventory (table + LowStock-index)
- `dynamodb:Scan` on ReliefCenters
- `dynamodb:Query` on HelpRequests (StatusUrgency-index)

### Role 2: `LambdaRequestRole`
Used by: `submit_request`, `list_requests`, `update_request_status`

**Permissions:**
- `dynamodb:PutItem` on HelpRequests
- `dynamodb:Scan` on HelpRequests
- `dynamodb:Query` on HelpRequests (StatusUrgency-index)
- `dynamodb:UpdateItem` on HelpRequests

---

## CloudFormation IAM Policy (Optional)

If you want to use IaC, here's the IAM policy JSON for Role 1:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:*:table/ReliefCenters",
                "arn:aws:dynamodb:us-east-1:*:table/ReliefCenters/index/*",
                "arn:aws:dynamodb:us-east-1:*:table/Inventory",
                "arn:aws:dynamodb:us-east-1:*:table/Inventory/index/*",
                "arn:aws:dynamodb:us-east-1:*:table/Users",
                "arn:aws:dynamodb:us-east-1:*:table/Users/index/*",
                "arn:aws:dynamodb:us-east-1:*:table/HelpRequests",
                "arn:aws:dynamodb:us-east-1:*:table/HelpRequests/index/*"
            ]
        }
    ]
}
```
