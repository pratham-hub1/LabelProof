import json
import os

def test_ingestion_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ingestion.config')
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    assert 'image/jpeg' in config['allowed_content_types']
    assert 'application/pdf' in config['allowed_content_types']
    assert config['size_cap_bytes'] == 20971520
    assert config['stale_processing_seconds'] == 300
    assert config['upload_timeout_seconds'] == 960
    assert config['presign_expiry_seconds'] == 900
    assert config['scan_id_charset'] == 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
