import json
import base64
import boto3
from botocore.exceptions import ClientError
from src.gauntlet.run import validate_schema

HAIKU_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
SONNET_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def invoke_bedrock(image_bytes, content_type, model_id, bedrock_client=None):
    """
    Invokes the Bedrock Claude 3 model with the given image.
    """
    if bedrock_client is None:
        bedrock_client = boto3.client('bedrock-runtime')
        
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # We only care about images here. If it's a PDF, the caller should have converted it to images.
    # The extraction prompt would normally be here. For the interface, we just send a minimal prompt.
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": encoded_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract label information according to the schema."
                    }
                ],
            }
        ],
    }
    
    response = bedrock_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )
    
    response_body = json.loads(response.get('body').read())
    # Extract text from Claude 3 response
    content = response_body.get('content', [])
    text = ""
    for item in content:
        if item.get('type') == 'text':
            text += item.get('text', '')
            
    # Try to parse the text as JSON
    try:
        # Often LLMs wrap JSON in markdown blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def call_extraction_with_fallback(image_bytes, content_type, bedrock_client=None):
    """
    Tries Haiku first. If it fails to return valid schema, falls back to Sonnet.
    """
    # Try Haiku
    extraction = invoke_bedrock(image_bytes, content_type, HAIKU_MODEL_ID, bedrock_client)
    
    if extraction and validate_schema(extraction):
        return extraction
        
    # Fallback to Sonnet
    extraction_sonnet = invoke_bedrock(image_bytes, content_type, SONNET_MODEL_ID, bedrock_client)
    return extraction_sonnet
