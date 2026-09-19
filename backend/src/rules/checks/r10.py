from src.rules.engine import registry

@registry.register("r10_contrast", requires=["net_quantity"])
def check_r10(context):
    return {"status": "PASS"}
