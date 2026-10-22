# GitHub OIDC for kordis.cloud deploys

Finding 4 of the external cost and security review: the workflow used one pair of long-lived AWS keys for every job, including mocked unit tests. This plan replaces them with GitHub OIDC and three narrow roles. The workflow side is in this PR; the AWS side below is applied by Nikos.

Replace `<ACCOUNT_ID>` with the AWS account id. Region is `us-east-1`.

## Who gets what

| Job | AWS access after this change |
|---|---|
| `test-infra` (unit tests, `sam validate --lint`) | none (moto uses fake credentials) |
| `integration-tests` | none (calls the public `https://api.kordis.cloud/`) |
| `e2e-tests` | none |
| `deploy-site` | `gha-kordis-cloud-site`: write the site bucket only |
| `build-deploy-infra`, `cleanup-sam-artifacts` | `gha-kordis-cloud-infra`: drive the two CloudFormation stacks, the SAM artifact bucket, and pass one role to CloudFormation |
| (CloudFormation itself) | `cfn-exec-kordis-cloud`: creates and updates the stack's resources; only CloudFormation can assume it |

Both GitHub roles trust only pushes and manual runs on `main` of `nkordis/kordis.cloud`. A pull request, fork or other branch cannot assume them.

The three role names deliberately do **not** start with `kordis-cloud-`. The execution role may manage `role/kordis-cloud-*` (the stack's Lambda roles), and a shared prefix would let a deploy edit or escalate the deploy roles themselves.

## Steps

Steps 1 to 5 are automated in `scripts/oidc-setup.sh`. In AWS CloudShell run:
```
curl -fsSL https://raw.githubusercontent.com/nkordis/kordis.cloud/main/scripts/oidc-setup.sh -o oidc-setup.sh && bash oidc-setup.sh
```
(Before this PR merges, use `ci/github-oidc` instead of `main` in that URL.) The JSON below is what the script applies.

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

### 3. `gha-kordis-cloud-site` (site upload)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::kordis-cloud" },
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": "arn:aws:s3:::kordis-cloud/*" }
  ]
}
```

### 4. `cfn-exec-kordis-cloud` (used by CloudFormation only)
Trust policy: principal `cloudformation.amazonaws.com`, with `aws:SourceAccount` = `<ACCOUNT_ID>`.

Permissions: what the stack creates, limited to its resources where AWS supports it:
- `dynamodb:*` on `arn:aws:dynamodb:us-east-1:<ACCOUNT_ID>:table/kordis-cloud`
- `lambda:*` on `arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:kordis-cloud-*`
- `logs:*` on `arn:aws:logs:us-east-1:<ACCOUNT_ID>:log-group:/aws/lambda/kordis-cloud-*`, plus `logs:DescribeLogGroups` on `*` (that call can't be scoped to a prefix)
- `iam:GetRole`, `CreateRole`, `DeleteRole`, `TagRole`, `UntagRole`, `PutRolePolicy`, `DeleteRolePolicy`, `GetRolePolicy`, `ListRolePolicies`, `ListAttachedRolePolicies`, `DetachRolePolicy`, `UpdateAssumeRolePolicy`, `PassRole` on `arn:aws:iam::<ACCOUNT_ID>:role/kordis-cloud-*`
- `iam:AttachRolePolicy` on the same roles, **only** with condition `ArnEquals` `iam:PolicyARN` = `arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole` or `arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess` (the two managed policies SAM attaches), so a deploy can never attach an admin policy
- `s3:*` on `arn:aws:s3:::kordis-cloud` (bucket settings and policy, not objects)
- `s3:GetObject` on `arn:aws:s3:::aws-sam-cli-managed-default-samclisourcebucket-*/*` (Lambda reads the code package with the caller's permissions)
- `apigateway:*` on `arn:aws:apigateway:us-east-1::/*` (API Gateway has no useful per-API scoping at create time)
- `cloudfront:*` on `*` and `acm:DescribeCertificate`, `acm:RequestCertificate`, `acm:DeleteCertificate`, `acm:AddTagsToCertificate` on `*` (CloudFront and ACM ids are not known in advance)
- `route53:GetHostedZone`, `ChangeResourceRecordSets`, `ListResourceRecordSets`, `GetChange` on `arn:aws:route53:::hostedzone/Z05030141Q82CAW2GKME0` and `arn:aws:route53:::change/*`
- `xray:*` is not needed (the functions' own roles get X-Ray write access)

These were written from the template, not tested against the account. Step 7 tests them with a real change before anything depends on them.

### 5. `gha-kordis-cloud-infra` (SAM deploy and artifact cleanup)
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
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/cfn-exec-kordis-cloud",
      "Condition": { "StringEquals": { "iam:PassedToService": "cloudformation.amazonaws.com" } } }
  ]
}
```

### 6. GitHub repository variables
Settings → Secrets and variables → Actions → **Variables** (not secrets; role ARNs are not sensitive):
- `AWS_DEPLOY_INFRA_ROLE_ARN` = `arn:aws:iam::<ACCOUNT_ID>:role/gha-kordis-cloud-infra`
- `AWS_DEPLOY_SITE_ROLE_ARN` = `arn:aws:iam::<ACCOUNT_ID>:role/gha-kordis-cloud-site`
- `AWS_CFN_EXECUTION_ROLE_ARN` = `arn:aws:iam::<ACCOUNT_ID>:role/cfn-exec-kordis-cloud`

### 7. Test the execution role, merge, then remove the old keys
1. **Test `cfn-exec-kordis-cloud` with a real change first.** A run with nothing to change creates an empty changeset and never uses the role, so a green run alone proves nothing. A real update that hits AccessDenied rolls back as the same role and can leave the stack in `UPDATE_ROLLBACK_FAILED`, which blocks every later deploy. Locally, with your admin credentials:
   ```
   sam build && sam deploy --role-arn arn:aws:iam::<ACCOUNT_ID>:role/cfn-exec-kordis-cloud \
     --parameter-overrides ReservedConcurrency=1
   ```
   then the same command with `ReservedConcurrency=2` to set it back. (If your account can't reserve concurrency and samconfig sets `ReservedConcurrency=0`, use a local, uncommitted edit instead, e.g. `RetentionInDays: 7` on one log group, deploy, then deploy again without it.) If it fails, the stack event names the missing action; add it and repeat. If the stack is ever stuck in `UPDATE_ROLLBACK_FAILED`, run `aws cloudformation continue-update-rollback --stack-name kordis-cloud --role-arn <a role with admin rights>`.
2. Merge this PR only after steps 1 to 6 and 7.1. Every merge deploys, and jobs fail at "Configure AWS credentials" if a variable is missing.
3. Run the workflow once with **Run workflow** and check that all jobs are green.
4. Delete the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` repository secrets, then deactivate and delete that IAM user's access key.

## Rollback
Revert this PR. The old key secrets keep working until step 7.4, so do 7.4 only after a green OIDC run.
