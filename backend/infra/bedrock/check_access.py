import boto3
import json

def check_bedrock():
    session = boto3.Session(profile_name="labelcheck", region_name="ap-south-1")
    bedrock = session.client('bedrock')
    
    models_to_check = [
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-sonnet-4-20250514-v1:0"
    ]
    
    print("Checking Bedrock model access in ap-south-1...")
    
    try:
        response = bedrock.list_foundation_models()
        available_models = [model['modelId'] for model in response['modelSummaries']]
        
        for m in models_to_check:
            if m in available_models:
                print(f"[OK] {m} is available.")
            else:
                print(f"[MISSING] {m} is not available in the list.")
                
        # Also check Inference Profiles if using cross-region inference
        profiles = bedrock.list_inference_profiles()
        print("\nAvailable Inference Profiles:")
        for p in profiles.get('inferenceProfileSummaries', []):
            print(f"- {p['inferenceProfileId']}")
            
    except Exception as e:
        print(f"Error checking Bedrock access: {e}")

if __name__ == "__main__":
    check_bedrock()
