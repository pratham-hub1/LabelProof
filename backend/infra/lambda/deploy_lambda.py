import boto3
import json
import zipfile
import os

def deploy():
    session = boto3.Session(profile_name="labelcheck", region_name="ap-south-1")
    iam = session.client('iam')
    lam = session.client('lambda')
    s3 = session.client('s3')

    # 1. Create IAM Role for Lambda
    role_name = 'LabelCheckLambdaRole'
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        print(f"Creating role {role_name}...")
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )
        role_arn = role['Role']['Arn']
        print(f"Created role. ARN: {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"Role already exists. ARN: {role_arn}")

    policy_json = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": "arn:aws:s3:::labelcheck-uploads/*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": "arn:aws:s3:::labelcheck-outputs/*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Scan",
                    "dynamodb:Query"
                ],
                "Resource": [
                    "arn:aws:dynamodb:ap-south-1:*:table/scans",
                    "arn:aws:dynamodb:ap-south-1:*:table/scans/index/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": "*"
            }
        ]
    }
    
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName='LabelCheckLambdaPolicy',
        PolicyDocument=json.dumps(policy_json)
    )
    print("Attached inline policy.")

    import time
    print("Waiting for role to propagate...")
    time.sleep(10)

    # 2. Package Lambda
    print("Packaging lambda...")
    lambda_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'lambda')
    zip_path = os.path.join(lambda_dir, 'function.zip')
    with zipfile.ZipFile(zip_path, 'w') as zf:
        handler_path = os.path.join(lambda_dir, 'handler.py')
        if os.path.exists(handler_path):
            zf.write(handler_path, 'handler.py')
        else:
            print(f"handler.py not found at {handler_path}")

    # 3. Create/Update Lambda Function
    func_name = 'labelcheck-handler'
    with open(zip_path, 'rb') as f:
        zip_content = f.read()

    try:
        print(f"Creating lambda function {func_name}...")
        response = lam.create_function(
            FunctionName=func_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='handler.handler',
            Code={'ZipFile': zip_content},
            Timeout=60,
            MemorySize=1024,
            Environment={
                'Variables': {
                    'TABLE_NAME': 'scans',
                    'UPLOADS_BUCKET': 'labelcheck-uploads',
                    'OUTPUTS_BUCKET': 'labelcheck-outputs',
                    'WEB_BUCKET': 'labelcheck-web',
                    'REGION': 'ap-south-1'
                }
            }
        )
        print("Created function.")
    except lam.exceptions.ResourceConflictException:
        print("Function already exists, updating code and config...")
        lam.update_function_code(FunctionName=func_name, ZipFile=zip_content)
        lam.update_function_configuration(
            FunctionName=func_name,
            Environment={
                'Variables': {
                    'TABLE_NAME': 'scans',
                    'UPLOADS_BUCKET': 'labelcheck-uploads',
                    'OUTPUTS_BUCKET': 'labelcheck-outputs',
                    'WEB_BUCKET': 'labelcheck-web',
                    'REGION': 'ap-south-1'
                }
            }
        )
        print("Updated function.")

    # 4. Function URL
    try:
        furl = lam.create_function_url_config(
            FunctionName=func_name,
            AuthType='NONE',
            Cors={
                'AllowOrigins': ['*'],
                'AllowMethods': ['*'],
                'AllowHeaders': ['*']
            }
        )
        print(f"Function URL: {furl['FunctionUrl']}")
        lam.add_permission(
            FunctionName=func_name,
            StatementId='FunctionURLAllowPublic',
            Action='lambda:InvokeFunctionUrl',
            Principal='*',
            FunctionUrlAuthType='NONE'
        )
    except lam.exceptions.ResourceConflictException:
        furl = lam.get_function_url_config(FunctionName=func_name)
        print(f"Function URL already exists: {furl['FunctionUrl']}")

    # 5. S3 Trigger
    print("Setting up S3 trigger...")
    try:
        lam.add_permission(
            FunctionName=func_name,
            StatementId='AllowS3Invoke',
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn='arn:aws:s3:::labelcheck-uploads'
        )
    except lam.exceptions.ResourceConflictException:
        print("S3 trigger permission already exists.")

    s3.put_bucket_notification_configuration(
        Bucket='labelcheck-uploads',
        NotificationConfiguration={
            'LambdaFunctionConfigurations': [
                {
                    'LambdaFunctionArn': lam.get_function(FunctionName=func_name)['Configuration']['FunctionArn'],
                    'Events': ['s3:ObjectCreated:*'],
                    'Filter': {
                        'Key': {
                            'FilterRules': [
                                {'Name': 'prefix', 'Value': 'uploads/'}
                            ]
                        }
                    }
                }
            ]
        }
    )
    print("S3 trigger configured.")

if __name__ == "__main__":
    deploy()
