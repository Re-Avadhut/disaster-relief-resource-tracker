# Disaster Relief Resource Tracker

## Project Showcase and Viva Preparation Guide

This document explains the complete project in presentation-ready language:

- What problem the project solves
- The AWS architecture and request flow
- Every Lambda function
- DynamoDB tables, keys, and indexes
- IAM users, roles, and policies
- API Gateway and S3 setup
- CloudWatch logging
- Testing and deployment verification
- Security decisions and limitations
- Likely questions and short answers

Use the **Short project explanation** section for the opening of the
presentation. Use the remaining sections when the evaluator asks for
technical details.

---

## 1. Short project explanation

> The Disaster Relief Resource Tracker is a serverless web application for
> coordinating disaster-relief requests, relief centers, and available
> resources. A person can submit a help request without creating an account.
> Administrators can view incoming requests, check urgent cases, assign a
> request to a specific active relief center, and monitor low-stock resources.
> Relief-center staff can view their center's inventory and update quantities.
>
> The frontend is hosted as static files in Amazon S3. It calls an Amazon API
> Gateway REST API. API Gateway invokes separate Python AWS Lambda functions,
> and the Lambda functions use the boto3 SDK to read and write data in Amazon
> DynamoDB. Lambda execution logs are sent to Amazon CloudWatch Logs through
> the Lambda execution role.

The main design choice is serverless:

```text
Browser
  -> Amazon S3 static frontend
  -> API Gateway REST API
  -> Python Lambda functions
  -> DynamoDB tables
  -> CloudWatch Logs for execution logs
```

There are no EC2 servers to manage. AWS handles the infrastructure needed to
run the functions and scale the managed services.

---

## 2. What problem the project solves

During a disaster, information is usually scattered:

- People need food, water, medical supplies, or shelter.
- Relief centers have limited and changing inventory.
- Administrators need to prioritize urgent requests.
- A request should have a visible lifecycle instead of remaining an
  untracked message.

This project provides one small coordination system:

1. A public user submits a help request.
2. The request is stored with a generated ID and a pending status.
3. An administrator reviews the request.
4. The administrator assigns it to a selected active relief center.
5. Staff can manage the center's inventory.
6. The request can eventually be marked as resolved.
7. Low-stock resources are surfaced to the administrator.

The project demonstrates a complete cloud workflow rather than only a static
web page.

---

## 3. AWS architecture

### Main services

| AWS service | Responsibility |
|---|---|
| Amazon S3 | Hosts the static HTML, CSS, and JavaScript frontend |
| API Gateway REST API | Provides HTTP endpoints and invokes Lambda |
| AWS Lambda | Runs the backend business logic without servers |
| Amazon DynamoDB | Stores centers, inventory, requests, and users |
| AWS IAM | Controls who can access AWS and what Lambda can access |
| Amazon CloudWatch Logs | Stores Lambda invocation and error logs |

### Actual deployment values

| Item | Value |
|---|---|
| Region | `ap-south-1` |
| API Gateway REST API ID | `qk6fhr7ko8` |
| API base URL | `https://qk6fhr7ko8.execute-api.ap-south-1.amazonaws.com/prod` |
| S3 bucket | `disaster-relief-tracker-avadhut-2026` |
| S3 website endpoint | `http://disaster-relief-tracker-avadhut-2026.s3-website.ap-south-1.amazonaws.com/` |
| API stage | `prod` |

The frontend stores the API base URL in `frontend/js/api.js`. It does not
contain AWS access keys. The browser only makes HTTP requests to API Gateway.

### Complete request flow

For a public request:

```text
User fills public-request.html
  -> public-request.js validates the form
  -> api.js sends POST /requests
  -> API Gateway invokes submit_request
  -> submit_request validates the data
  -> submit_request writes to HelpRequests
  -> Lambda returns HTTP 201 and a requestId
  -> frontend displays the success state
```

For an administrator assignment:

```text
Admin clicks View
  -> frontend opens the request-details modal

Admin clicks Assign
  -> frontend calls GET /centers?status=active
  -> admin selects a relief center
  -> frontend sends PUT /requests/{requestId}
     { "status": "assigned", "assignedCenterId": "..." }
  -> API Gateway invokes update_request_status
  -> Lambda updates the HelpRequests item
  -> frontend reloads the request table and statistics
```

For inventory:

```text
Staff opens center dashboard
  -> GET /centers/{centerId}/inventory
  -> get_inventory queries all resources for that center

Staff changes a quantity
  -> PUT /centers/{centerId}/inventory
  -> update_inventory updates the item
  -> Lambda calculates lowStock
  -> admin can see the item through LowStock-index
```

---

## 4. Frontend structure

The frontend intentionally remains plain static HTML, CSS, and JavaScript.
This keeps the project easy to deploy to S3 and easy to explain.

| File | Purpose |
|---|---|
| `frontend/index.html` | Staff/admin login page |
| `frontend/public-request.html` | Public help-request form |
| `frontend/admin-dashboard.html` | Admin statistics, requests, centers, and low-stock view |
| `frontend/center-dashboard.html` | Staff center details and inventory management |
| `frontend/js/api.js` | API Gateway URL and shared HTTP helper |
| `frontend/js/auth.js` | Role guard and browser session helpers |
| `frontend/js/login.js` | Login form controller |
| `frontend/js/public-request.js` | Public form validation and submission |
| `frontend/js/admin-dashboard.js` | Admin data loading, View, Assign, Resolve, and registration |
| `frontend/js/center-dashboard.js` | Center inventory loading and updates |
| `frontend/css/style.css` | Responsive visual design and dashboard layout |

Tailwind's browser CDN is included for utility classes and small interactions,
but the project does not require a React build process. The main visual
system is still in `style.css`.

### Authentication behavior in the frontend

After login, the frontend stores the returned user object in browser
`localStorage` under `drt_user`. Protected pages call:

```javascript
requireAuth('admin')
requireAuth('staff')
```

The guard redirects to the login page when no local session exists or when
the role does not match.

This is suitable for a demonstration, but it is not a production security
boundary. A browser can modify localStorage. A production version should use
Amazon Cognito and an API Gateway authorizer.

---

## 5. DynamoDB data model

The project uses four separate tables because each table represents a clear
business concept. This is easier to explain in a college project than a
single-table design.

### 5.1 `ReliefCenters`

**Partition key:** `centerId` (String)

Stores:

- Center name and location
- Contact information
- Staff email
- Active/inactive status
- Optional latitude and longitude
- Creation timestamp

**GSI:** `StaffEmail-index`

- Partition key: `staffEmail`
- Purpose: find the center associated with a staff login

### 5.2 `Inventory`

**Partition key:** `centerId` (String)  
**Sort key:** `resourceType` (String)

The composite key means one center can have one item for each resource type,
such as food, water, medical, and shelter.

Stores:

- Current quantity
- Unit
- Minimum threshold
- `lowStock` flag
- Last-updated timestamp

**GSI:** `LowStock-index`

- Partition key: `lowStock`
- Sort key: `resourceType`
- Purpose: query all items with `lowStock = "true"` across centers

The low-stock flag is denormalized intentionally. Instead of calculating a
comparison across every inventory item for every admin page load, the update
Lambda calculates it once whenever an item changes.

### 5.3 `HelpRequests`

**Partition key:** `requestId` (String)

Stores:

- Requester name
- Location
- Need type
- Numeric urgency
- Human-readable urgency label
- Description
- Optional phone number
- Status
- Assigned center ID
- Creation timestamp

Possible statuses:

```text
pending -> assigned -> resolved
```

**GSI:** `StatusUrgency-index`

- Partition key: `status`
- Sort key: `urgency`
- Purpose: retrieve requests for a status and prioritize critical requests

Urgency values are numeric because DynamoDB can sort them naturally:

```text
1 = critical
2 = high
3 = medium
4 = low
```

**GSI:** `LocationStatus-index`

- Partition key: `location`
- Sort key: `status`
- Purpose: support location-based status filtering

### 5.4 `Users`

**Partition key:** `email` (String)

Stores:

- Email
- Password hash
- Display name
- Role: `admin` or `staff`
- Center ID for staff
- Creation timestamp

The current project stores this information for demonstration login behavior.
For production, Cognito should own passwords, MFA, token issuance, and user
authentication.

---

## 6. Lambda functions explained

Every Lambda follows the same broad pattern:

1. API Gateway supplies an event.
2. The function reads path parameters, query parameters, or the JSON body.
3. It validates required input.
4. It uses a boto3 DynamoDB resource and table object.
5. It returns an API Gateway-compatible response:

```python
{
    "statusCode": 200,
    "headers": {...},
    "body": json.dumps(...)
}
```

The CORS headers allow the S3-hosted frontend to call the API. The
`Content-Type` header tells the browser that the response is JSON.

### 6.1 `create_center`

**Route:** `POST /centers`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Parses the JSON request body.
2. Checks `name`, `location`, `staffEmail`, and `staffPassword`.
3. Generates a UUID for `centerId`.
4. Creates a `ReliefCenters` item.
5. Hashes the staff password and creates a `Users` item.
6. Creates default inventory rows for food, water, medical, and shelter.
7. Returns HTTP `201` with the new center ID.

The default inventory starts at zero, so each new center is initially marked
low stock. This gives the admin immediate visibility of resources that need
to be supplied.

The function uses `Decimal` for DynamoDB numeric values because boto3's
DynamoDB resource interface expects exact decimal values rather than binary
floating-point values.

### 6.2 `get_center`

**Route:** `GET /centers/{centerId}`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Reads `centerId` from API Gateway path parameters.
2. Calls `GetItem` on `ReliefCenters`.
3. Returns HTTP `404` if there is no matching item.
4. Returns the center record with HTTP `200` when found.

This is a direct partition-key lookup and is efficient for one known center.

### 6.3 `list_centers`

**Route:** `GET /centers`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Reads the optional `status` query parameter.
2. Scans all centers when no filter is provided.
3. Uses a filtered scan when `status=active` is requested.
4. Returns the center list and count.

The admin needs an active-center list for assignment. A scan is acceptable
for the small demonstration dataset. At larger scale, a status GSI would be
preferable.

### 6.4 `update_inventory`

**Route:** `PUT /centers/{centerId}/inventory`  
**Role:** `LambdaReliefCenterRole`

Expected fields include:

```json
{
  "resourceType": "food",
  "quantity": 150,
  "unit": "kg",
  "threshold": 100
}
```

What it does:

1. Reads `centerId` from the path.
2. Reads `resourceType`, quantity, unit, and threshold from the body.
3. Converts numeric values to `Decimal`.
4. Calculates:

```text
lowStock = "true" if quantity < threshold else "false"
```

5. Updates only the supplied fields.
6. Always updates `lowStock` and `lastUpdated`.
7. Uses the composite key `centerId + resourceType`.
8. Returns the updated item.

This calculation is the reason the admin dashboard can query
`LowStock-index` directly.

### 6.5 `get_inventory`

**Route:** `GET /centers/{centerId}/inventory`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Reads the center ID.
2. Queries `Inventory` using the partition key `centerId`.
3. Returns all resource types for that center.

A Query is used instead of a Scan because all requested records share a
known partition key.

### 6.6 `get_low_stock`

**Route:** `GET /inventory/low-stock`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Queries `LowStock-index` where `lowStock = "true"`.
2. For each low-stock item, reads the corresponding center.
3. Caches center lookups in `center_cache` so multiple resources from one
   center do not cause repeated reads.
4. Returns a display-friendly result containing center name, location,
   resource, quantity, unit, and threshold.

This is an example of enriching an inventory record with related center
information before returning it to the frontend.

### 6.7 `submit_request`

**Route:** `POST /requests`  
**Role:** `LambdaRequestRole`

What it does:

1. Parses the public form body.
2. Validates required fields:
   `name`, `location`, `needType`, `urgency`, and `description`.
3. Validates urgency is one of `1`, `2`, `3`, or `4`.
4. Converts urgency to a label.
5. Generates a UUID request ID.
6. Sets the initial status to `pending`.
7. Sets `assignedCenterId` to `null`.
8. Stores an ISO 8601 UTC timestamp.
9. Writes the item to `HelpRequests`.
10. Returns HTTP `201`.

This function is intentionally public so a person asking for help does not
need an account.

### 6.8 `list_requests`

**Route:** `GET /requests`  
**Role:** `LambdaRequestRole`

Supported query parameters:

```text
status=pending
sort=urgency
location=Mumbai
```

What it does:

1. If a status is supplied, queries `StatusUrgency-index`.
2. Otherwise scans the requests table.
3. Sorts by numeric urgency when requested.
4. Applies a case-insensitive location filter.
5. Returns the requests and count.

The status query uses the GSI because DynamoDB Query requires a known
partition-key value. The location filter is currently applied in Python,
which is acceptable for this project but could be replaced by a more
targeted query design at larger scale.

### 6.9 `update_request_status`

**Route:** `PUT /requests/{requestId}`  
**Role:** `LambdaRequestRole`

Valid statuses:

```text
pending
assigned
resolved
```

What it does:

1. Reads `requestId` from the path.
2. Validates that a status was supplied.
3. Rejects invalid status values.
4. Requires `assignedCenterId` when the new status is `assigned`.
5. Builds a DynamoDB `UpdateExpression`.
6. Updates status and, when supplied, the assigned center ID.
7. Returns the updated request using `ReturnValues='ALL_NEW'`.

The admin's Assign button calls this function after the admin selects a
specific active center. The Resolve button calls it with:

```json
{
  "status": "resolved"
}
```

The current implementation validates allowed status values but does not
enforce every transition server-side. A production improvement would use a
conditional update so a resolved request cannot be moved backward.

### 6.10 `login_user`

**Route:** `POST /auth/login`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Reads email and password.
2. Rejects missing credentials with HTTP `400`.
3. Looks up the user by email.
4. Hashes the submitted password.
5. Compares it with the stored hash.
6. Loads center information for staff users.
7. Creates a mock token.
8. Returns the user role, name, center, and token.

Important limitation:

- The token is a mock token.
- API Gateway does not currently validate it.
- The frontend uses the token only as a request header and the browser uses
  local role checks.
- Production authentication should use Amazon Cognito and an API Gateway
  JWT/Cognito authorizer.

This limitation should be stated confidently if asked. It shows awareness of
the difference between a course demonstration and a production system.

### 6.11 `get_stats`

**Route:** `GET /stats`  
**Role:** `LambdaReliefCenterRole`

What it does:

1. Counts all relief centers.
2. Counts active relief centers.
3. Queries request counts for pending, assigned, and resolved statuses.
4. Queries pending requests with urgency `1` for critical requests.
5. Queries `LowStock-index` for low-stock inventory.
6. Returns a summary object for the admin dashboard.

It uses `Select='COUNT'` where only counts are needed, reducing returned
payload compared with reading complete items.

---

## 7. IAM users, roles, and policies

### IAM user versus Lambda execution role

These are different:

- An **IAM user** is a person or program identity used to sign in to AWS or
  call AWS APIs.
- A **Lambda execution role** is assumed by a Lambda function while it runs.

The deployment tutorial recommends:

1. Protect the root account with MFA.
2. Avoid using root access keys.
3. Create an IAM user for console or CLI administration.
4. Use MFA for that user.
5. Attach broad administrator permissions only temporarily for a personal
   learning account.
6. Use Lambda execution roles for application permissions.

The frontend never receives AWS access keys.

### Trust policy

A Lambda execution role has a trust relationship that allows the AWS Lambda
service to assume the role. This is different from the permissions policy:

- Trust policy: who may assume the role
- Permissions policy: what the assumed role may do

### Project roles

The project uses two main roles:

#### `LambdaReliefCenterRole`

Used by:

```text
create_center
get_center
list_centers
update_inventory
get_inventory
get_low_stock
login_user
get_stats
```

It needs DynamoDB permissions for center, inventory, and user operations.

#### `LambdaRequestRole`

Used by:

```text
submit_request
list_requests
update_request_status
```

It needs:

- `dynamodb:PutItem`
- `dynamodb:UpdateItem`
- `dynamodb:Query`
- `dynamodb:Scan`

on `HelpRequests` and its indexes.

### CloudWatch permissions

Both roles should include the managed policy:

```text
AWSLambdaBasicExecutionRole
```

This allows Lambda to create log groups/streams and write log events to
CloudWatch Logs. It is why normal `print()` output from the functions can be
viewed in the Lambda Monitor tab.

### Least privilege explanation

The project separates request operations from center/inventory operations so
each group can have a narrower policy. A stronger production version would
create one role per Lambda and restrict each resource ARN to the exact table
and index needed.

---

## 8. How the project was created in the AWS Console

### Step 1: Choose one region

The project uses `ap-south-1` for all resources. Keeping services in one
region makes names, permissions, latency, and troubleshooting easier.

### Step 2: Prepare account security

In IAM and account security:

1. Enable MFA on the root account.
2. Do not create root access keys.
3. Create an administrator IAM user for learning/deployment.
4. Enable MFA for that user.
5. Create a billing budget or alert.

### Step 3: Create DynamoDB tables

Create the tables with on-demand capacity:

```text
ReliefCenters
Inventory
HelpRequests
Users
```

Then create the GSIs exactly as described in the data model section. The
index status must be Active before Lambda code that queries the index is
tested.

Encryption at rest should remain enabled. On-demand capacity is appropriate
for this small demonstration because it avoids capacity planning.

### Step 4: Create IAM roles

In IAM:

1. Create a role trusted by Lambda.
2. Attach `AWSLambdaBasicExecutionRole`.
3. Add an inline DynamoDB policy.
4. Create the second request role.
5. Attach the least-privilege policies.

### Step 5: Create Lambda functions

For each Python file:

1. Choose **Author from scratch**.
2. Use the matching function name.
3. Select a supported Python runtime.
4. Select the existing execution role.
5. Paste the file contents into the Lambda editor as
   `lambda_function.py`.
6. Keep the handler as:

```text
lambda_function.lambda_handler
```

If uploading a zip with a different filename, the handler must match the
module filename. This is a common deployment error.

### Step 6: Test a Lambda directly

Before API Gateway, use the Lambda Test tab with an event such as:

```json
{
  "body": "{\"name\":\"Test User\",\"location\":\"Test Area\",\"needType\":\"food\",\"urgency\":1,\"description\":\"Test request\"}"
}
```

Expected result:

```text
statusCode = 201
```

If the test fails, check the Monitor tab and CloudWatch logs. Common causes
are wrong table names, wrong region, missing IAM permissions, or missing
indexes.

### Step 7: Create API Gateway REST API

Create a Regional REST API named `DisasterReliefTrackerAPI`.

For each resource and method:

1. Create the path.
2. Select the method.
3. Select Lambda integration.
4. Enable Lambda proxy integration.
5. Choose the matching Lambda.
6. Approve the Lambda permission prompt.

Important paths:

```text
/centers/{centerId}
/centers/{centerId}/inventory
/requests/{requestId}
```

The names inside braces must match the names the Lambda reads from
`event['pathParameters']`.

Enable CORS if the console configuration requires it. The Lambda response
also returns CORS headers for browser requests.

### Step 8: Deploy the API

Create the `prod` stage and deploy the API. The frontend's `API_BASE_URL`
must use the deployed stage URL, not only the API root.

Example:

```text
https://qk6fhr7ko8.execute-api.ap-south-1.amazonaws.com/prod
```

If a route works in the API Gateway test tool but not in the browser, check
the stage deployment, URL, CORS, and frontend API base URL.

### Step 9: Create the S3 frontend bucket

Create the S3 bucket in the same region and upload only the contents of
`frontend/`, not the entire repository.

Enable static website hosting:

- Index document: `index.html`
- Configure the appropriate public website access for a demonstration, or
  use CloudFront with a private bucket for production.

The website endpoint is HTTP-only in the current demonstration. A production
deployment should use CloudFront and HTTPS.

### Step 10: Upload and verify

The deployment command used for the current project is:

```powershell
aws s3 sync frontend s3://disaster-relief-tracker-avadhut-2026 --region ap-south-1
```

Then open the S3 website endpoint and test:

1. Public request form
2. Login
3. Admin dashboard
4. Center dashboard
5. View request
6. Assign request
7. Inventory update

---

## 9. CloudWatch Logs and monitoring

### How logs are created

When a Lambda runs, AWS sends its standard output and errors to a CloudWatch
Logs group, usually named:

```text
/aws/lambda/<function-name>
```

The `AWSLambdaBasicExecutionRole` policy grants the basic log permissions.

The functions use `print()` for simple diagnostic messages such as:

```python
print(f"Error updating request: {str(e)}")
```

The API response intentionally returns a generic error message instead of
exposing internal details to the browser:

```json
{
  "error": "Internal server error"
}
```

The detailed exception remains in CloudWatch for diagnosis.

### How to view logs

1. Open AWS Console.
2. Open CloudWatch.
3. Choose Logs and Log groups.
4. Open `/aws/lambda/<function-name>`.
5. Open a recent log stream.
6. Check the `START`, application output, `END`, and `REPORT` entries.

The `REPORT` line is useful for duration, billed duration, memory size, and
maximum memory used.

### What to show in the report

Capture:

- Lambda function name
- Recent invocation timestamp
- Successful execution or useful error line
- CloudWatch `REPORT` line

Never include access keys, secret keys, passwords, or tokens in screenshots.

### Better production observability

For a production system, add:

- CloudWatch alarms for Lambda errors and throttles
- API Gateway access logs
- Structured JSON logging
- CloudTrail for AWS API auditing
- Request IDs/correlation IDs
- A dashboard for API latency and Lambda errors

---

## 10. Testing strategy

The project uses two levels of testing.

### Local Lambda unit tests

`tests/test_lambda_handlers.py` mocks DynamoDB table calls. This tests
business logic without changing AWS data.

The tests cover:

- Invalid public help-request input
- Urgency validation
- Successful request creation
- Login failure behavior
- Low-stock calculation and lookup
- Request status updates
- Assignment validation
- Invalid status rejection
- Lambda error responses

Run:

```powershell
& ".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_lambda_handlers.py"
```

The current result is:

```text
Ran 11 tests
OK
```

### Deployed AWS tests

`tests/test_aws_deployment.py` contains opt-in tests:

```powershell
$env:RUN_AWS_TESTS = "1"
& ".venv\Scripts\python.exe" -m unittest tests.test_aws_deployment -v
```

These verify:

- API Gateway can list centers
- `/stats` returns a response
- Invalid help requests return HTTP `400`
- Low-stock endpoint returns the expected shape

AWS CLI deployment checks verify:

- AWS identity is available
- The REST API exists
- All 11 Lambda functions exist

The test that creates a request is disabled by default because it writes data.
It should only be enabled intentionally:

```powershell
$env:AWS_TEST_CREATE_DATA = "1"
```

### Why both test types matter

Local tests are fast, repeatable, and isolate Lambda logic. Live tests prove
that API Gateway, Lambda, IAM, DynamoDB, and the deployed URL are connected.
Neither type replaces the other.

---

## 11. Main user workflows

### Public help request

1. User opens the public request page.
2. User enters name, location, need, urgency, description, and optional phone.
3. JavaScript validates the form and description length.
4. API Gateway calls `submit_request`.
5. Lambda stores a pending request.
6. User sees a success confirmation.

### Admin workflow

1. Admin signs in.
2. Admin dashboard loads stats, requests, low-stock items, and centers.
3. Admin filters by status, urgency, or location.
4. Admin selects View to inspect complete details.
5. Admin selects Assign.
6. The active-center dropdown is loaded from `GET /centers?status=active`.
7. Admin selects one center.
8. `update_request_status` stores `assignedCenterId`.
9. Admin or staff later marks the request resolved.

### Inventory workflow

1. Staff signs in.
2. Staff dashboard loads the staff member's center.
3. Inventory is queried by `centerId`.
4. Staff updates a quantity.
5. Lambda recalculates the low-stock flag.
6. Admin sees low-stock items through the GSI-backed endpoint.

---

## 12. Important design decisions

### Why Lambda?

The workload is request-driven and relatively small. Lambda removes server
management and charges according to invocations and execution rather than
requiring an always-running server.

### Why API Gateway?

It provides HTTP routes, method/path routing, Lambda integration, deployment
stages, and browser-facing API access.

### Why DynamoDB?

The data is naturally represented as key-value/document records, and the
access patterns are known:

- Get a center by ID
- Query inventory by center
- Query requests by status and urgency
- Query low-stock items

DynamoDB GSIs support those access patterns without joining relational
tables.

### Why separate tables?

Separate tables make the data model clear for a small academic project.
Single-table DynamoDB designs can be efficient at scale but are harder to
explain and maintain for this scope.

### Why use GSIs?

A DynamoDB Query requires a key. GSIs allow queries by a different access
pattern:

- Status and urgency
- Low-stock flag
- Staff email
- Location and status

### Why UUIDs?

UUIDs give each center and request a unique identifier without depending on a
central counter. This works well with distributed serverless writes.

### Why UTC ISO timestamps?

UTC avoids timezone ambiguity. ISO 8601 strings are readable and sortable.

### Why `Decimal`?

DynamoDB's boto3 resource interface uses Decimal for numeric values to avoid
floating-point precision problems.

### Why use `Scan` in some functions?

The current dataset is small and the admin needs an overview of all centers
or requests. A scan is simple for the demonstration. At larger scale,
queries, GSIs, pagination, and narrower access patterns would be needed.

---

## 13. Security and limitations to explain honestly

### Current limitations

1. Authentication is demonstration-level:
   - SHA-256 hashing is used in the Lambda.
   - The returned token is a mock token.
   - API Gateway does not validate the token.
   - Browser localStorage role checks are not a secure authorization boundary.

2. The S3 website endpoint is HTTP:
   - Use CloudFront and HTTPS for production.

3. The public request endpoint is intentionally open:
   - A production system needs rate limiting, validation, abuse detection, and
     possibly CAPTCHA or WAF controls.

4. Some list and statistics operations use scans:
   - Appropriate for a small demonstration dataset.
   - Not ideal for very large tables.

5. The Lambda handlers return generic 500 errors:
   - This protects internal details from users.
   - CloudWatch contains the detailed exception for operators.

6. Pagination is not implemented:
   - The current project assumes a small dataset.
   - Production list endpoints should paginate DynamoDB results.

### Security improvements for production

- Amazon Cognito user pools
- API Gateway authorizer
- MFA
- HTTPS through CloudFront
- S3 private bucket with CloudFront Origin Access Control
- AWS WAF and throttling
- Strong password hashing managed by Cognito
- Conditional DynamoDB updates for valid state transitions
- Strict input validation and request size limits
- Separate IAM role per Lambda
- CloudWatch alarms and CloudTrail auditing
- Encryption and least-privilege resource policies

---

## 14. Likely evaluator questions and answers

### Q: Explain the project in one minute.

**Answer:** It is a serverless disaster-relief coordination system. Public
users submit requests, admins prioritize and assign them to relief centers,
and staff update center inventory. S3 hosts the frontend, API Gateway routes
requests, Lambda runs Python business logic, DynamoDB stores data, IAM
controls access, and CloudWatch stores execution logs.

### Q: What happens when a user submits a request?

**Answer:** The frontend sends `POST /requests` to API Gateway. API Gateway
invokes `submit_request`. The Lambda validates required fields and urgency,
generates a UUID, sets status to pending, writes the item to HelpRequests,
and returns HTTP 201.

### Q: How does assignment work?

**Answer:** The admin clicks Assign, chooses an active center loaded from
`GET /centers?status=active`, and the frontend sends
`PUT /requests/{requestId}` with status assigned and the selected
`assignedCenterId`. The update Lambda stores both values in DynamoDB.

### Q: Why did you not create a separate Lambda for View?

**Answer:** View is a read-only presentation of data already returned by the
list endpoint. The admin dashboard already has the complete request object,
so opening a client-side modal avoids an unnecessary database call. A
separate `GET /requests/{requestId}` endpoint could be added if individual
request retrieval were needed at larger scale.

### Q: Why did you use a separate Lambda for assignment?

**Answer:** Assignment is a state update, so it uses the existing
`update_request_status` Lambda. A separate Lambda would duplicate the same
DynamoDB update logic. Reusing the status-update endpoint keeps the API
smaller and the workflow consistent.

### Q: What is a GSI?

**Answer:** A Global Secondary Index is an alternate DynamoDB access path with
its own key schema. For example, StatusUrgency-index lets the application
query all pending requests and order them by numeric urgency instead of
looking them up by request ID.

### Q: Why is urgency stored as a number?

**Answer:** Numeric values sort naturally in DynamoDB. Critical urgency is 1,
so it appears before high 2, medium 3, and low 4. A separate label is stored
for human-readable display.

### Q: How is low stock calculated?

**Answer:** When inventory is updated, the Lambda compares quantity with the
threshold. It writes `lowStock = "true"` when quantity is below the
threshold. The LowStock-index then allows the admin to query all low-stock
items.

### Q: Why use Query instead of Scan?

**Answer:** Query is used when the partition key is known, such as querying
inventory by center ID or requests by status through a GSI. Scan reads the
whole table and is used only for small overview operations where no suitable
partition key is supplied.

### Q: What is the difference between IAM users and roles?

**Answer:** An IAM user represents a person or program that signs in to AWS.
An IAM role is assumed temporarily by a service such as Lambda. The role
gives the function only the permissions it needs to access DynamoDB and write
CloudWatch logs.

### Q: How does Lambda access DynamoDB?

**Answer:** The Lambda assumes its execution role. The role's permissions
policy allows specific DynamoDB actions on the required resources. The code
uses boto3's DynamoDB resource interface to call methods such as
`get_item`, `put_item`, `query`, `scan`, and `update_item`.

### Q: Where are Lambda errors recorded?

**Answer:** The Lambda prints diagnostic details, and AWS sends standard
output and errors to `/aws/lambda/<function-name>` in CloudWatch Logs. The
API response exposes a generic error while the detailed exception remains
available to the operator.

### Q: What happens if a Lambda has no permission?

**Answer:** DynamoDB raises an AWS authorization error, Lambda logs the
exception in CloudWatch, and the handler returns an internal-server-error
response. I would check the function's execution role, table ARN, region,
and action permissions.

### Q: Why does the frontend use S3?

**Answer:** The frontend is static HTML, CSS, and JavaScript, so S3 provides
simple and inexpensive object hosting without managing a web server. For
production HTTPS and private-bucket protection, I would put CloudFront in
front of S3.

### Q: Why API Gateway REST API instead of a direct database call?

**Answer:** The browser must not access DynamoDB directly with AWS
credentials. API Gateway provides a controlled HTTP boundary, and Lambda
contains the validation and business logic.

### Q: Is the current login production-ready?

**Answer:** No. It is intentionally a demonstration implementation. It uses
a mock token and browser-side role checks. A production implementation would
use Cognito for password management and tokens, then an API Gateway
authorizer to validate the token before Lambda runs.

### Q: How would you scale this project?

**Answer:** I would add pagination, replace broad scans with targeted queries
and GSIs, use Cognito and authorizers, add WAF and throttling, create
per-function IAM roles, use CloudFront for HTTPS, add alarms and structured
logs, and use conditional writes for safe request state transitions.

### Q: How did you test the application?

**Answer:** I used mocked local unit tests for Lambda validation and business
logic, JavaScript syntax checks, and opt-in live AWS tests for API Gateway
responses and deployed resource existence. This separates fast logic tests
from integration tests that can touch AWS.

### Q: Why are errors returned as 400 or 500?

**Answer:** HTTP 400 means the caller sent invalid or incomplete input.
HTTP 500 means an unexpected backend or AWS error occurred. The function
returns a safe generic message while logging the detailed error in
CloudWatch.

### Q: What is the role of API Gateway proxy integration?

**Answer:** Proxy integration passes the HTTP method, path parameters, query
parameters, headers, and body to Lambda in one event object. The Lambda then
returns the status code, headers, and body that API Gateway sends back to the
browser.

### Q: What happens if the user enters an invalid urgency?

**Answer:** The Lambda converts the value to an integer and only accepts 1,
2, 3, or 4. Invalid values return HTTP 400 and no DynamoDB write occurs.

### Q: What happens when an assigned request is resolved?

**Answer:** The admin or staff sends a status update with `resolved`. The
Lambda updates the request item and the dashboard reloads the request list
and statistics.

---

## 15. Showcase demonstration order

Use this order during the presentation:

1. Open the deployed S3 website.
2. Explain that the page is static frontend code.
3. Submit a safe sample help request.
4. Show the success response and request ID.
5. Sign in as admin.
6. Show dashboard statistics and the new pending request.
7. Click View and explain that the details modal uses the loaded request.
8. Click Assign and select a relief center.
9. Show the status changing to assigned.
10. Open the center dashboard.
11. Show inventory and update one quantity.
12. Show the low-stock effect if appropriate.
13. Open the AWS Console and show:
    - S3 bucket
    - API Gateway routes
    - Lambda functions
    - DynamoDB tables
    - IAM role
    - CloudWatch log group
14. Finish with the tests and production-improvement discussion.

Use fake or clearly labelled test data. Do not show real passwords, access
keys, secret keys, session tokens, or private user information.

---

## 16. Final points to remember

If you forget a detail, return to the architecture:

```text
Frontend -> API Gateway -> Lambda -> DynamoDB
                         |
                         -> CloudWatch Logs
```

The most important explanations are:

1. Why serverless services were selected.
2. How the request moves through the system.
3. How DynamoDB keys and GSIs support the queries.
4. How IAM roles protect AWS resources.
5. How CloudWatch helps diagnose Lambda errors.
6. What the current authentication limitation is.
7. What improvements would be needed for production.

