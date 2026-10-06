# Disaster Relief Resource Tracker

A serverless AWS application for tracking disaster relief resources, managing relief centers, and connecting help seekers with available aid.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                       │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Login Page  │  │ Center Dash │  │ Admin Dashboard│  │
│  │ index.html  │  │center-dash. │  │ admin-dash.html│  │
│  └──────┬──────┘  └──────┬──────┘  └───────┬───────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          │                              │
│                    ┌─────▼─────┐                        │
│                    │  api.js   │  ← HTTP calls          │
│                    └─────┬─────┘                        │
└──────────────────────────┼──────────────────────────────┘
                           │ HTTPS
              ┌────────────▼────────────┐
              │   AMAZON API GATEWAY    │
              │   (REST API)            │
              │                         │
              │  POST /auth/login       │
              │  POST /centers          │
              │  GET  /centers/{id}     │
              │  GET  /centers          │
              │  PUT  /centers/{id}/inv │
              │  GET  /centers/{id}/inv │
              │  GET  /inventory/low..  │
              │  POST /requests         │
              │  GET  /requests         │
              │  PUT  /requests/{id}    │
              │  GET  /stats            │
              └────────────┬────────────┘
                           │ AWS Lambda proxy
              ┌────────────▼────────────┐
              │   AWS LAMBDA            │
              │   (Python 3.x)          │
              │                         │
              │  create_center.py       │
              │  get_center.py          │
              │  list_centers.py        │
              │  update_inventory.py    │
              │  get_inventory.py       │
              │  get_low_stock.py       │
              │  submit_request.py      │
              │  list_requests.py       │
              │  update_request_status  │
              │  login_user.py          │
              │  get_stats.py           │
              └────────────┬────────────┘
                           │ boto3 SDK
              ┌────────────▼────────────┐
              │   AMAZON DYNAMODB       │
              │                         │
              │  ReliefCenters table    │
              │  Inventory table        │
              │  HelpRequests table     │
              │  Users table            │
              └─────────────────────────┘
```

## Project Structure

```
AWS Project/
├── README.md                      ← This file
├── dynamodb-schema.json           ← Table schemas with design rationale
├── iam-permissions.md             ← Least-privilege IAM per function
│
├── frontend/                      ← Static files (deploy to S3)
│   ├── index.html                 ← Login page
│   ├── center-dashboard.html      ← Staff center management
│   ├── public-request.html        ← Public help request form
│   ├── admin-dashboard.html       ← Admin overview
│   ├── css/
│   │   └── style.css              ← All styling
│   └── js/
│       ├── api.js                 ← API Gateway URL + HTTP helpers
│       ├── auth.js                ← Auth guard + session helpers
│       ├── login.js               ← Login form controller
│       ├── center-dashboard.js    ← Center inventory controller
│       ├── public-request.js      ← Help request form controller
│       └── admin-dashboard.js     ← Admin dashboard controller
│
└── lambda/                        ← One file per Lambda function
    ├── create_center.py           ← POST /centers
    ├── get_center.py              ← GET /centers/{centerId}
    ├── list_centers.py            ← GET /centers
    ├── update_inventory.py        ← PUT /centers/{centerId}/inventory
    ├── get_inventory.py           ← GET /centers/{centerId}/inventory
    ├── get_low_stock.py           ← GET /inventory/low-stock
    ├── submit_request.py          ← POST /requests
    ├── list_requests.py           ← GET /requests
    ├── update_request_status.py   ← PUT /requests/{requestId}
    ├── login_user.py              ← POST /auth/login
    └── get_stats.py               ← GET /stats
```

## How the Pieces Connect

### 1. Frontend → API Gateway

The frontend is a set of static HTML/CSS/JS files. `api.js` contains the `API_BASE_URL` constant that points to your API Gateway invoke URL. All HTTP requests go through `apiRequest()` which handles JSON serialization and error parsing.

**You need to**: Replace `YOUR_API_GATEWAY_INVOKE_URL_HERE` in `frontend/js/api.js` with your actual API Gateway URL.

### 2. API Gateway → Lambda

Each API Gateway route maps to a Lambda function. You create this mapping in the API Gateway console:
- `POST /auth/login` → `login_user` Lambda
- `POST /centers` → `create_center` Lambda
- `GET /centers/{centerId}` → `get_center` Lambda
- `PUT /centers/{centerId}/inventory` → `update_inventory` Lambda
- ... and so on

API Gateway passes the request body, path parameters, and query string parameters to Lambda via the `event` object.

### 3. Lambda → DynamoDB

Each Lambda function uses `boto3` (AWS SDK for Python) to read/write to DynamoDB. The function's IAM execution role grants only the specific DynamoDB permissions it needs (see `iam-permissions.md`).

### 4. DynamoDB Tables

Four tables, each with a clear purpose:
- **ReliefCenters** — Center details (PK: centerId)
- **Inventory** — Resources per center (PK: centerId, SK: resourceType)
- **HelpRequests** — Public requests (PK: requestId, with GSIs for status/urgency)
- **Users** — Login accounts (PK: email)

Full schema with rationale: see `dynamodb-schema.json`

## Setup Instructions

### Prerequisites
- AWS Account
- AWS CLI configured
- Python 3.9+

### Step 1: Create DynamoDB Tables

In the AWS Console → DynamoDB → Create table, create these 4 tables as defined in `dynamodb-schema.json`:

1. **ReliefCenters** — Partition key: `centerId` (String)
   - Create GSI: `StaffEmail-index`, partition key: `staffEmail`

2. **Inventory** — Partition key: `centerId` (String), Sort key: `resourceType` (String)
   - Create GSI: `LowStock-index`, partition key: `lowStock`, sort key: `resourceType`

3. **HelpRequests** — Partition key: `requestId` (String)
   - Create GSI: `StatusUrgency-index`, partition key: `status`, sort key: `urgency`
   - Create GSI: `LocationStatus-index`, partition key: `location`, sort key: `status`

4. **Users** — Partition key: `email` (String)

### Step 2: Create Lambda Functions

1. Go to AWS Lambda → Create function → Author from scratch
2. Runtime: Python 3.9+
3. Create one function per file in the `lambda/` directory
4. Copy-paste the code from each `.py` file
5. Set the handler to `lambda_handler` (already the default)
6. Assign the appropriate IAM role (see `iam-permissions.md`)

### Step 3: Create API Gateway

1. Go to API Gateway → Create REST API (not HTTP API for full control)
2. Create resources and methods matching the routes listed above
3. Enable CORS on all resources
4. For each method, set the integration type to "Lambda Function" and select the corresponding Lambda
5. Deploy the API to a stage (e.g., `prod`)
6. Copy the invoke URL

### Step 4: Update Frontend

1. Open `frontend/js/api.js`
2. Replace `YOUR_API_GATEWAY_INVOKE_URL_HERE` with your API Gateway invoke URL

### Step 5: Deploy Frontend to S3

1. Create an S3 bucket
2. Enable static website hosting
3. Upload all files from the `frontend/` directory
4. Set bucket policy to allow public read access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
        }
    ]
}
```

5. Visit the website URL from the bucket properties

### Step 6: Seed Test Data (Optional)

1. Register a relief center via the admin dashboard or API
2. Login as the staff user and update inventory
3. Submit a few help requests from the public form
4. Check the admin dashboard to see everything

## Testing the Application

1. **Public user**: Go to `public-request.html` → Submit a help request
2. **Staff login**: Go to `index.html` → Login → Update inventory
3. **Admin login**: Go to `index.html` → Login with admin credentials → View dashboard

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Separate DynamoDB tables** | Clearer for course demo; each table maps 1:1 to a concept |
| **Composite key on Inventory** | centerId + resourceType ensures one record per resource per center |
| **LowStock GSI with boolean flag** | Enables fast queries for critical alerts without scanning entire table |
| **Urgency as Number (1-4)** | DynamoDB sorts numerically; urgency=1 sorts first (highest priority) |
| **Plain HTML/CSS/JS frontend** | Static-hostable on S3; no build step needed; easy to explain |
| **One Lambda per action** | Follows single-responsibility principle; easy to test and debug |
| **No hardcoded credentials** | Lambda uses IAM execution roles; frontend uses no AWS keys |

## Limitations (for discussion in viva)

- **Auth is simplified**: Passwords use a basic SHA-256 hash and the returned token is only a demo session token. In production, use AWS Cognito with JWT tokens.
- **Public users** can submit a request and check its status using the request reference shown after submission.
- **Operational endpoints** include `GET /health` for a simple deployment check and `GET /requests/{requestId}` for public status lookup.
- **No pagination**: Scan/Query results are not paginated. In production, use DynamoDB pagination with `LastEvaluatedKey`.
- **No optimistic locking**: Concurrent inventory updates could cause race conditions. Use DynamoDB conditional writes.
- **Single-region**: No cross-region replication. For global disasters, consider DynamoDB Global Tables.
- **No real-time updates**: Dashboard requires manual refresh. Could add WebSocket API or AppSync subscriptions.
