import pytest
from src.gauntlet.run import run_gauntlet

def test_run_gauntlet_schema_invalid(mocker):
    # Mock cache miss
    mocker.patch("src.gauntlet.run.get_extraction_cache", return_value=None)
    # Mock bedrock caller returning invalid schema
    bedrock_caller = mocker.MagicMock(return_value={"schema_version": "0.1"})
    
    res = run_gauntlet(b"image", "image/jpeg", "bucket", "etag", bedrock_caller, s3_client=mocker.MagicMock())
    assert res == {"error": "G0_SCHEMA_INVALID"}

def test_run_gauntlet_cache_hit(mocker):
    valid_extraction = {
        "schema_version": "1.0",
        "image": {"width": 100, "height": 100},
        "fields": {
            "mrp": {"raw": "MRP 20", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.9}
        }
    }
    
    mocker.patch("src.gauntlet.run.get_extraction_cache", return_value=valid_extraction)
    bedrock_caller = mocker.MagicMock()
    
    # Mock word index
    mocker.patch("src.gauntlet.run.build_word_index", return_value=[{"word": "MRP", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.9}])
    mocker.patch("src.gauntlet.run.compute_readability", return_value=True)
    mocker.patch("src.gauntlet.run.load_anchors_config", return_value={"mrp": [r"\bmrp\b"]})
    mocker.patch("src.gauntlet.run.load_readability_config", return_value={})
    
    # Mock map_field_result to just return a dummy
    mocker.patch("src.gauntlet.run.map_field_result", return_value={"gauntlet_status": "VERIFIED", "reason_code": None})
    
    res = run_gauntlet(b"image", "image/jpeg", "bucket", "etag", bedrock_caller, s3_client=mocker.MagicMock())
    
    bedrock_caller.assert_not_called()
    assert "gauntlet_results" in res
    assert res["gauntlet_results"]["mrp"] == {"gauntlet_status": "VERIFIED", "reason_code": None}

def test_run_gauntlet_cache_miss_valid_schema(mocker):
    valid_extraction = {
        "schema_version": "1.0",
        "image": {"width": 100, "height": 100},
        "fields": {
            "mrp": {"raw": "MRP 20", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.9}
        }
    }
    
    mocker.patch("src.gauntlet.run.get_extraction_cache", return_value=None)
    mock_put_cache = mocker.patch("src.gauntlet.run.put_extraction_cache")
    bedrock_caller = mocker.MagicMock(return_value=valid_extraction)
    
    mocker.patch("src.gauntlet.run.build_word_index", return_value=[])
    mocker.patch("src.gauntlet.run.compute_readability", return_value=True)
    mocker.patch("src.gauntlet.run.load_anchors_config", return_value={})
    mocker.patch("src.gauntlet.run.load_readability_config", return_value={})
    
    # map_field_result will use actual or mock? Let's mock it
    mocker.patch("src.gauntlet.run.map_field_result", return_value={"gauntlet_status": "ABSENT", "reason_code": "NOT_PRINTED"})
    
    res = run_gauntlet(b"image", "image/jpeg", "bucket", "etag", bedrock_caller, s3_client=mocker.MagicMock())
    
    bedrock_caller.assert_called_once()
    mock_put_cache.assert_called_once()
    assert res["gauntlet_results"]["mrp"]["gauntlet_status"] == "ABSENT"
