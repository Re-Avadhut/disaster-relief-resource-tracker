# Disaster Relief Resource Tracker

## Beginner AWS Deployment Tutorial

This guide deploys the current project as a small serverless application using:

- Amazon DynamoDB for data storage
- AWS Lambda for Python backend functions
- Amazon API Gateway REST API for HTTP endpoints
- Amazon S3 for the static HTML/CSS/JavaScript frontend

The application has no build step. You upload the frontend files as they are.

> **Important:** This project is suitable for learning and demonstrations. It is not production authentication. The current login Lambda creates a mock token, but API Gateway/Lambda does not validate that token. Use Amazon Cognito and an API Gateway authorizer before using this application with real personal data.

---

## 1. What You Need Before Starting

### 1.1 AWS account

You need:

- An AWS account with a verified email address
- A payment method on the account
- Access to the AWS Management Console
- A phone number for account verification if AWS requests one

AWS may require identity verification before some services become available.

### 1.2 Project files

Your project folder is:

```text
AWS Project/
├── dynamodb-schema.json
├── iam-permissions.md
├── frontend/
└── lambda/
```

Do not upload the entire project folder to S3. Only the contents of `frontend/` belong in the website bucket.

### 1.3 Choose one AWS Region

Choose one region and use it for every resource. For example:

```text
us-east-1 (US East - N. Virginia)
ap-south-1 (Asia Pacific - Mumbai)
```

The region does not have to match your physical location, but using one region keeps the project easier to understand. In the AWS Console, check the region selector in the upper-right corner before creating each resource.

Write down your choice:

```text
AWS_REGION = ____________________
```

---

## 2. Secure the New AWS Account First

Do this before creating application resources.

### 2.1 Protect the root account

1. Sign in at <https://console.aws.amazon.com/>.
2. Open the account menu in the upper-right corner.
3. Open **Security credentials**.
4. Enable multi-factor authentication (MFA) for the root user.
5. Do not create root access keys.
6. Do not use the root user for everyday development.

### 2.2 Turn on billing alerts

1. Open **Billing and Cost Management**.
2. Open **Billing preferences**.
3. Enable email delivery of billing alerts.
4. Open **Budgets**.
5. Create a monthly cost budget with an amount you are comfortable with, such as `$5` or `$10`.
6. Add your email address for alerts.

Some AWS services can generate charges even when they are only used for testing. Delete resources when you finish.

### 2.3 Create an administrator IAM user

For a first learning deployment, create an IAM user rather than using root:

1. Open **IAM**.
2. Select **Users**.
3. Select **Create user**.
4. Choose a name such as `project-admin`.
5. Enable console access.
6. Set a strong password.
7. Enable MFA for this user.
8. Attach `AdministratorAccess` temporarily if this is only a personal learning account.
9. Sign out of root and sign in as this IAM user.

For a real organization, use IAM Identity Center and avoid giving broad administrator permissions to daily users.

---

## 3. Prepare the Project Locally

Open PowerShell in the project folder:

```powershell
Set-Location "C:\Users\Avadhut\Documents\Development\Simple Projects\Simple-Projects\OpenCode\AWS Project"
```

Run the existing syntax checks:

```powershell
python -m compileall lambda
Get-ChildItem frontend/js/*.js | ForEach-Object { node --check $_.FullName }
```

You should see the Python files compile without errors. The JavaScript checks should also complete without syntax errors.

### 3.1 Optional: install and configure AWS CLI

The Console procedure below is enough. The AWS CLI is optional, but useful later.

Install the AWS CLI from:

<https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>

Verify it:

```powershell
aws --version
```

Configure it only if you created access credentials for your IAM user:

```powershell
aws configure
```

Enter:

```text
AWS Access Key ID:       your access key
AWS Secret Access Key:   your secret key
Default region name:     your chosen region
Default output format:  json
```

Never put AWS keys in this project, in the frontend, or in a public repository.

---

## 4. Create the DynamoDB Tables

The Lambda code expects these exact table names and key names. A typo here will cause runtime errors.

Open **DynamoDB** in the AWS Console, make sure the correct region is selected, and choose **Create table**.

For the first deployment, choose **On-demand** capacity. It is simpler for a small demonstration and charges based on usage.

### 4.1 Create `ReliefCenters`

1. Select **Create table**.
2. Table name: `ReliefCenters`
3. Partition key: `centerId`
4. Key type: `String`
5. Capacity mode: **On-demand**
6. Leave encryption enabled.
7. Create the table.

After it is created, add the GSI:

1. Open the `ReliefCenters` table.
2. Open the **Indexes** tab.
3. Choose **Create index**.
4. Partition key: `staffEmail`
5. Index name: `StaffEmail-index`
6. Projection: **All**
7. Create the index.

### 4.2 Create `Inventory`

1. Create another table.
2. Table name: `Inventory`
3. Partition key: `centerId` (`String`)
4. Sort key: `resourceType` (`String`)
5. Capacity mode: **On-demand**
6. Create the table.

Add the GSI:

- Partition key: `lowStock`
- Sort key: `resourceType`
- Index name: `LowStock-index`
- Projection: **All**

The code stores `lowStock` as the string values `true` and `false`, not as DynamoDB Boolean values. Keep that distinction when testing manually.

### 4.3 Create `HelpRequests`

1. Create another table.
2. Table name: `HelpRequests`
3. Partition key: `requestId` (`String`)
4. Capacity mode: **On-demand**
5. Create the table.

Add these indexes:

#### `StatusUrgency-index`

- Partition key: `status` (`String`)
- Sort key: `urgency` (`Number`)
- Projection: **All**

#### `LocationStatus-index`

- Partition key: `location` (`String`)
- Sort key: `status` (`String`)
- Projection: **All**

### 4.4 Create `Users`

1. Create another table.
2. Table name: `Users`
3. Partition key: `email` (`String`)
4. Capacity mode: **On-demand**
5. Create the table.

### 4.5 Verify DynamoDB setup

Before moving on, check that the Tables page shows exactly:

```text
ReliefCenters
Inventory
HelpRequests
Users
```

Also check that every listed GSI has status **Active**. Do not deploy Lambdas until the indexes are active.

---

## 5. Create IAM Roles for Lambda

Every Lambda needs an execution role. The role gives the Lambda permission to call DynamoDB.

For a beginner deployment, you can use two roles as described in [iam-permissions.md](iam-permissions.md). Separate roles are better than giving every function unrestricted access.

### 5.1 Create the first role

1. Open **IAM**.
2. Select **Roles**.
3. Select **Create role**.
4. Trusted entity type: **AWS service**.
5. Use case: **Lambda**.
6. Select **Next**.
7. Attach `AWSLambdaBasicExecutionRole`.
8. Select **Next**.
9. Role name: `LambdaReliefCenterRole`.
10. Create the role.

`AWSLambdaBasicExecutionRole` allows Lambda to write logs to CloudWatch. You still need a DynamoDB policy.

### 5.2 Add the DynamoDB policy

Open the new role:

1. Select **Add permissions**.
2. Select **Create inline policy**.
3. Open the **JSON** editor.
4. Replace the contents with the policy below.
5. Replace `YOUR_REGION` with your region, such as `ap-south-1`.
6. Replace `YOUR_ACCOUNT_ID` with your AWS account ID.
7. Name the policy `ReliefCenterDynamoDBAccess`.
8. Create the policy.

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
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/ReliefCenters",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/ReliefCenters/index/*",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/Inventory",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/Inventory/index/*",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/Users",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/Users/index/*",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/HelpRequests",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/HelpRequests/index/*"
      ]
    }
  ]
}
```

### 5.3 Create the request role

Repeat the process:

- Role name: `LambdaRequestRole`
- Trusted entity: Lambda
- Managed policy: `AWSLambdaBasicExecutionRole`
- Inline policy name: `RequestDynamoDBAccess`

Use this JSON after replacing the region and account ID:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/HelpRequests",
        "arn:aws:dynamodb:YOUR_REGION:YOUR_ACCOUNT_ID:table/HelpRequests/index/*"
      ]
    }
  ]
}
```

### 5.4 Which role belongs to which Lambda?

Attach `LambdaReliefCenterRole` to:

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

Attach `LambdaRequestRole` to:

```text
submit_request
list_requests
update_request_status
```

The first time you create each Lambda, select the existing role instead of creating a new one.

---

## 6. Create the Lambda Functions

Create one Lambda function for each Python file in the local `lambda` folder.

Open **Lambda** in the AWS Console and select **Create function**.

Repeat these steps for every function:

1. Select **Author from scratch**.
2. Function name: use the filename without `.py`, for example `login_user`.
3. Runtime: choose a current supported Python runtime, such as Python 3.11 or Python 3.12.
4. Architecture: `x86_64` is fine.
5. Expand **Change default execution role**.
6. Select **Use an existing role**.
7. Select the correct role from Section 5.
8. Create the function.
9. In the function page, open the **Code** tab.
10. Open the inline editor file, usually `lambda_function.py`.
11. Delete the sample code.
12. Open the matching local Python file.
13. Copy its complete contents into the Lambda editor.
14. Select **Deploy**.

The function handler should be:

```text
lambda_function.lambda_handler
```

If you upload a file named `login_user.py` instead of using the inline editor, change the handler to:

```text
login_user.lambda_handler
```

For this project, using the inline editor with the code pasted into `lambda_function.py` is the easiest method.

### Function name mapping

| Local file                 | Lambda function name    | API route                           |
| -------------------------- | ----------------------- | ----------------------------------- |
| `create_center.py`         | `create_center`         | `POST /centers`                     |
| `get_center.py`            | `get_center`            | `GET /centers/{centerId}`           |
| `list_centers.py`          | `list_centers`          | `GET /centers`                      |
| `update_inventory.py`      | `update_inventory`      | `PUT /centers/{centerId}/inventory` |
| `get_inventory.py`         | `get_inventory`         | `GET /centers/{centerId}/inventory` |
| `get_low_stock.py`         | `get_low_stock`         | `GET /inventory/low-stock`          |
| `submit_request.py`        | `submit_request`        | `POST /requests`                    |
| `list_requests.py`         | `list_requests`         | `GET /requests`                     |
| `update_request_status.py` | `update_request_status` | `PUT /requests/{requestId}`         |
| `login_user.py`            | `login_user`            | `POST /auth/login`                  |
| `get_stats.py`             | `get_stats`             | `GET /stats`                        |

### 6.1 Test a Lambda directly

Before API Gateway, test at least one function:

1. Open the `submit_request` Lambda.
2. Select the **Test** tab.
3. Create a new test event.
4. Use this event:

```json
{
  "body": "{\"name\":\"Test User\",\"location\":\"Test Area\",\"needType\":\"food\",\"urgency\":1,\"description\":\"Test request\",\"contactPhone\":\"1234567890\"}"
}
```

5. Run the test.
6. A successful result should have `statusCode` equal to `201`.

If it fails, open the **Monitor** tab and view the CloudWatch logs. Common causes are a wrong table name, wrong region, missing IAM permission, or a missing GSI.

---

## 7. Create the API Gateway REST API

The frontend expects a REST API URL and the Lambda code expects API Gateway REST proxy events. Use **REST API**, not HTTP API, for this tutorial.

### 7.1 Create the API

1. Open **API Gateway**.
2. Select **Create API**.
3. Under **REST API**, choose **Build**.
4. Select **New API**.
5. API name: `DisasterReliefTrackerAPI`.
6. Endpoint type: **Regional**.
7. Create the API.

### 7.2 Create each route

For each route below, create the resource and method, then connect it to the listed Lambda.

```text
POST /auth/login                         login_user
POST /centers                             create_center
GET  /centers                             list_centers
GET  /centers/{centerId}                  get_center
GET  /centers/{centerId}/inventory        get_inventory
PUT  /centers/{centerId}/inventory        update_inventory
GET  /inventory/low-stock                 get_low_stock
POST /requests                            submit_request
GET  /requests                            list_requests
PUT  /requests/{requestId}                 update_request_status
GET  /stats                               get_stats
```

For each method:

1. Create the resource path if it does not exist.
2. Select **Create method**.
3. Choose the HTTP method.
4. Integration type: **Lambda Function**.
5. Enable **Use Lambda Proxy integration**.
6. Choose the correct region.
7. Choose the correct Lambda function.
8. Save the method.
9. Approve the permission prompt if AWS shows one.

### 7.3 Create path parameters correctly

These paths require a variable segment:

```text
/centers/{centerId}
/centers/{centerId}/inventory
/requests/{requestId}
```

When creating the resource, select **Configure as proxy resource** only if you understand that it changes routing. For this project, create normal resources and use a path part named exactly:

```text
{centerId}
{requestId}
```

The names must match the Lambda code.

### 7.4 Configure CORS

The Lambda responses already include CORS response headers, but the browser also sends an `OPTIONS` preflight request for JSON POST/PUT calls. Configure CORS on every resource/method:

1. Select a resource in API Gateway.
2. Select **Enable CORS** or **CORS configuration**.
3. Allow origin: `*` for this learning deployment.
4. Allow headers:

```text
Content-Type,Authorization
```

5. Allow methods used by the resource.
6. Confirm the CORS changes.
7. Repeat for all resources or use the API-level CORS configuration if available.

For a real deployment, replace `*` with the exact website origin.

### 7.5 Deploy the API

1. Select **Actions** or **Deploy API**.
2. Create a new stage named `prod`.
3. Deploy.
4. Copy the invoke URL. It looks similar to:

```text
https://abc123.execute-api.us-east-1.amazonaws.com/prod
```

Save it:

```text
API_BASE_URL = https://________________.execute-api.________________.amazonaws.com/prod
```

---

## 8. Configure the Frontend

Open:

```text
frontend/js/api.js
```

Find:

```js
const API_BASE_URL = "YOUR_API_GATEWAY_INVOKE_URL_HERE";
```

Replace it with your API Gateway URL. Do not add a trailing slash:

```js
const API_BASE_URL = "https://abc123.execute-api.us-east-1.amazonaws.com/prod";
```

Save the file.

Run the JavaScript check again:

```powershell
Get-ChildItem frontend/js/*.js | ForEach-Object { node --check $_.FullName }
```

---

## 9. Create the First Admin User

The login screen needs an admin user, but this project does not include a public admin-registration screen. Create the first admin directly in DynamoDB.

### 9.1 Generate the password hash

The current code uses SHA-256 for the demo password hash. Run this locally in PowerShell, replacing `YourStrongPasswordHere`:

```powershell
python -c "import hashlib; print(hashlib.sha256(b'YourStrongPasswordHere').hexdigest())"
```

Copy the printed hash.

> This is a demonstration setup. For production, do not use this custom password system. Use Cognito.

### 9.2 Insert the admin item

1. Open DynamoDB.
2. Open the `Users` table.
3. Select **Explore table items**.
4. Select **Create item**.
5. Add this item in JSON view:

```json
{
  "email": "admin@example.com",
  "passwordHash": "PASTE_THE_SHA256_HASH_HERE",
  "name": "System Administrator",
  "role": "admin",
  "createdAt": "2026-09-10T00:00:00Z"
}
```

6. Save the item.

Use the email and original password, not the hash, on the login page.

### 9.3 Important admin behavior

The admin can:

- register relief centers
- create staff accounts indirectly through center registration
- view request statistics
- view low-stock inventory
- assign requests
- resolve requests

The first admin user must be seeded manually because there is no admin creation Lambda or form.

---

## 10. Create and Upload the S3 Website

### 10.1 Create the bucket

1. Open **S3**.
2. Select **Create bucket**.
3. Choose a globally unique bucket name, such as:

```text
disaster-relief-tracker-yourname-2026
```

4. Select the same AWS region used by the other resources.
5. Leave ACLs disabled unless AWS specifically requires otherwise.
6. For this simple public website tutorial, clear **Block all public access** and acknowledge the warning.
7. Create the bucket.

A public bucket is acceptable only for this simple static demo. For a real website, use CloudFront with Origin Access Control instead of exposing the bucket publicly.

### 10.2 Enable static website hosting

1. Open the bucket.
2. Open **Properties**.
3. Find **Static website hosting**.
4. Select **Edit**.
5. Enable it.
6. Hosting type: **Host a static website**.
7. Index document: `index.html`
8. Save changes.

### 10.3 Upload the frontend

From the local project folder:

```powershell
aws s3 sync frontend s3://YOUR_BUCKET_NAME
```

Or use the Console:

1. Open the bucket.
2. Select **Upload**.
3. Select the files and folders inside `frontend/`.
4. Upload them while preserving this structure:

```text
index.html
center-dashboard.html
public-request.html
admin-dashboard.html
css/style.css
js/api.js
js/auth.js
js/login.js
js/center-dashboard.js
js/public-request.js
js/admin-dashboard.js
```

Do not upload the `frontend` folder as an extra top-level folder. `index.html` must be at the bucket root.

### 10.4 Add the bucket policy

Open **Permissions**, then **Bucket policy**, and paste this policy. Replace `YOUR_BUCKET_NAME`:

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

If AWS refuses the policy, check that Block Public Access was disabled for this bucket and that the bucket name is correct.

### 10.5 Open the website

1. Return to **Properties**.
2. Find the **Static website hosting** URL.
3. Open the URL in a new browser tab.
4. The login page should load.

Use the public request link to test the unauthenticated workflow.

---

## 11. Test the Complete Application

Test in this order because each step creates data used by the next one.

### 11.1 Test the public request form

1. Open the website.
2. Select **Submit a help request**.
3. Complete every required field.
4. Submit the form.
5. Confirm that a success message appears.
6. In DynamoDB, open `HelpRequests` and confirm that an item exists.

If the browser reports a CORS error, check API Gateway CORS and redeploy the API after changing it.

### 11.2 Test admin login

1. Open `index.html` from the deployed website.
2. Enter the seeded admin email and original password.
3. Confirm that `admin-dashboard.html` opens.
4. Confirm that stats, requests, low-stock items, and centers load.

If login returns an internal error, inspect the `login_user` CloudWatch log and verify the `Users` table item.

### 11.3 Register a relief center

From the admin dashboard:

1. Enter a center name.
2. Enter its location and contact information.
3. Enter a unique staff email.
4. Enter a temporary staff password.
5. Submit the form.

This creates:

- one `ReliefCenters` item
- one `Users` item with role `staff`
- four `Inventory` items: food, water, medical, shelter

### 11.4 Test staff login and inventory

1. Sign out.
2. Open the login page.
3. Login using the staff email and password created by the admin.
4. Confirm that the center dashboard opens.
5. Update food, water, medical, or shelter quantities.
6. Confirm that low-stock values change when quantity crosses the threshold.

### 11.5 Test assignment and resolution

1. Create another public help request.
2. Open the admin dashboard.
3. Select **Assign**.
4. Confirm the request status changes to `assigned`.
5. Select **Resolve**.
6. Confirm the request status changes to `resolved`.
7. In DynamoDB, verify that `assignedCenterId` is stored.

---

## 12. Troubleshooting Guide

### Browser says `Failed to fetch`

Check:

- `API_BASE_URL` is correct
- API Gateway stage is included, such as `/prod`
- the API was redeployed after route or CORS changes
- the browser can reach the API URL directly
- Lambda has permission to access DynamoDB

### Browser reports a CORS error

Check:

- API Gateway has `OPTIONS` handling or CORS enabled
- `Content-Type` and `Authorization` are allowed headers
- the API was redeployed after changing CORS
- the Lambda response contains CORS headers

### Lambda returns `ResourceNotFoundException`

Usually one of these is wrong:

- table name is misspelled
- Lambda is deployed in a different region from DynamoDB
- a GSI name is misspelled
- the DynamoDB table or index is not active yet

### Lambda returns `AccessDeniedException`

Open the Lambda execution role and verify:

- `AWSLambdaBasicExecutionRole` is attached
- the DynamoDB inline policy is attached
- region and account ID in the policy are correct
- table and index ARNs are correct

### Login says invalid credentials

Check:

- the `Users` item exists
- the email is the exact partition key value
- the stored `passwordHash` is the SHA-256 hash of the password you typed
- the user `role` is `admin` or `staff`

### Admin dashboard shows no requests

Check:

- the public form successfully returned a success message
- an item exists in `HelpRequests`
- the `list_requests` Lambda role includes `Scan`
- the API route is `GET /requests`, not `POST /requests`

### Low-stock section fails

Check:

- `Inventory` has the `LowStock-index`
- its partition key is `lowStock`
- the Lambda role includes `Query` on the index
- values are stored as the strings `true` and `false`

### S3 gives `403 Forbidden`

Check:

- `index.html` is at the bucket root
- the bucket website hosting setting is enabled
- the bucket policy uses the correct bucket name
- Block Public Access is disabled for this demo bucket

### Changes do not appear after uploading frontend files

Refresh with `Ctrl+F5`. If using a CDN later, invalidate the CloudFront cache.

---

## 13. CloudWatch Logs

Every Lambda automatically writes logs when its role includes `AWSLambdaBasicExecutionRole`.

To view logs:

1. Open **Lambda**.
2. Open the function.
3. Select **Monitor**.
4. Select **View CloudWatch logs**.
5. Open the newest log stream.

Look for:

- table/index not found errors
- access denied errors
- Python exceptions
- malformed event data

Do not log passwords, tokens, or personal contact information.

---

## 14. Updating the Application Later

### Update a Lambda

1. Edit the local Python file.
2. Run:

```powershell
python -m compileall lambda
```

3. Open the matching Lambda in AWS.
4. Replace the inline editor code.
5. Select **Deploy**.

### Update the frontend

1. Edit the local HTML, CSS, or JavaScript file.
2. Run the JavaScript syntax check:

```powershell
Get-ChildItem frontend/js/*.js | ForEach-Object { node --check $_.FullName }
```

3. Upload the changed files:

```powershell
aws s3 sync frontend s3://YOUR_BUCKET_NAME
```

4. Refresh the browser with `Ctrl+F5`.

### Change API routes

Whenever you add or change an API Gateway route:

1. Update the Lambda.
2. Update API Gateway.
3. Enable or update CORS.
4. Deploy the API to the `prod` stage again.
5. Confirm the invoke URL has the correct stage.

---

## 15. Delete Everything When Finished

To prevent ongoing charges, delete resources after the demonstration.

### Delete the S3 website

1. Empty the bucket.
2. Delete the bucket.

CLI option:

```powershell
aws s3 rb s3://YOUR_BUCKET_NAME --force
```

### Delete API Gateway

Open API Gateway, select `DisasterReliefTrackerAPI`, and delete it.

### Delete Lambda functions

Delete all eleven functions.

### Delete IAM roles

Delete the inline policies first if AWS requires it, then delete:

```text
LambdaReliefCenterRole
LambdaRequestRole
```

Keep your personal IAM administrator user if you still need the account.

### Delete DynamoDB tables

Delete:

```text
ReliefCenters
Inventory
HelpRequests
Users
```

This permanently deletes the project data.

### Check billing

Open **Billing and Cost Management** and confirm that no unexpected resources remain in any region. Also check other regions if you accidentally created resources there.

---

## 16. Deployment Checklist

Use this as a final checklist:

- [ ] Root account has MFA
- [ ] Billing budget and alerts are configured
- [ ] One AWS region has been selected
- [ ] `ReliefCenters` table exists
- [ ] `Inventory` table exists
- [ ] `HelpRequests` table exists
- [ ] `Users` table exists
- [ ] All required GSIs are active
- [ ] Lambda execution roles exist
- [ ] Eleven Lambda functions are deployed
- [ ] Lambda handlers are set correctly
- [ ] Lambda test invocation works
- [ ] API Gateway REST API exists
- [ ] All eleven routes are connected
- [ ] CORS is enabled
- [ ] API is deployed to `prod`
- [ ] `frontend/js/api.js` contains the API URL
- [ ] The first admin user exists in `Users`
- [ ] S3 website hosting is enabled
- [ ] Frontend files are at the bucket root
- [ ] Public request submission works
- [ ] Admin login works
- [ ] Center registration works
- [ ] Staff login works
- [ ] Inventory updates work
- [ ] Request assignment and resolution work
- [ ] CloudWatch logs have been checked
- [ ] Unused resources are deleted after testing

---

## 17. Recommended Improvements After This Tutorial

Before calling this production-ready, replace the simplified authentication with:

- Amazon Cognito User Pool
- Cognito JWT tokens
- API Gateway Cognito authorizer
- HTTPS custom domain, usually through CloudFront
- private S3 bucket with CloudFront Origin Access Control
- password reset and account recovery
- input validation and rate limiting
- DynamoDB pagination
- conditional writes for concurrent inventory updates
- CloudWatch alarms and structured logging
- backups and retention policies

The current deployment is a useful learning path for understanding how a browser, API Gateway, Lambda, DynamoDB, IAM, and S3 fit together.
