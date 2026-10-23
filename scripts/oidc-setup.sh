#!/usr/bin/env bash
# GitHub OIDC setup for kordis.cloud (finding 4): the AWS side of docs/github-oidc-plan.md.
# Run in AWS CloudShell (us-east-1) as an admin. Safe to run more than once.
# Creates: OIDC provider, gha-kordis-cloud-site, gha-kordis-cloud-infra, cfn-exec-kordis-cloud,
# and the kordis-cloud-lambda-boundary permissions boundary.
# Every run resets each role to exactly what is declared here: trust policy, inline
# policies (unknown ones are deleted) and attached managed policies (all detached).
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

# 4a. Permissions boundary for every role the stack creates (the Lambda roles).
# A role's effective permissions are the intersection of its own policies and this
# boundary, so even a role the deploy writes with Action "*" can only reach the counter
# table, the stack's log groups and X-Ray. The exec role cannot edit this policy.
BOUNDARY_ARN="arn:aws:iam::${ACCOUNT}:policy/kordis-cloud-lambda-boundary"
cat > boundary.json <<EOF
{"Version":"2012-10-17","Statement":[
 {"Sid":"CounterTable","Effect":"Allow","Action":["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem"],
  "Resource":"arn:aws:dynamodb:${REGION}:${ACCOUNT}:table/kordis-cloud"},
 {"Sid":"StackLogs","Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
  "Resource":["arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/kordis-cloud-*","arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/kordis-cloud-*:*"]},
 {"Sid":"Tracing","Effect":"Allow","Action":["xray:PutTraceSegments","xray:PutTelemetryRecords","xray:GetSamplingRules","xray:GetSamplingTargets","xray:GetSamplingStatisticSummaries"],"Resource":"*"}]}
EOF
if aws iam get-policy --policy-arn "$BOUNDARY_ARN" >/dev/null 2>&1; then
  # Keep at most 5 versions: drop the oldest non-default one before adding a new default
  OLD=$(aws iam list-policy-versions --policy-arn "$BOUNDARY_ARN" --query 'Versions[?IsDefaultVersion==`false`].VersionId' --output text)
  for v in $OLD; do aws iam delete-policy-version --policy-arn "$BOUNDARY_ARN" --version-id "$v"; done
  aws iam create-policy-version --policy-arn "$BOUNDARY_ARN" --policy-document file://boundary.json --set-as-default >/dev/null
else
  aws iam create-policy --policy-name kordis-cloud-lambda-boundary --policy-document file://boundary.json >/dev/null
fi
echo "ok: $BOUNDARY_ARN"

# 4b. CloudFormation execution role.
# Role writes are allowed only while the target role carries the boundary above, so a
# deploy cannot create or edit an unbounded role and pass it to Lambda. Removing a
# boundary (iam:DeleteRolePermissionsBoundary) is never granted.
cat > cfn-exec.json <<EOF
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":"dynamodb:*","Resource":"arn:aws:dynamodb:${REGION}:${ACCOUNT}:table/kordis-cloud"},
 {"Effect":"Allow","Action":"lambda:*","Resource":"arn:aws:lambda:${REGION}:${ACCOUNT}:function:kordis-cloud-*"},
 {"Effect":"Allow","Action":"logs:*","Resource":["arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/kordis-cloud-*","arn:aws:logs:${REGION}:${ACCOUNT}:log-group:/aws/lambda/kordis-cloud-*:*"]},
 {"Effect":"Allow","Action":"logs:DescribeLogGroups","Resource":"*"},
 {"Sid":"ManageStackRoles","Effect":"Allow","Action":["iam:GetRole","iam:GetRolePolicy","iam:ListRolePolicies","iam:ListAttachedRolePolicies","iam:TagRole","iam:UntagRole","iam:DeleteRole","iam:UpdateAssumeRolePolicy"],"Resource":"arn:aws:iam::${ACCOUNT}:role/kordis-cloud-*"},
 {"Sid":"WriteBoundedStackRoles","Effect":"Allow","Action":["iam:CreateRole","iam:PutRolePermissionsBoundary","iam:PutRolePolicy","iam:DeleteRolePolicy","iam:DetachRolePolicy"],"Resource":"arn:aws:iam::${ACCOUNT}:role/kordis-cloud-*",
  "Condition":{"StringEquals":{"iam:PermissionsBoundary":"${BOUNDARY_ARN}"}}},
 {"Sid":"AttachLambdaManagedPolicies","Effect":"Allow","Action":"iam:AttachRolePolicy","Resource":"arn:aws:iam::${ACCOUNT}:role/kordis-cloud-*",
  "Condition":{"StringEquals":{"iam:PermissionsBoundary":"${BOUNDARY_ARN}"},
   "ArnEquals":{"iam:PolicyARN":["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole","arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess"]}}},
 {"Sid":"PassStackRolesToLambda","Effect":"Allow","Action":"iam:PassRole","Resource":"arn:aws:iam::${ACCOUNT}:role/kordis-cloud-*",
  "Condition":{"StringEquals":{"iam:PassedToService":"lambda.amazonaws.com"}}},
 {"Effect":"Allow","Action":"s3:*","Resource":"arn:aws:s3:::kordis-cloud"},
 {"Effect":"Allow","Action":"s3:GetObject","Resource":"arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*/*"},
 {"Effect":"Allow","Action":"apigateway:*","Resource":"arn:aws:apigateway:${REGION}::/*"},
 {"Effect":"Allow","Action":["cloudfront:*","acm:DescribeCertificate","acm:RequestCertificate","acm:DeleteCertificate","acm:AddTagsToCertificate","acm:ListTagsForCertificate"],"Resource":"*"},
 {"Effect":"Allow","Action":["route53:GetHostedZone","route53:ChangeResourceRecordSets","route53:ListResourceRecordSets","route53:GetChange"],"Resource":["arn:aws:route53:::hostedzone/Z05030141Q82CAW2GKME0","arn:aws:route53:::change/*"]}]}
EOF

# 5. GitHub infra role (drives CloudFormation, SAM artifact bucket, passes the exec role)
cat > infra.json <<EOF
{"Version":"2012-10-17","Statement":[
 {"Sid":"Stacks","Effect":"Allow","Action":["cloudformation:CreateChangeSet","cloudformation:DescribeChangeSet","cloudformation:ExecuteChangeSet","cloudformation:DeleteChangeSet","cloudformation:DescribeStacks","cloudformation:DescribeStackEvents","cloudformation:GetTemplate","cloudformation:GetTemplateSummary","cloudformation:ListStackResources","cloudformation:ContinueUpdateRollback","cloudformation:CancelUpdateStack"],
  "Resource":["arn:aws:cloudformation:${REGION}:${ACCOUNT}:stack/kordis-cloud/*","arn:aws:cloudformation:${REGION}:${ACCOUNT}:stack/aws-sam-cli-managed-default/*","arn:aws:cloudformation:${REGION}:aws:transform/Serverless-2016-10-31"]},
 {"Sid":"ValidateTemplate","Effect":"Allow","Action":"cloudformation:ValidateTemplate","Resource":"*"},
 {"Sid":"SamArtifacts","Effect":"Allow","Action":["s3:ListBucket","s3:GetObject","s3:PutObject","s3:DeleteObject","s3:GetLifecycleConfiguration","s3:PutLifecycleConfiguration"],
  "Resource":["arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*","arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*/*"]},
 {"Sid":"HandRoleToCloudFormation","Effect":"Allow","Action":"iam:PassRole","Resource":"arn:aws:iam::${ACCOUNT}:role/cfn-exec-kordis-cloud",
  "Condition":{"StringEquals":{"iam:PassedToService":"cloudformation.amazonaws.com"}}}]}
EOF

create_role() { # name trust-file policy-file [extra inline policy names to keep...]
  local name=$1 trust=$2 policy=$3; shift 3
  if aws iam get-role --role-name "$name" >/dev/null 2>&1; then
    aws iam update-assume-role-policy --role-name "$name" --policy-document "file://$trust"
  else
    aws iam create-role --role-name "$name" --assume-role-policy-document "file://$trust" >/dev/null
  fi
  aws iam put-role-policy --role-name "$name" --policy-name "$name" --policy-document "file://$policy"
  # Remove anything not declared here, so a rerun leaves the role exactly as specified
  for p in $(aws iam list-role-policies --role-name "$name" --query 'PolicyNames[]' --output text); do
    case " $name $* " in *" $p "*) ;; *) echo "removing undeclared inline policy $p from $name"; aws iam delete-role-policy --role-name "$name" --policy-name "$p";; esac
  done
  for a in $(aws iam list-attached-role-policies --role-name "$name" --query 'AttachedPolicies[].PolicyArn' --output text); do
    echo "detaching undeclared managed policy $a from $name"; aws iam detach-role-policy --role-name "$name" --policy-arn "$a"
  done
  if [ "$(aws iam get-role --role-name "$name" --query 'Role.PermissionsBoundary.PermissionsBoundaryArn' --output text)" != "None" ]; then
    echo "removing unexpected permissions boundary from $name"; aws iam delete-role-permissions-boundary --role-name "$name"
  fi
  echo "ok: arn:aws:iam::${ACCOUNT}:role/$name"
}
create_role gha-kordis-cloud-site trust-github-main.json site.json
# With a service role, CloudFormation expands the SAM transform as that role
cat > cfn-exec-transform.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"cloudformation:CreateChangeSet",
 "Resource":"arn:aws:cloudformation:${REGION}:aws:transform/Serverless-2016-10-31"}]}
EOF
aws iam put-role-policy --role-name cfn-exec-kordis-cloud --policy-name cfn-exec-kordis-cloud-sam-transform --policy-document file://cfn-exec-transform.json
create_role cfn-exec-kordis-cloud trust-cloudformation.json cfn-exec.json cfn-exec-kordis-cloud-sam-transform
create_role gha-kordis-cloud-infra trust-github-main.json infra.json
