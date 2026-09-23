import json
import os
from setool.config.models import SetoolConfig
from setool.graph.graph import ProgramGraph

def generate_schemas():
    os.makedirs("schemas", exist_ok=True)
    with open("schemas/config.schema.json", "w") as f:
        json.dump(SetoolConfig.model_json_schema(), f, indent=2)

    with open("schemas/program-graph.schema.json", "w") as f:
        json.dump(ProgramGraph.model_json_schema(), f, indent=2)

if __name__ == "__main__":
    generate_schemas()
