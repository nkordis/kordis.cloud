# GitHub OIDC for kordis.cloud deploys

Finding 4 of the external cost and security review: the workflow used one pair of long-lived AWS keys for every job, including mocked unit tests. This plan replaces them with GitHub OIDC and three narrow roles. The workflow side is in this PR; the AWS side below is applied by Nikos.

Replace `<ACCOUNT_ID>` with the AWS account id. Region is `us-east-1`.

## Who gets what

| Job | AWS access after this change |
|---|---|
| `test-infra` (unit tests, `sam validate --lint`) | none (moto uses fake credentials) |
| `integration-tests` | none (calls the public `https://api.kordis.cloud/`) |
| `e2e-tests` | none |
| `deploy-site` | `kordis-cloud-gha-site`: write the site bucket only |
| `build-deploy-infra`, `cleanup-sam-artifacts` | `kordis-cloud-gha-infra`: drive the two CloudFormation stacks, the SAM artifact bucket, and pass one role to CloudFormation |
| (CloudFormation itself) | `kordis-cloud-cfn-exec`: creates and updates the stack's resources; only CloudFormation can assume it |

Both GitHub roles trust only pushes and manual runs on `main` of `nkordis/kordis.cloud`. A pull request, fork or other branch cannot assume them.

## Steps

### 1. OIDC identity provider (once per account)
IAM → Identity providers → Add provider → OpenID Connect, URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`. Or:
```
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```
(IAM no longer requires a thumbprint for this provider; if your CLI version asks for one, use the console instead, which fills it in.)

### 2. Trust policy for both GitHub roles (`trust-github-main.json`)
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:nkordis/kordis.cloud:ref:refs/heads/main"
      }
    }
  }]
}
```

### 3. `kordis-cloud-gha-site` (site upload)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::kordis-cloud" },
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": "arn:aws:s3:::kordis-cloud/*" }
  ]
}
```

### 4. `kordis-cloud-cfn-exec` (used by CloudFormation only)
Trust policy: principal `cloudformation.amazonaws.com`, with `aws:SourceAccount` = `<ACCOUNT_ID>`.

Permissions: what the stack creates, limited to its resources where AWS supports it:
- `dynamodb:*` on `arn:aws:dynamodb:us-east-1:<ACCOUNT_ID>:table/kordis-cloud`
- `lambda:*` on `arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:kordis-cloud-*`
- `logs:*` on `arn:aws:logs:us-east-1:<ACCOUNT_ID>:log-group:/aws/lambda/kordis-cloud-*`
- `iam:GetRole`, `CreateRole`, `DeleteRole`, `TagRole`, `UntagRole`, `PutRolePolicy`, `DeleteRolePolicy`, `GetRolePolicy`, `AttachRolePolicy`, `DetachRolePolicy`, `UpdateAssumeRolePolicy`, `PassRole` on `arn:aws:iam::<ACCOUNT_ID>:role/kordis-cloud-*`
- `s3:*` on `arn:aws:s3:::kordis-cloud` (bucket settings and policy, not objects)
- `apigateway:*` on `arn:aws:apigateway:us-east-1::/*` (API Gateway has no useful per-API scoping at create time)
- `cloudfront:*` on `*` and `acm:DescribeCertificate`, `acm:RequestCertificate`, `acm:DeleteCertificate`, `acm:AddTagsToCertificate` on `*` (CloudFront and ACM ids are not known in advance)
- `route53:GetHostedZone`, `ChangeResourceRecordSets`, `ListResourceRecordSets`, `GetChange` on `arn:aws:route53:::hostedzone/Z05030141Q82CAW2GKME0` and `arn:aws:route53:::change/*`
- `xray:*` is not needed (the functions' own roles get X-Ray write access)

Start from this; if a deploy fails with AccessDenied, the CloudFormation event names the missing action, and only that action should be added.

### 5. `kordis-cloud-gha-infra` (SAM deploy and artifact cleanup)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "Stacks", "Effect": "Allow",
      "Action": ["cloudformation:CreateChangeSet", "cloudformation:DescribeChangeSet", "cloudformation:ExecuteChangeSet",
                 "cloudformation:DeleteChangeSet", "cloudformation:DescribeStacks", "cloudformation:DescribeStackEvents",
                 "cloudformation:GetTemplate", "cloudformation:GetTemplateSummary", "cloudformation:ListStackResources"],
      "Resource": ["arn:aws:cloudformation:us-east-1:<ACCOUNT_ID>:stack/kordis-cloud/*",
                   "arn:aws:cloudformation:us-east-1:<ACCOUNT_ID>:stack/aws-sam-cli-managed-default/*",
                   "arn:aws:cloudformation:us-east-1:aws:transform/Serverless-2016-10-31"] },
    { "Sid": "ValidateTemplate", "Effect": "Allow", "Action": "cloudformation:ValidateTemplate", "Resource": "*" },
    { "Sid": "SamArtifacts", "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                 "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration"],
      "Resource": ["arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*",
                   "arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*/*"] },
    { "Sid": "HandRoleToCloudFormation", "Effect": "Allow", "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/kordis-cloud-cfn-exec",
      "Condition": { "StringEquals": { "iam:PassedToService": "cloudformation.amazonaws.com" } } }
  ]
}
```

### 6. GitHub repository variables
Settings → Secrets and variables → Actions → **Variables** (not secrets; role ARNs are not sensitive):
- `AWS_DEPLOY_INFRA_ROLE_ARN` = `arn:aws:iam::<ACCOUNT_ID>:role/kordis-cloud-gha-infra`
- `AWS_DEPLOY_SITE_ROLE_ARN` = `arn:aws:iam::<ACCOUNT_ID>:role/kordis-cloud-gha-site`
- `AWS_CFN_EXECUTION_ROLE_ARN` = `arn:aws:iam::<ACCOUNT_ID>:role/kordis-cloud-cfn-exec`

### 7. Merge, verify, then remove the old keys
1. Merge this PR only after steps 1 to 6. Every merge deploys, and jobs fail at "Configure AWS credentials" if a variable is missing.
2. Run the workflow once with **Run workflow** (it forces an infra deploy) and check that all jobs are green.
3. Delete the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` repository secrets, then deactivate and delete that IAM user's access key.

## Rollback
Revert this PR. The old key secrets keep working until step 7.3, so do 7.3 only after a green OIDC run.
