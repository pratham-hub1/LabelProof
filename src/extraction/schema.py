EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "source_type": {"type": "string"},
        "image": {
            "type": "object",
            "properties": {
                "width": {"type": "number"},
                "height": {"type": "number"}
            },
            "required": ["width", "height"]
        },
        "language": {"type": "string"},
        "brand_guess": {"type": ["string", "null"]},
        "fields": {
            "type": "object",
            "properties": {
                "manufacturer_name": {"$ref": "#/$defs/field_type"},
                "manufacturer_address": {"$ref": "#/$defs/field_type"},
                "generic_name": {"$ref": "#/$defs/field_type"},
                "net_quantity": {"$ref": "#/$defs/field_type"},
                "mfg_date": {"$ref": "#/$defs/field_type"},
                "mrp": {"$ref": "#/$defs/field_type"},
                "consumer_care": {"$ref": "#/$defs/field_type"}
            },
            "required": [
                "manufacturer_name", "manufacturer_address", "generic_name",
                "net_quantity", "mfg_date", "mrp", "consumer_care"
            ]
        }
    },
    "required": ["schema_version", "source_type", "image", "language", "fields"],
    "$defs": {
        "field_type": {
            "type": "object",
            "properties": {
                "raw": {"type": ["string", "null"]},
                "parsed": {"type": ["object", "null"]},
                "confidence": {"type": ["number", "null"]},
                "box": {
                    "type": ["array", "null"],
                    "items": {"type": "number"},
                    "minItems": 4,
                    "maxItems": 4
                }
            },
            "required": ["raw", "parsed", "confidence", "box"]
        }
    }
}

import jsonschema

def validate_schema(data):
    jsonschema.validate(instance=data, schema=EXTRACTION_SCHEMA)
    return data
