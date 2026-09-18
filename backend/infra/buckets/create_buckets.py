import boto3
import json

def create_buckets():
    session = boto3.Session(profile_name="labelcheck", region_name="ap-south-1")
    s3 = session.client('s3')
    
    # Bucket names
    uploads_bucket = 'labelcheck-uploads'
    outputs_bucket = 'labelcheck-outputs'
    web_bucket = 'labelcheck-web'
    
    buckets = [uploads_bucket, outputs_bucket, web_bucket]
    
    for bucket in buckets:
        try:
            print(f"Creating {bucket}...")
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
            )
            print(f"Created {bucket}")
        except s3.exceptions.BucketAlreadyOwnedByYou:
            print(f"{bucket} already exists and is owned by you.")
        except s3.exceptions.BucketAlreadyExists:
            print(f"{bucket} already exists and is owned by someone else!")

    # CORS for uploads
    print("Setting CORS for uploads...")
    cors_uploads = {
        'CORSRules': [{
            'AllowedHeaders': ['Content-Type'],
            'AllowedMethods': ['PUT'],
            'AllowedOrigins': ['*'],
            'ExposeHeaders': []
        }]
    }
    s3.put_bucket_cors(Bucket=uploads_bucket, CORSConfiguration=cors_uploads)
    
    # Public read policy for outputs
    print("Setting public-read policy for outputs...")
    # First disable block public access
    s3.put_public_access_block(
        Bucket=outputs_bucket,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False
        }
    )
    
    policy_outputs = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{outputs_bucket}/*"
            }
        ]
    }
    s3.put_bucket_policy(Bucket=outputs_bucket, Policy=json.dumps(policy_outputs))
    
    # CORS for outputs
    print("Setting CORS for outputs...")
    cors_outputs = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': ['*'],
            'ExposeHeaders': []
        }]
    }
    s3.put_bucket_cors(Bucket=outputs_bucket, CORSConfiguration=cors_outputs)
    
    print("Setting static website for web bucket...")
    s3.put_bucket_website(
        Bucket=web_bucket,
        WebsiteConfiguration={
            'ErrorDocument': {'Key': 'index.html'},
            'IndexDocument': {'Suffix': 'index.html'}
        }
    )
    
    print("Buckets created and configured.")

if __name__ == "__main__":
    create_buckets()
