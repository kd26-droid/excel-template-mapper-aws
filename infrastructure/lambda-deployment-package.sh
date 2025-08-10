#!/bin/bash

# Excel Template Mapper - Lambda Deployment Package Creator
# This script creates a deployment package for the Lambda function with all dependencies

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_SOURCE="${PROJECT_ROOT}/amplify/backend/function/excelMapper/src"
BUILD_DIR="${PROJECT_ROOT}/build"
PACKAGE_DIR="${BUILD_DIR}/lambda-package"
REQUIREMENTS_FILE="${LAMBDA_SOURCE}/requirements.txt"

echo "🚀 Creating Lambda deployment package..."
echo "Project root: ${PROJECT_ROOT}"
echo "Lambda source: ${LAMBDA_SOURCE}"

# Clean and create build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${PACKAGE_DIR}"

# Copy source code
echo "📦 Copying source code..."
cp "${LAMBDA_SOURCE}/index.py" "${PACKAGE_DIR}/"
cp "${REQUIREMENTS_FILE}" "${PACKAGE_DIR}/"

# Create virtual environment and install dependencies
echo "📚 Installing Python dependencies..."
cd "${PACKAGE_DIR}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt -t .

# Remove virtual environment
deactivate
rm -rf venv

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Remove large unused packages if they exist
rm -rf boto3* botocore* 2>/dev/null || true  # AWS Lambda already has these
rm -rf wheel* setuptools* pip* 2>/dev/null || true

# Create deployment package
echo "📦 Creating deployment ZIP..."
zip -r "../lambda-deployment-package.zip" . -q

cd "${PROJECT_ROOT}"

# Display package info
PACKAGE_SIZE=$(du -h "${BUILD_DIR}/lambda-deployment-package.zip" | cut -f1)
echo "✅ Lambda deployment package created!"
echo "   Location: ${BUILD_DIR}/lambda-deployment-package.zip"
echo "   Size: ${PACKAGE_SIZE}"

# Verify package contents
echo ""
echo "📋 Package contents:"
unzip -l "${BUILD_DIR}/lambda-deployment-package.zip" | head -20

echo ""
echo "🎯 Next steps:"
echo "   1. Upload this package to AWS Lambda"
echo "   2. Update function configuration"
echo "   3. Set environment variables"
echo "   4. Configure triggers"

# Create layer package for reusable dependencies
echo ""
echo "🔧 Creating Lambda Layer package..."
LAYER_DIR="${BUILD_DIR}/layer-package"
mkdir -p "${LAYER_DIR}/python"

# Install common dependencies in layer
cd "${LAYER_DIR}/python"
pip install -r "${REQUIREMENTS_FILE}" -t . --no-deps

# Create layer ZIP
cd "${LAYER_DIR}"
zip -r "../python-libs-layer.zip" . -q

LAYER_SIZE=$(du -h "${BUILD_DIR}/python-libs-layer.zip" | cut -f1)
echo "✅ Lambda Layer package created!"
echo "   Location: ${BUILD_DIR}/python-libs-layer.zip"
echo "   Size: ${LAYER_SIZE}"

echo ""
echo "🚀 Deployment packages ready!"