#!/bin/bash

# Excel Template Mapper - Secure Deployment Script
# This script deploys the complete AWS infrastructure using secure methods

set -e

# Configuration
PROJECT_NAME="excel-template-mapper"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"
NOTIFICATION_EMAIL=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is required but not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured or invalid"
        error "Please run 'aws configure' first"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check zip command
    if ! command -v zip &> /dev/null; then
        error "zip command is required but not installed"
        exit 1
    fi
    
    success "All prerequisites met"
}

# Get AWS account ID
get_account_id() {
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log "AWS Account ID: $ACCOUNT_ID"
}

# Prompt for notification email
get_notification_email() {
    if [[ -z "$NOTIFICATION_EMAIL" ]]; then
        echo -n "Enter email address for notifications (required): "
        read NOTIFICATION_EMAIL
        
        if [[ -z "$NOTIFICATION_EMAIL" ]]; then
            error "Email address is required for deployment"
            exit 1
        fi
    fi
    log "Notifications will be sent to: $NOTIFICATION_EMAIL"
}

# Build Lambda deployment package
build_lambda_package() {
    log "Building Lambda deployment package..."
    
    cd "$(dirname "$0")"
    
    if [[ -f "./lambda-deployment-package.sh" ]]; then
        ./lambda-deployment-package.sh
    else
        error "Lambda deployment script not found"
        exit 1
    fi
    
    success "Lambda package built"
}

# Deploy infrastructure
deploy_infrastructure() {
    log "Deploying infrastructure stack..."
    
    local stack_name="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$stack_name" &> /dev/null; then
        warning "Stack $stack_name already exists. Updating..."
        
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body file://cloudformation-template.yaml \
            --parameters ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
                        ParameterKey=ProjectName,ParameterValue="$PROJECT_NAME" \
            --capabilities CAPABILITY_NAMED_IAM
        
        aws cloudformation wait stack-update-complete --stack-name "$stack_name"
    else
        log "Creating new stack $stack_name..."
        
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body file://cloudformation-template.yaml \
            --parameters ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
                        ParameterKey=ProjectName,ParameterValue="$PROJECT_NAME" \
            --capabilities CAPABILITY_NAMED_IAM \
            --on-failure ROLLBACK
        
        aws cloudformation wait stack-create-complete --stack-name "$stack_name"
    fi
    
    success "Infrastructure stack deployed"
}

# Update Lambda function
update_lambda_function() {
    log "Updating Lambda function code..."
    
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    local package_path="../build/lambda-deployment-package.zip"
    
    if [[ ! -f "$package_path" ]]; then
        error "Lambda package not found at $package_path"
        exit 1
    fi
    
    aws lambda update-function-code \
        --function-name "$function_name" \
        --zip-file fileb://"$package_path"
    
    # Wait for function to be updated
    aws lambda wait function-updated --function-name "$function_name"
    
    success "Lambda function updated"
}

# Configure S3 CORS
configure_s3_cors() {
    log "Configuring S3 CORS..."
    
    local buckets=(
        "${PROJECT_NAME}-uploads-${ENVIRONMENT}-${ACCOUNT_ID}"
        "${PROJECT_NAME}-processed-${ENVIRONMENT}-${ACCOUNT_ID}"
        "${PROJECT_NAME}-templates-${ENVIRONMENT}-${ACCOUNT_ID}"
    )
    
    for bucket in "${buckets[@]}"; do
        log "Configuring CORS for bucket: $bucket"
        
        # Check if bucket exists
        if aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
            aws s3api put-bucket-cors \
                --bucket "$bucket" \
                --cors-configuration file://s3-cors-config.json
            
            success "CORS configured for $bucket"
        else
            warning "Bucket $bucket not found, skipping CORS configuration"
        fi
    done
}

# Deploy monitoring
deploy_monitoring() {
    log "Deploying monitoring stack..."
    
    local stack_name="${PROJECT_NAME}-monitoring-${ENVIRONMENT}"
    
    # Check if monitoring stack exists
    if aws cloudformation describe-stacks --stack-name "$stack_name" &> /dev/null; then
        warning "Monitoring stack $stack_name already exists. Updating..."
        
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body file://cloudwatch-alarms.yaml \
            --parameters ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
                        ParameterKey=ProjectName,ParameterValue="$PROJECT_NAME" \
                        ParameterKey=NotificationEmail,ParameterValue="$NOTIFICATION_EMAIL"
        
        aws cloudformation wait stack-update-complete --stack-name "$stack_name"
    else
        log "Creating monitoring stack $stack_name..."
        
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body file://cloudwatch-alarms.yaml \
            --parameters ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
                        ParameterKey=ProjectName,ParameterValue="$PROJECT_NAME" \
                        ParameterKey=NotificationEmail,ParameterValue="$NOTIFICATION_EMAIL" \
            --on-failure ROLLBACK
        
        aws cloudformation wait stack-create-complete --stack-name "$stack_name"
    fi
    
    # Deploy CloudWatch dashboard
    log "Creating CloudWatch dashboard..."
    aws cloudwatch put-dashboard \
        --dashboard-name "ExcelTemplateMapper-${ENVIRONMENT}" \
        --dashboard-body file://cloudwatch-dashboard.json
    
    success "Monitoring stack deployed"
}

# Test deployment
test_deployment() {
    log "Testing deployment..."
    
    local function_name="${PROJECT_NAME}-main-${ENVIRONMENT}"
    
    # Test Lambda function
    log "Testing Lambda function..."
    local test_payload='{"httpMethod": "GET", "path": "/health"}'
    
    local response=$(aws lambda invoke \
        --function-name "$function_name" \
        --payload "$test_payload" \
        --output text \
        --query 'StatusCode' \
        response.json)
    
    if [[ "$response" == "200" ]]; then
        success "Lambda function test passed"
    else
        error "Lambda function test failed"
        cat response.json
        exit 1
    fi
    
    # Clean up test file
    rm -f response.json
    
    # Test API Gateway (if available)
    local api_url=$(aws cloudformation describe-stacks \
        --stack-name "${PROJECT_NAME}-${ENVIRONMENT}" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -n "$api_url" ]]; then
        log "Testing API Gateway at: $api_url"
        
        local health_response=$(curl -s -o /dev/null -w "%{http_code}" "$api_url/health" || echo "000")
        
        if [[ "$health_response" == "200" ]]; then
            success "API Gateway test passed"
        else
            warning "API Gateway test failed (HTTP $health_response)"
        fi
    fi
}

# Get deployment outputs
get_outputs() {
    log "Getting deployment outputs..."
    
    local stack_name="${PROJECT_NAME}-${ENVIRONMENT}"
    
    echo ""
    echo "=== DEPLOYMENT OUTPUTS ==="
    
    # Get stack outputs
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue,Description]' \
        --output table
    
    echo ""
    echo "=== NEXT STEPS ==="
    echo "1. Update frontend .env file with API Gateway URL"
    echo "2. Deploy frontend using: amplify publish"
    echo "3. Test the complete application workflow"
    echo "4. Monitor CloudWatch dashboard for health metrics"
    echo "5. Confirm SNS notification delivery"
    echo ""
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f response.json
}

# Main deployment function
main() {
    echo ""
    echo "🚀 Excel Template Mapper Deployment Script"
    echo "=========================================="
    echo ""
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    check_prerequisites
    get_account_id
    get_notification_email
    
    echo ""
    warning "Starting deployment with the following configuration:"
    echo "  Project: $PROJECT_NAME"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region: $AWS_REGION"
    echo "  Account: $ACCOUNT_ID"
    echo "  Email: $NOTIFICATION_EMAIL"
    echo ""
    
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Deployment cancelled by user"
        exit 0
    fi
    
    echo ""
    log "Starting deployment process..."
    echo ""
    
    # Execute deployment steps
    build_lambda_package
    deploy_infrastructure
    update_lambda_function
    configure_s3_cors
    deploy_monitoring
    test_deployment
    get_outputs
    
    echo ""
    success "🎉 Deployment completed successfully!"
    echo ""
    
    log "View your CloudWatch dashboard at:"
    echo "https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=ExcelTemplateMapper-${ENVIRONMENT}"
    echo ""
    
    log "Monitor your application logs at:"
    echo "https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups/log-group/%252Faws%252Flambda%252F${PROJECT_NAME}-main-${ENVIRONMENT}"
    echo ""
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --cleanup      Clean up build artifacts"
        echo ""
        echo "Environment Variables:"
        echo "  PROJECT_NAME      Project name (default: excel-template-mapper)"
        echo "  ENVIRONMENT       Environment name (default: dev)"  
        echo "  AWS_REGION        AWS region (default: us-east-1)"
        echo "  NOTIFICATION_EMAIL Email for notifications"
        echo ""
        exit 0
        ;;
    --cleanup)
        log "Cleaning up build artifacts..."
        rm -rf ../build/
        success "Cleanup completed"
        exit 0
        ;;
    *)
        main
        ;;
esac