#!/bin/bash

# Excel Template Mapper - Deployment Testing Script
# Comprehensive testing suite for validating deployment

set -e

# Configuration
PROJECT_NAME="excel-template-mapper"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

error() {
    echo -e "${RED}[FAIL]${NC} $1" >&2
    ((TESTS_FAILED++))
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TESTS_TOTAL++))
    log "Running test: $test_name"
    
    if $test_function; then
        success "$test_name"
    else
        error "$test_name"
    fi
    echo ""
}

# Get AWS account ID
get_account_id() {
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    if [[ -z "$ACCOUNT_ID" ]]; then
        error "Unable to get AWS account ID"
        return 1
    fi
    log "AWS Account ID: $ACCOUNT_ID"
}

# Test 1: CloudFormation Stack Status
test_cloudformation_stack() {
    local stack_name="${PROJECT_NAME}-${ENVIRONMENT}"
    
    local stack_status=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null)
    
    if [[ "$stack_status" == "CREATE_COMPLETE" ]] || [[ "$stack_status" == "UPDATE_COMPLETE" ]]; then
        return 0
    else
        echo "Stack status: $stack_status"
        return 1
    fi
}

# Test 2: Lambda Function Exists and is Active
test_lambda_function() {
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    
    local function_state=$(aws lambda get-function \
        --function-name "$function_name" \
        --query 'Configuration.State' \
        --output text 2>/dev/null)
    
    if [[ "$function_state" == "Active" ]]; then
        return 0
    else
        echo "Lambda function state: $function_state"
        return 1
    fi
}

# Test 3: Lambda Function Health Check
test_lambda_health() {
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    
    # Create test payload for health check
    local test_payload='{"httpMethod": "GET", "path": "/health"}'
    
    # Invoke function
    local response=$(aws lambda invoke \
        --function-name "$function_name" \
        --payload "$test_payload" \
        --output json \
        response.json 2>/dev/null)
    
    local status_code=$(echo "$response" | jq -r '.StatusCode')
    
    if [[ "$status_code" == "200" ]]; then
        # Check response body
        local response_body=$(cat response.json 2>/dev/null)
        if echo "$response_body" | jq -e '.statusCode == 200' > /dev/null 2>&1; then
            rm -f response.json
            return 0
        fi
    fi
    
    echo "Lambda invocation failed (Status: $status_code)"
    cat response.json 2>/dev/null || echo "No response file"
    rm -f response.json
    return 1
}

# Test 4: S3 Buckets Existence and CORS
test_s3_buckets() {
    local buckets=(
        "${PROJECT_NAME}-uploads-${ENVIRONMENT}-${ACCOUNT_ID}"
        "${PROJECT_NAME}-processed-${ENVIRONMENT}-${ACCOUNT_ID}"
        "${PROJECT_NAME}-templates-${ENVIRONMENT}-${ACCOUNT_ID}"
    )
    
    for bucket in "${buckets[@]}"; do
        # Check if bucket exists
        if ! aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
            echo "Bucket $bucket does not exist"
            return 1
        fi
        
        # Check CORS configuration
        if ! aws s3api get-bucket-cors --bucket "$bucket" >/dev/null 2>&1; then
            echo "CORS not configured for bucket $bucket"
            return 1
        fi
    done
    
    return 0
}

# Test 5: DynamoDB Tables
test_dynamodb_tables() {
    local tables=(
        "${PROJECT_NAME}_Sessions_${ENVIRONMENT}"
        "${PROJECT_NAME}_Templates_${ENVIRONMENT}"
        "${PROJECT_NAME}_TagTemplates_${ENVIRONMENT}"
        "${PROJECT_NAME}_ProcessingJobs_${ENVIRONMENT}"
    )
    
    for table in "${tables[@]}"; do
        local table_status=$(aws dynamodb describe-table \
            --table-name "$table" \
            --query 'Table.TableStatus' \
            --output text 2>/dev/null)
        
        if [[ "$table_status" != "ACTIVE" ]]; then
            echo "Table $table status: $table_status"
            return 1
        fi
    done
    
    return 0
}

# Test 6: API Gateway
test_api_gateway() {
    local stack_name="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Get API Gateway URL from CloudFormation stack outputs
    local api_url=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -z "$api_url" ]]; then
        echo "API Gateway URL not found in stack outputs"
        return 1
    fi
    
    # Test health endpoint
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "${api_url}/health" 2>/dev/null || echo "000")
    
    if [[ "$response_code" == "200" ]]; then
        return 0
    else
        echo "API Gateway health check failed (HTTP $response_code)"
        return 1
    fi
}

# Test 7: CloudWatch Log Groups
test_cloudwatch_logs() {
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    local log_group_name="/aws/lambda/${function_name}"
    
    # Check if log group exists
    if aws logs describe-log-groups \
        --log-group-name-prefix "$log_group_name" \
        --query 'logGroups[0].logGroupName' \
        --output text 2>/dev/null | grep -q "$log_group_name"; then
        return 0
    else
        echo "Log group $log_group_name not found"
        return 1
    fi
}

# Test 8: CloudWatch Alarms
test_cloudwatch_alarms() {
    local monitoring_stack="${PROJECT_NAME}-monitoring-${ENVIRONMENT}"
    
    # Check if monitoring stack exists
    local stack_status=$(aws cloudformation describe-stacks \
        --stack-name "$monitoring_stack" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null)
    
    if [[ "$stack_status" == "CREATE_COMPLETE" ]] || [[ "$stack_status" == "UPDATE_COMPLETE" ]]; then
        # Check for key alarms
        local alarm_count=$(aws cloudwatch describe-alarms \
            --alarm-name-prefix "$PROJECT_NAME" \
            --query 'MetricAlarms | length(@)' \
            --output text 2>/dev/null)
        
        if [[ "$alarm_count" -gt 0 ]]; then
            return 0
        else
            echo "No CloudWatch alarms found"
            return 1
        fi
    else
        echo "Monitoring stack status: $stack_status"
        return 1
    fi
}

# Test 9: IAM Roles and Policies
test_iam_permissions() {
    local role_name="${PROJECT_NAME}-lambda-execution-role-${ENVIRONMENT}"
    
    # Check if role exists
    if aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
        # Check if role has necessary policies
        local policy_count=$(aws iam list-attached-role-policies \
            --role-name "$role_name" \
            --query 'AttachedPolicies | length(@)' \
            --output text 2>/dev/null)
        
        if [[ "$policy_count" -gt 0 ]]; then
            return 0
        else
            echo "No policies attached to role $role_name"
            return 1
        fi
    else
        echo "IAM role $role_name not found"
        return 1
    fi
}

# Test 10: End-to-End Functionality
test_end_to_end() {
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    
    # Test upload endpoint
    local upload_payload='{
        "httpMethod": "POST",
        "path": "/upload",
        "headers": {"Content-Type": "application/json"},
        "body": "{\"test\": true}"
    }'
    
    local response=$(aws lambda invoke \
        --function-name "$function_name" \
        --payload "$upload_payload" \
        --output json \
        response.json 2>/dev/null)
    
    local status_code=$(echo "$response" | jq -r '.StatusCode')
    
    if [[ "$status_code" == "200" ]]; then
        rm -f response.json
        return 0
    else
        echo "End-to-end test failed (Status: $status_code)"
        cat response.json 2>/dev/null
        rm -f response.json
        return 1
    fi
}

# Test 11: Performance Baseline
test_performance() {
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    
    # Test cold start performance
    local start_time=$(date +%s%3N)
    
    local test_payload='{"httpMethod": "GET", "path": "/health"}'
    
    aws lambda invoke \
        --function-name "$function_name" \
        --payload "$test_payload" \
        response.json >/dev/null 2>&1
    
    local end_time=$(date +%s%3N)
    local duration=$((end_time - start_time))
    
    rm -f response.json
    
    # Check if response time is reasonable (under 10 seconds)
    if [[ "$duration" -lt 10000 ]]; then
        log "Lambda cold start: ${duration}ms"
        return 0
    else
        echo "Lambda response time too high: ${duration}ms"
        return 1
    fi
}

# Test 12: Security Validation
test_security() {
    local buckets=(
        "${PROJECT_NAME}-uploads-${ENVIRONMENT}-${ACCOUNT_ID}"
        "${PROJECT_NAME}-processed-${ENVIRONMENT}-${ACCOUNT_ID}"
        "${PROJECT_NAME}-templates-${ENVIRONMENT}-${ACCOUNT_ID}"
    )
    
    for bucket in "${buckets[@]}"; do
        # Check public access block
        local public_block=$(aws s3api get-public-access-block \
            --bucket "$bucket" \
            --query 'PublicAccessBlockConfiguration.BlockPublicAcls' \
            --output text 2>/dev/null)
        
        if [[ "$public_block" != "True" ]]; then
            echo "Bucket $bucket does not block public ACLs"
            return 1
        fi
    done
    
    return 0
}

# Generate test report
generate_report() {
    echo ""
    echo "=================================================="
    echo "           DEPLOYMENT TEST REPORT"
    echo "=================================================="
    echo ""
    echo "Project: $PROJECT_NAME"
    echo "Environment: $ENVIRONMENT"
    echo "Test Date: $(date)"
    echo "AWS Region: $AWS_REGION"
    echo "Account ID: $ACCOUNT_ID"
    echo ""
    echo "Results:"
    echo "  Total Tests: $TESTS_TOTAL"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}🎉 All tests passed! Deployment is healthy.${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Deploy frontend using: amplify publish"
        echo "2. Test complete user workflow"
        echo "3. Monitor CloudWatch dashboards"
        echo "4. Verify SNS notification delivery"
        return 0
    else
        echo -e "${RED}❌ $TESTS_FAILED tests failed. Please review and fix issues.${NC}"
        echo ""
        echo "Common solutions:"
        echo "1. Re-run deployment script: ./deploy.sh"
        echo "2. Check CloudWatch logs for errors"
        echo "3. Verify AWS permissions"
        echo "4. Ensure all resources are in the correct region"
        return 1
    fi
}

# Main function
main() {
    echo ""
    echo "🧪 Excel Template Mapper Deployment Testing"
    echo "==========================================="
    echo ""
    
    # Get AWS account ID
    if ! get_account_id; then
        error "Failed to get AWS account information"
        exit 1
    fi
    
    echo ""
    log "Starting deployment tests..."
    echo ""
    
    # Run all tests
    run_test "CloudFormation Stack Status" test_cloudformation_stack
    run_test "Lambda Function Status" test_lambda_function
    run_test "Lambda Health Check" test_lambda_health
    run_test "S3 Buckets and CORS" test_s3_buckets
    run_test "DynamoDB Tables" test_dynamodb_tables
    run_test "API Gateway" test_api_gateway
    run_test "CloudWatch Log Groups" test_cloudwatch_logs
    run_test "CloudWatch Alarms" test_cloudwatch_alarms
    run_test "IAM Roles and Policies" test_iam_permissions
    run_test "End-to-End Functionality" test_end_to_end
    run_test "Performance Baseline" test_performance
    run_test "Security Validation" test_security
    
    # Generate final report
    generate_report
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --quick        Run only basic health checks"
        echo ""
        echo "Environment Variables:"
        echo "  PROJECT_NAME   Project name (default: excel-template-mapper)"
        echo "  ENVIRONMENT    Environment name (default: dev)"  
        echo "  AWS_REGION     AWS region (default: us-east-1)"
        echo ""
        exit 0
        ;;
    --quick)
        # Run only essential tests
        log "Running quick health checks..."
        
        get_account_id
        run_test "CloudFormation Stack" test_cloudformation_stack
        run_test "Lambda Function" test_lambda_function  
        run_test "Lambda Health Check" test_lambda_health
        
        generate_report
        ;;
    *)
        main
        ;;
esac