#!/usr/bin/env bash
# GitHub OIDC setup for kordis.cloud (finding 4): the AWS side of docs/github-oidc-plan.md.
# Run in AWS CloudShell (us-east-1) as an admin. Safe to run more than once.
# Creates: OIDC provider, gha-kordis-cloud-site, gha-kordis-cloud-infra, cfn-exec-kordis-cloud.
set -euo pipefail
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
cd "$(mktemp -d)"

# 1. OIDC identity provider (skip if it already exists)
if ! aws iam get-open-id-connect-provider --open-id-connect-provider-arn "arn:aws:iam::${ACCOUNT}:oidc-provider/token.actions.githubusercontent.com" >/dev/null 2>&1; then
  aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com --client-id-list sts.amazonaws.com
fi

# 2. Trust policies
cat > trust-github-main.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
 "Principal":{"Federated":"arn:aws:iam::${ACCOUNT}:oidc-provider/token.actions.githubusercontent.com"},
 "Action":"sts:AssumeRoleWithWebIdentity",
 "Condition":{"StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com",
  "token.actions.githubusercontent.com:sub":"repo:nkordis/kordis.cloud:ref:refs/heads/main"}}}]}
EOF
cat > trust-cloudformation.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"cloudformation.amazonaws.com"},
 "Action":"sts:AssumeRole","Condition":{"StringEquals":{"aws:SourceAccount":"${ACCOUNT}"}}}]}
EOF

# 3. Site upload role
cat > site.json <<'EOF'
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":"s3:ListBucket","Resource":"arn:aws:s3:::kordis-cloud"},
 {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":"arn:aws:s3:::kordis-cloud/*"}]}
EOF

# 4. CloudFormation execution role
cat > cfn-exec.json <<EOF
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":"dynamodb:*","Resource":"arn:aws:dynamodb:${REGION}:${ACCOUNT}:table/kordis-cloud"},
 {"Effect":"Allow","Action":"lambda:*","Resource":"arn:aws:lambda:${REGION}:${ACCOUNT}:function:kordis-cloud-*"},
 {"Effect":"Allow","Action":"logs:*","Resource":["arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/kordis-cloud-*","arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/kordis-cloud-*:*"]},
 {"Effect":"Allow","Action":"logs:DescribeLogGroups","Resource":"*"},
 {"Effect":"Allow","Action":["iam:GetRole","iam:CreateRole","iam:DeleteRole","iam:TagRole","iam:UntagRole","iam:PutRolePolicy","iam:DeleteRolePolicy","iam:GetRolePolicy","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:DetachRolePolicy","iam:UpdateAssumeRolePolicy","iam:PassRole"],"Resource":"arn:aws:iam::${ACCOUNT}:role/kordis-cloud-*"},
 {"Effect":"Allow","Action":"iam:AttachRolePolicy","Resource":"arn:aws:iam::${ACCOUNT}:role/kordis-cloud-*",
  "Condition":{"ArnEquals":{"iam:PolicyARN":["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole","arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess"]}}},
 {"Effect":"Allow","Action":"s3:*","Resource":"arn:aws:s3:::kordis-cloud"},
 {"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*/*"},
 {"Effect":"Allow","Action":"apigateway:*","Resource":"arn:aws:apigateway:${REGION}::/*"},
 {"Effect":"Allow","Action":["cloudfront:*","acm:DescribeCertificate","acm:RequestCertificate","acm:DeleteCertificate","acm:AddTagsToCertificate","acm:ListTagsForCertificate"],"Resource":"*"},
 {"Effect":"Allow","Action":["route53:GetHostedZone","route53:ChangeResourceRecordSets","route53:ListResourceRecordSets","route53:GetChange"],"Resource":["arn:aws:route53:::hostedzone/Z05030141Q82CAW2GKME0","arn:aws:route53:::change/*"]}]}
EOF

# 5. GitHub infra role (drives CloudFormation, SAM artifact bucket, passes the exec role)
cat > infra.json <<EOF
{"Version":"2012-10-17","Statement":[
 {"Sid":"Stacks","Effect":"Allow","Action":["cloudformation:CreateChangeSet","cloudformation:DescribeChangeSet","cloudformation:ExecuteChangeSet","cloudformation:DeleteChangeSet","cloudformation:DescribeStacks","cloudformation:DescribeStackEvents","cloudformation:GetTemplate","cloudformation:GetTemplateSummary","cloudformation:ListStackResources"],
  "Resource":["arn:aws:cloudformation:${REGION}:${ACCOUNT}:stack/kordis-cloud/*","arn:aws:cloudformation:${REGION}:${ACCOUNT}:stack/aws-sam-cli-managed-default/*","arn:aws:cloudformation:${REGION}:aws:transform/Serverless-2016-10-31"]},
 {"Sid":"ValidateTemplate","Effect":"Allow","Action":"cloudformation:ValidateTemplate","Resource":"*"},
 {"Sid":"SamArtifacts","Effect":"Allow","Action":["s3:ListBucket","s3:GetObject","s3:PutObject","s3:DeleteObject","s3:GetLifecycleConfiguration","s3:PutLifecycleConfiguration"],
  "Resource":["arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*","arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*/*"]},
 {"Sid":"HandRoleToCloudFormation","Effect":"Allow","Action":"iam:PassRole","Resource":"arn:aws:iam::${ACCOUNT}:role/cfn-exec-kordis-cloud",
  "Condition":{"StringEquals":{"iam:PassedToService":"cloudformation.amazonaws.com"}}}]}
EOF

create_role() { # name trust-file policy-file
  aws iam get-role --role-name "$1" >/dev/null 2>&1 || aws iam create-role --role-name "$1" --assume-role-policy-document "file://$2" >/dev/null
  aws iam put-role-policy --role-name "$1" --policy-name "$1" --policy-document "file://$3"
  echo "ok: arn:aws:iam::${ACCOUNT}:role/$1"
}
create_role gha-kordis-cloud-site trust-github-main.json site.json
create_role cfn-exec-kordis-cloud trust-cloudformation.json cfn-exec.json
create_role gha-kordis-cloud-infra trust-github-main.json infra.json
