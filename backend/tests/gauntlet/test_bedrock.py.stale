import pytest
import json
from io import BytesIO
from src.gauntlet.bedrock import invoke_bedrock, call_extraction_with_fallback, HAIKU_MODEL_ID, SONNET_MODEL_ID

def test_invoke_bedrock_success(mocker):
    mock_client = mocker.MagicMock()
    
    # Valid extraction
    valid_extraction = {
        "schema_version": "1.0",
        "fields": {}
    }
    
    mock_response = {
        "body": BytesIO(json.dumps({
            "content": [{"type": "text", "text": f"```json\n{json.dumps(valid_extraction)}\n```"}]
        }).encode('utf-8'))
    }
    
    mock_client.invoke_model.return_value = mock_response
    
    res = invoke_bedrock(b"image", "image/jpeg", HAIKU_MODEL_ID, bedrock_client=mock_client)
    assert res == valid_extraction
    
def test_invoke_bedrock_decode_error(mocker):
    mock_client = mocker.MagicMock()
    
    mock_response = {
        "body": BytesIO(json.dumps({
            "content": [{"type": "text", "text": "This is not JSON"}]
        }).encode('utf-8'))
    }
    
    mock_client.invoke_model.return_value = mock_response
    
    res = invoke_bedrock(b"image", "image/jpeg", HAIKU_MODEL_ID, bedrock_client=mock_client)
    assert res is None

def test_fallback_success_on_first_try(mocker):
    mock_invoke = mocker.patch("src.gauntlet.bedrock.invoke_bedrock")
    mock_invoke.return_value = {"schema_version": "1.0", "fields": {}}
    
    res = call_extraction_with_fallback(b"image", "image/jpeg", bedrock_client=mocker.MagicMock())
    assert res == {"schema_version": "1.0", "fields": {}}
    # Haiku called, Sonnet not called
    mock_invoke.assert_called_once_with(b"image", "image/jpeg", HAIKU_MODEL_ID, mocker.ANY)

def test_fallback_success_on_second_try(mocker):
    mock_invoke = mocker.patch("src.gauntlet.bedrock.invoke_bedrock")
    # First try returns invalid schema (missing fields)
    # Second try returns valid
    mock_invoke.side_effect = [
        {"schema_version": "0.1"},
        {"schema_version": "1.0", "fields": {}}
    ]
    
    res = call_extraction_with_fallback(b"image", "image/jpeg", bedrock_client=mocker.MagicMock())
    assert res == {"schema_version": "1.0", "fields": {}}
    assert mock_invoke.call_count == 2
    # Verify Sonnet was called second
    assert mock_invoke.call_args_list[1][0][2] == SONNET_MODEL_ID

def test_fallback_failure_both(mocker):
    mock_invoke = mocker.patch("src.gauntlet.bedrock.invoke_bedrock")
    mock_invoke.side_effect = [None, None]
    
    res = call_extraction_with_fallback(b"image", "image/jpeg", bedrock_client=mocker.MagicMock())
    assert res is None
    assert mock_invoke.call_count == 2
