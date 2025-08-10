# Complete Manual Setup Guide - Excel Template Mapper

## 📋 Overview

This guide walks you through manually setting up the complete Excel Template Mapper infrastructure using AWS CLI commands. **NO API GATEWAY** - using Lambda Function URLs instead.

---

## ⚠️ CRITICAL SECURITY NOTICE

**NEVER use the credentials you shared earlier!** They are compromised. Follow these steps:

1. **Delete compromised keys**:
   ```bash
   aws iam delete-access-key --access-key-id AKIAZVHK6XPIQ4PT23MC --user-name YOUR_USERNAME
   ```

2. **Create new credentials**:
   ```bash
   aws iam create-access-key --user-name YOUR_USERNAME
   ```

3. **Configure AWS CLI**:
   ```bash
   aws configure
   # Enter your NEW credentials
   ```

---

## 🏗️ Architecture Overview

```
GitHub Repository
    ↓
AWS Lambda Function (with Function URL)
    ↓
S3 Buckets (uploads, processed, templates)
    ↓
DynamoDB Tables (sessions, templates, jobs)
    ↓
CloudWatch (logging & monitoring)
    ↓
Frontend (React - deployed to Amplify)
```

---

## 📦 Step 1: GitHub Repository Setup

### 1.1 Create GitHub Repository

```bash
# Navigate to your project
cd /Users/kartikd/Downloads/final\ amplify/excel-template-mapper-final

# Initialize git (if not done)
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Excel Template Mapper with Lambda Function URLs

- Complete Lambda function for Excel processing
- S3 configuration for file storage
- DynamoDB schema for data management
- Frontend React application
- No API Gateway - using Lambda Function URLs
- CloudWatch monitoring setup"

# Create GitHub repository (replace YOUR_USERNAME)
gh repo create excel-template-mapper --public --description "AI-powered Excel template mapper with serverless AWS architecture - Lambda Function URLs"

# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/excel-template-mapper.git
git branch -M main
git push -u origin main
```

### 1.2 Verify GitHub Repository

✅ Check these files are uploaded:
- `amplify/backend/function/excelMapper/src/index.py` (Lambda function)
- `frontend/src/` (React application)
- `infrastructure/` (AWS CLI scripts)
- `README.md` and documentation
- `.gitignore` (properly configured)

---

## 🗄️ Step 2: Create DynamoDB Tables

### 2.1 Sessions Table

```bash
aws dynamodb create-table \
    --table-name ExcelMapper_Sessions \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --time-to-live-specification \
        AttributeName=ttl,Enabled=true \
    --point-in-time-recovery-specification \
        PointInTimeRecoveryEnabled=true \
    --tags \
        Key=Environment,Value=dev \
        Key=Project,Value=excel-template-mapper
```

### 2.2 Templates Table

```bash
aws dynamodb create-table \
    --table-name ExcelMapper_Templates \
    --attribute-definitions \
        AttributeName=id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
        AttributeName=usage_count,AttributeType=N \
    --key-schema \
        AttributeName=id,KeyType=HASH \
    --global-secondary-indexes \
        IndexName=CreatedAtIndex,KeySchema=[{AttributeName=created_at,KeyType=HASH}],Projection={ProjectionType=ALL} \
        IndexName=UsageCountIndex,KeySchema=[{AttributeName=usage_count,KeyType=HASH}],Projection={ProjectionType=ALL} \
    --billing-mode PAY_PER_REQUEST \
    --point-in-time-recovery-specification \
        PointInTimeRecoveryEnabled=true \
    --tags \
        Key=Environment,Value=dev \
        Key=Project,Value=excel-template-mapper
```

### 2.3 Tag Templates Table

```bash
aws dynamodb create-table \
    --table-name ExcelMapper_TagTemplates \
    --attribute-definitions \
        AttributeName=id,AttributeType=S \
    --key-schema \
        AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --point-in-time-recovery-specification \
        PointInTimeRecoveryEnabled=true \
    --tags \
        Key=Environment,Value=dev \
        Key=Project,Value=excel-template-mapper
```

### 2.4 Processing Jobs Table

```bash
aws dynamodb create-table \
    --table-name ExcelMapper_ProcessingJobs \
    --attribute-definitions \
        AttributeName=job_id,AttributeType=S \
        AttributeName=status,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=job_id,KeyType=HASH \
    --global-secondary-indexes \
        IndexName=StatusIndex,KeySchema=[{AttributeName=status,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}],Projection={ProjectionType=ALL} \
    --billing-mode PAY_PER_REQUEST \
    --time-to-live-specification \
        AttributeName=ttl,Enabled=true \
    --point-in-time-recovery-specification \
        PointInTimeRecoveryEnabled=true \
    --tags \
        Key=Environment,Value=dev \
        Key=Project,Value=excel-template-mapper
```

### 2.5 Verify DynamoDB Tables

```bash
# Check all tables are created
aws dynamodb list-tables

# Check specific table status
aws dynamodb describe-table --table-name ExcelMapper_Sessions --query 'Table.TableStatus'
aws dynamodb describe-table --table-name ExcelMapper_Templates --query 'Table.TableStatus'
aws dynamodb describe-table --table-name ExcelMapper_TagTemplates --query 'Table.TableStatus'
aws dynamodb describe-table --table-name ExcelMapper_ProcessingJobs --query 'Table.TableStatus'
```

---

## 🪣 Step 3: Create S3 Buckets

### 3.1 Get Your AWS Account ID

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"
```

### 3.2 Create Upload Bucket

```bash
UPLOAD_BUCKET="excel-mapper-uploads-dev-${AWS_ACCOUNT_ID}"

aws s3 mb s3://$UPLOAD_BUCKET --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $UPLOAD_BUCKET \
    --versioning-configuration Status=Enabled

# Configure lifecycle policy
cat > /tmp/upload-lifecycle.json << EOF
{
    "Rules": [
        {
            "ID": "DeleteOldUploads",
            "Status": "Enabled",
            "Expiration": {
                "Days": 7
            }
        },
        {
            "ID": "DeleteIncompleteMultipartUploads",
            "Status": "Enabled",
            "AbortIncompleteMultipartUpload": {
                "DaysAfterInitiation": 1
            }
        }
    ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket $UPLOAD_BUCKET \
    --lifecycle-configuration file:///tmp/upload-lifecycle.json

# Configure CORS
cat > /tmp/cors-config.json << EOF
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
            "AllowedOrigins": ["*"],
            "ExposedHeaders": ["ETag", "x-amz-meta-*"],
            "MaxAgeSeconds": 3600
        }
    ]
}
EOF

aws s3api put-bucket-cors \
    --bucket $UPLOAD_BUCKET \
    --cors-configuration file:///tmp/cors-config.json

# Block public access
aws s3api put-public-access-block \
    --bucket $UPLOAD_BUCKET \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### 3.3 Create Processed Files Bucket

```bash
PROCESSED_BUCKET="excel-mapper-processed-dev-${AWS_ACCOUNT_ID}"

aws s3 mb s3://$PROCESSED_BUCKET --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $PROCESSED_BUCKET \
    --versioning-configuration Status=Enabled

# Configure lifecycle policy (30 days retention)
cat > /tmp/processed-lifecycle.json << EOF
{
    "Rules": [
        {
            "ID": "DeleteOldProcessed",
            "Status": "Enabled",
            "Expiration": {
                "Days": 30
            }
        }
    ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket $PROCESSED_BUCKET \
    --lifecycle-configuration file:///tmp/processed-lifecycle.json

# Configure CORS
aws s3api put-bucket-cors \
    --bucket $PROCESSED_BUCKET \
    --cors-configuration file:///tmp/cors-config.json

# Block public access
aws s3api put-public-access-block \
    --bucket $PROCESSED_BUCKET \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### 3.4 Create Templates Bucket

```bash
TEMPLATES_BUCKET="excel-mapper-templates-dev-${AWS_ACCOUNT_ID}"

aws s3 mb s3://$TEMPLATES_BUCKET --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $TEMPLATES_BUCKET \
    --versioning-configuration Status=Enabled

# Configure CORS
aws s3api put-bucket-cors \
    --bucket $TEMPLATES_BUCKET \
    --cors-configuration file:///tmp/cors-config.json

# Block public access
aws s3api put-public-access-block \
    --bucket $TEMPLATES_BUCKET \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### 3.5 Verify S3 Buckets

```bash
# List all buckets
aws s3 ls | grep excel-mapper

# Check bucket configurations
aws s3api get-bucket-cors --bucket $UPLOAD_BUCKET
aws s3api get-bucket-versioning --bucket $UPLOAD_BUCKET
aws s3api get-bucket-lifecycle-configuration --bucket $UPLOAD_BUCKET
```

---

## 🔐 Step 4: Create IAM Role for Lambda

### 4.1 Create Trust Policy

```bash
cat > /tmp/lambda-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
```

### 4.2 Create IAM Role

```bash
aws iam create-role \
    --role-name excel-mapper-lambda-execution-role \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Execution role for Excel Template Mapper Lambda function"
```

### 4.3 Attach Basic Lambda Execution Policy

```bash
aws iam attach-role-policy \
    --role-name excel-mapper-lambda-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### 4.4 Create Custom Policy for S3 and DynamoDB Access

```bash
cat > /tmp/lambda-custom-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::excel-mapper-uploads-dev-${AWS_ACCOUNT_ID}/*",
                "arn:aws:s3:::excel-mapper-processed-dev-${AWS_ACCOUNT_ID}/*",
                "arn:aws:s3:::excel-mapper-templates-dev-${AWS_ACCOUNT_ID}/*",
                "arn:aws:s3:::excel-mapper-uploads-dev-${AWS_ACCOUNT_ID}",
                "arn:aws:s3:::excel-mapper-processed-dev-${AWS_ACCOUNT_ID}",
                "arn:aws:s3:::excel-mapper-templates-dev-${AWS_ACCOUNT_ID}"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:${AWS_ACCOUNT_ID}:table/ExcelMapper_Sessions",
                "arn:aws:dynamodb:us-east-1:${AWS_ACCOUNT_ID}:table/ExcelMapper_Templates",
                "arn:aws:dynamodb:us-east-1:${AWS_ACCOUNT_ID}:table/ExcelMapper_TagTemplates",
                "arn:aws:dynamodb:us-east-1:${AWS_ACCOUNT_ID}:table/ExcelMapper_ProcessingJobs",
                "arn:aws:dynamodb:us-east-1:${AWS_ACCOUNT_ID}:table/ExcelMapper_Templates/index/*",
                "arn:aws:dynamodb:us-east-1:${AWS_ACCOUNT_ID}:table/ExcelMapper_ProcessingJobs/index/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
                "logs:DescribeLogGroups"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name excel-mapper-lambda-policy \
    --policy-document file:///tmp/lambda-custom-policy.json \
    --description "Custom policy for Excel Template Mapper Lambda function"
```

### 4.5 Attach Custom Policy to Role

```bash
aws iam attach-role-policy \
    --role-name excel-mapper-lambda-execution-role \
    --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/excel-mapper-lambda-policy
```

### 4.6 Verify IAM Role

```bash
# Check role exists
aws iam get-role --role-name excel-mapper-lambda-execution-role

# List attached policies
aws iam list-attached-role-policies --role-name excel-mapper-lambda-execution-role
```

---

## 📦 Step 5: Prepare Lambda Deployment Package

### 5.1 Create Lambda Package

```bash
cd /Users/kartikd/Downloads/final\ amplify/excel-template-mapper-final

# Create build directory
mkdir -p build/lambda-package

# Copy Lambda source code
cp amplify/backend/function/excelMapper/src/index.py build/lambda-package/
cp amplify/backend/function/excelMapper/src/requirements.txt build/lambda-package/

cd build/lambda-package

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt -t .

# Remove virtual environment
deactivate
rm -rf venv

# Remove unnecessary files to reduce package size
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Remove AWS SDK (already available in Lambda)
rm -rf boto3* botocore* 2>/dev/null || true

# Create deployment ZIP
zip -r ../excel-mapper-lambda.zip . -q

cd ../..
echo "Lambda package created: build/excel-mapper-lambda.zip"
ls -lh build/excel-mapper-lambda.zip
```

---

## 🚀 Step 6: Deploy Lambda Function

### 6.1 Create Lambda Function

```bash
aws lambda create-function \
    --function-name excel-template-mapper \
    --runtime python3.9 \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/excel-mapper-lambda-execution-role \
    --handler index.lambda_handler \
    --zip-file fileb://build/excel-mapper-lambda.zip \
    --timeout 300 \
    --memory-size 1024 \
    --environment Variables='{
        "AWS_REGION":"us-east-1",
        "S3_BUCKET_UPLOADS":"'$UPLOAD_BUCKET'",
        "S3_BUCKET_PROCESSED":"'$PROCESSED_BUCKET'",
        "S3_BUCKET_TEMPLATES":"'$TEMPLATES_BUCKET'",
        "ENVIRONMENT":"dev"
    }' \
    --description "Excel Template Mapper - AI-powered Excel processing" \
    --tags Environment=dev,Project=excel-template-mapper
```

### 6.2 Create Function URL (Instead of API Gateway)

```bash
aws lambda create-function-url-config \
    --function-name excel-template-mapper \
    --auth-type NONE \
    --cors '{
        "AllowCredentials": false,
        "AllowHeaders": ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token", "x-amz-user-agent"],
        "AllowMethods": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
        "AllowOrigins": ["*"],
        "ExposeHeaders": ["date", "x-amzn-errortype"],
        "MaxAge": 86400
    }'
```

### 6.3 Get Function URL

```bash
LAMBDA_URL=$(aws lambda get-function-url-config \
    --function-name excel-template-mapper \
    --query FunctionUrl \
    --output text)

echo "🎉 Lambda Function URL: $LAMBDA_URL"
echo "Save this URL - you'll need it for frontend configuration!"
```

### 6.4 Test Lambda Function

```bash
# Test health endpoint
curl -X GET "$LAMBDA_URL" \
    -H "Content-Type: application/json" \
    -d '{"httpMethod": "GET", "path": "/health"}'

# Should return: {"statusCode": 200, "body": "...health check response..."}
```

---

## 📊 Step 7: CloudWatch Logging and Monitoring

### 7.1 Create CloudWatch Log Group

```bash
aws logs create-log-group \
    --log-group-name /aws/lambda/excel-template-mapper \
    --retention-in-days 14

# Verify log group created
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/excel-template-mapper
```

### 7.2 Create CloudWatch Alarms

```bash
# Lambda Error Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name excel-mapper-lambda-errors \
    --alarm-description "Lambda function errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 5 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value=excel-template-mapper \
    --treat-missing-data notBreaching

# Lambda Duration Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name excel-mapper-lambda-duration \
    --alarm-description "Lambda function duration" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 250000 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value=excel-template-mapper \
    --treat-missing-data notBreaching
```

---

## 🔧 Step 8: Configure S3 Event Triggers (Optional)

### 8.1 Add S3 Trigger Permission to Lambda

```bash
aws lambda add-permission \
    --function-name excel-template-mapper \
    --principal s3.amazonaws.com \
    --action lambda:InvokeFunction \
    --source-arn arn:aws:s3:::$UPLOAD_BUCKET \
    --statement-id s3-trigger-permission
```

### 8.2 Configure S3 Event Notification

```bash
cat > /tmp/s3-notification.json << EOF
{
    "LambdaConfigurations": [
        {
            "Id": "ExcelFileUploadTrigger",
            "LambdaFunctionArn": "arn:aws:lambda:us-east-1:${AWS_ACCOUNT_ID}:function:excel-template-mapper",
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {
                            "Name": "prefix",
                            "Value": "uploads/"
                        }
                    ]
                }
            }
        }
    ]
}
EOF

aws s3api put-bucket-notification-configuration \
    --bucket $UPLOAD_BUCKET \
    --notification-configuration file:///tmp/s3-notification.json
```

---

## 🌐 Step 9: Update Frontend Configuration

### 9.1 Update Frontend API Configuration

Edit `frontend/src/services/api.js`:

```javascript
// Replace the API_URL line with your Lambda Function URL
const API_URL = 'YOUR_LAMBDA_FUNCTION_URL_HERE'; // Replace with actual URL from Step 6.3
```

### 9.2 Create Environment File

Create `frontend/.env`:

```bash
cat > frontend/.env << EOF
REACT_APP_API_BASE_URL=$LAMBDA_URL
REACT_APP_AWS_REGION=us-east-1
REACT_APP_ENVIRONMENT=dev
EOF
```

### 9.3 Update Package.json Scripts (if needed)

Ensure your `frontend/package.json` has proper build scripts:

```json
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }
}
```

---

## 🚀 Step 10: Deploy Frontend with Amplify

### 10.1 Initialize Amplify

```bash
cd frontend

# Install Amplify CLI if not already installed
npm install -g @aws-amplify/cli

# Initialize Amplify
amplify init

# Follow prompts:
# ? Enter a name for the project: excel-template-mapper
# ? Initialize the project with the above configuration? Yes
# ? Select the authentication method you want to use: AWS profile
# ? Please choose the profile you want to use: default
```

### 10.2 Add Hosting

```bash
# Add hosting
amplify add hosting

# Choose:
# ? Select the plugin module to execute: Amazon CloudFront and S3
# ? Select the environment setup: PROD (S3 with CloudFront using HTTPS)
# ? hosting bucket name: excel-template-mapper-hosting-dev

# Publish the app
amplify publish
```

### 10.3 Alternative: Manual S3 + CloudFront Hosting

If you prefer manual setup:

```bash
# Build the React app
npm run build

# Create hosting bucket
HOSTING_BUCKET="excel-template-mapper-hosting-${AWS_ACCOUNT_ID}"
aws s3 mb s3://$HOSTING_BUCKET --region us-east-1

# Configure bucket for static website hosting
aws s3 website s3://$HOSTING_BUCKET \
    --index-document index.html \
    --error-document error.html

# Upload build files
aws s3 sync build/ s3://$HOSTING_BUCKET --delete

# Make bucket publicly readable
cat > /tmp/bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$HOSTING_BUCKET/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy \
    --bucket $HOSTING_BUCKET \
    --policy file:///tmp/bucket-policy.json

echo "Frontend deployed to: http://$HOSTING_BUCKET.s3-website-us-east-1.amazonaws.com"
```

---

## 🧪 Step 11: Testing Your Deployment

### 11.1 Test Lambda Function Directly

```bash
# Test health endpoint
curl -X POST "$LAMBDA_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "httpMethod": "GET",
        "path": "/health",
        "headers": {},
        "body": null
    }'

# Expected response: {"statusCode": 200, "body": "{\"status\":\"healthy\"...}"}
```

### 11.2 Test File Upload (using curl)

```bash
# Create a test file upload
echo "Test data" > /tmp/test.txt

# Test upload endpoint
curl -X POST "$LAMBDA_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "httpMethod": "POST",
        "path": "/upload",
        "headers": {"Content-Type": "application/json"},
        "body": "{\"test\": true}"
    }'
```

### 11.3 Test S3 Buckets

```bash
# Upload test file to S3
echo "Test upload" > /tmp/test-upload.txt
aws s3 cp /tmp/test-upload.txt s3://$UPLOAD_BUCKET/test/

# List bucket contents
aws s3 ls s3://$UPLOAD_BUCKET/ --recursive

# Download test file
aws s3 cp s3://$UPLOAD_BUCKET/test/test-upload.txt /tmp/downloaded.txt
cat /tmp/downloaded.txt
```

### 11.4 Test DynamoDB

```bash
# Create test session
aws dynamodb put-item \
    --table-name ExcelMapper_Sessions \
    --item '{
        "session_id": {"S": "test-session-123"},
        "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
        "status": {"S": "test"}
    }'

# Read test session
aws dynamodb get-item \
    --table-name ExcelMapper_Sessions \
    --key '{"session_id": {"S": "test-session-123"}}'

# Delete test session
aws dynamodb delete-item \
    --table-name ExcelMapper_Sessions \
    --key '{"session_id": {"S": "test-session-123"}}'
```

---

## 📊 Step 12: Monitor Your Application

### 12.1 View CloudWatch Logs

```bash
# Stream Lambda logs
aws logs tail /aws/lambda/excel-template-mapper --follow

# Filter for errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/excel-template-mapper \
    --filter-pattern "ERROR"
```

### 12.2 Check Metrics

```bash
# Get Lambda invocation metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=excel-template-mapper \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum

# Get Lambda error metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=excel-template-mapper \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum
```

---

## 🔧 Step 13: Cleanup Commands (if needed)

### 13.1 Delete Lambda Function

```bash
aws lambda delete-function --function-name excel-template-mapper
```

### 13.2 Delete S3 Buckets

```bash
# Empty and delete buckets
aws s3 rm s3://$UPLOAD_BUCKET --recursive
aws s3 rb s3://$UPLOAD_BUCKET

aws s3 rm s3://$PROCESSED_BUCKET --recursive
aws s3 rb s3://$PROCESSED_BUCKET

aws s3 rm s3://$TEMPLATES_BUCKET --recursive
aws s3 rb s3://$TEMPLATES_BUCKET
```

### 13.3 Delete DynamoDB Tables

```bash
aws dynamodb delete-table --table-name ExcelMapper_Sessions
aws dynamodb delete-table --table-name ExcelMapper_Templates
aws dynamodb delete-table --table-name ExcelMapper_TagTemplates
aws dynamodb delete-table --table-name ExcelMapper_ProcessingJobs
```

### 13.4 Delete IAM Role and Policy

```bash
# Detach policies
aws iam detach-role-policy \
    --role-name excel-mapper-lambda-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy \
    --role-name excel-mapper-lambda-execution-role \
    --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/excel-mapper-lambda-policy

# Delete custom policy
aws iam delete-policy --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/excel-mapper-lambda-policy

# Delete role
aws iam delete-role --role-name excel-mapper-lambda-execution-role
```

---

## 📋 Final Checklist

### ✅ AWS Resources Created:
- [ ] 4 DynamoDB tables (Sessions, Templates, TagTemplates, ProcessingJobs)
- [ ] 3 S3 buckets (uploads, processed, templates) with CORS
- [ ] IAM role with proper permissions
- [ ] Lambda function with Function URL
- [ ] CloudWatch log group and alarms
- [ ] S3 triggers configured (optional)

### ✅ Application Deployed:
- [ ] GitHub repository created and pushed
- [ ] Lambda function deployed with dependencies
- [ ] Frontend configured with Lambda URL
- [ ] Frontend deployed (Amplify or S3+CloudFront)
- [ ] End-to-end testing completed

### ✅ Monitoring Setup:
- [ ] CloudWatch alarms created
- [ ] Log monitoring configured
- [ ] Metrics tracking enabled

---

## 🎯 Important URLs to Save:

1. **Lambda Function URL**: `[Your Lambda URL from Step 6.3]`
2. **GitHub Repository**: `https://github.com/YOUR_USERNAME/excel-template-mapper`
3. **Frontend URL**: `[Your Amplify or S3 website URL]`
4. **CloudWatch Logs**: `https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups/log-group/%252Faws%252Flambda%252Fexcel-template-mapper`

---

## 📞 Next Steps:

1. **Test your application** end-to-end
2. **Monitor CloudWatch** for any errors
3. **Set up automated deployments** with GitHub Actions (optional)
4. **Configure custom domain** for frontend (optional)
5. **Add authentication** if needed (AWS Cognito)

---

**🎉 Your Excel Template Mapper is now live with Lambda Function URLs!**

No API Gateway needed - direct Lambda URL access with CORS configured for web requests.