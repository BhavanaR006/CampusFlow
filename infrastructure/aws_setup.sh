#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# CampusFlow — AWS Infrastructure Setup
# Amazon HackOn Season 6.0 | AWS Track
# ═══════════════════════════════════════════════════════════════════════════════

set -e

REGION="ap-south-1"
PROJECT="campusflow"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="${PROJECT}-frontend-${ACCOUNT_ID}"
LAMBDA_NAME="${PROJECT}-api"
API_NAME="${PROJECT}-http-api"
ROLE_NAME="${PROJECT}-lambda-role"

echo "🎓 CampusFlow AWS Infrastructure Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# ─── 1. S3 BUCKET (Static Frontend) ──────────────────────────────────────────
echo "📦 Creating S3 bucket for frontend..."
aws s3 mb s3://${S3_BUCKET} --region ${REGION} 2>/dev/null || echo "   Bucket exists"

# Enable static website hosting
aws s3 website s3://${S3_BUCKET} --index-document index.html --error-document index.html

# Set bucket policy for public read
aws s3api put-bucket-policy --bucket ${S3_BUCKET} --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::'${S3_BUCKET}'/*"
  }]
}'

# Upload frontend
aws s3 cp ../frontend/index.html s3://${S3_BUCKET}/index.html --content-type "text/html"
echo "   ✅ Frontend deployed to: http://${S3_BUCKET}.s3-website.${REGION}.amazonaws.com"

# ─── 2. IAM ROLE ─────────────────────────────────────────────────────────────
echo ""
echo "🔐 Creating IAM role..."
aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "   Role exists"

# Attach policy
aws iam put-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-name ${PROJECT}-policy \
  --policy-document file://iam_policy.json
echo "   ✅ IAM role configured"

# Wait for role propagation
sleep 10

# ─── 3. LAMBDA FUNCTION ──────────────────────────────────────────────────────
echo ""
echo "⚡ Creating Lambda function..."

# Package code
cd ..
rm -f lambda_package.zip
pip install -r backend/requirements.txt -t package/ --quiet
cp backend/main.py backend/database.py infrastructure/mangum_handler.py package/
cd package && zip -r ../lambda_package.zip . --quiet && cd ..
rm -rf package/

# Create/update Lambda
aws lambda create-function \
  --function-name ${LAMBDA_NAME} \
  --runtime python3.11 \
  --handler mangum_handler.handler \
  --role arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME} \
  --zip-file fileb://lambda_package.zip \
  --timeout 30 \
  --memory-size 256 \
  --region ${REGION} \
  --environment "Variables={AWS_REGION=${REGION}}" \
  2>/dev/null || \
aws lambda update-function-code \
  --function-name ${LAMBDA_NAME} \
  --zip-file fileb://lambda_package.zip \
  --region ${REGION}

rm -f lambda_package.zip
echo "   ✅ Lambda function deployed"

# ─── 4. API GATEWAY ──────────────────────────────────────────────────────────
echo ""
echo "🌐 Creating API Gateway..."
API_ID=$(aws apigatewayv2 create-api \
  --name ${API_NAME} \
  --protocol-type HTTP \
  --region ${REGION} \
  --query ApiId --output text 2>/dev/null || \
  aws apigatewayv2 get-apis --region ${REGION} --query "Items[?Name=='${API_NAME}'].ApiId" --output text)

# Create Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id ${API_ID} \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${LAMBDA_NAME} \
  --payload-format-version "2.0" \
  --region ${REGION} \
  --query IntegrationId --output text)

# Create catch-all route
aws apigatewayv2 create-route \
  --api-id ${API_ID} \
  --route-key '$default' \
  --target integrations/${INTEGRATION_ID} \
  --region ${REGION} > /dev/null

# Create stage
aws apigatewayv2 create-stage \
  --api-id ${API_ID} \
  --stage-name '$default' \
  --auto-deploy \
  --region ${REGION} > /dev/null 2>&1 || true

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name ${LAMBDA_NAME} \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
  --region ${REGION} 2>/dev/null || true

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com"
echo "   ✅ API Gateway: ${API_URL}"

# ─── 5. CLOUDFRONT ───────────────────────────────────────────────────────────
echo ""
echo "☁️  Creating CloudFront distribution..."
DIST_ID=$(aws cloudfront create-distribution \
  --origin-domain-name ${S3_BUCKET}.s3-website.${REGION}.amazonaws.com \
  --default-root-object index.html \
  --query Distribution.Id --output text 2>/dev/null || echo "skipped")

if [ "$DIST_ID" != "skipped" ]; then
  echo "   ✅ CloudFront Distribution: ${DIST_ID}"
fi

# ─── 6. DYNAMODB TABLES ──────────────────────────────────────────────────────
echo ""
echo "📊 Creating DynamoDB tables..."
for TABLE in users schedule notices tasks attendance exams chat-history alerts expenses mood-checkins placement-apps; do
  aws dynamodb create-table \
    --table-name ${PROJECT}-${TABLE} \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --region ${REGION} 2>/dev/null && echo "   ✅ ${PROJECT}-${TABLE}" || echo "   ⏭️  ${PROJECT}-${TABLE} exists"
done

# ─── DONE ─────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 CampusFlow deployed successfully!"
echo ""
echo "Frontend: http://${S3_BUCKET}.s3-website.${REGION}.amazonaws.com"
echo "API:      ${API_URL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
