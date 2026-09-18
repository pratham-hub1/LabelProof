# Lambda Layers

## 1. Python Dependencies
The `requirements.txt` file contains version-pinned dependencies required for determinism.

To build the layer for AWS Lambda:
```bash
mkdir -p python
pip install -r requirements.txt -t python/
zip -r python_deps_layer.zip python/
```
Deploy this zip as a Lambda layer.

## 2. Tesseract + eng/hin data
You will need a compiled Tesseract binary compatible with Amazon Linux 2023 (Lambda's execution environment) along with `eng.traineddata` and `hin.traineddata` in the `tessdata` directory.

Alternatively, use a pre-built Tesseract layer (e.g. from an AWS Serverless Application Repository or a well-known public layer) that supports `ap-south-1`. Ensure `TESSDATA_PREFIX` is set correctly in the environment (e.g., `/opt/tessdata`).
