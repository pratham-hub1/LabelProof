from src.rules.engine import registry

@registry.register("r9_clear_space", requires=["net_quantity"])
def check_r9(context):
    return {"status": "PASS"}
