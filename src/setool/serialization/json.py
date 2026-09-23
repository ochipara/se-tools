import json
from ..graph.graph import ProgramGraph
from ..config.models import SetoolConfig

def serialize_graph(graph: ProgramGraph, filepath: str):
    with open(filepath, "w") as f:
        f.write(graph.model_dump_json(indent=2))

def deserialize_graph(filepath: str) -> ProgramGraph:
    with open(filepath, "r") as f:
        data = json.load(f)
    return ProgramGraph.model_validate(data)

def serialize_config(config: SetoolConfig, filepath: str):
    with open(filepath, "w") as f:
        f.write(config.model_dump_json(indent=2))

def deserialize_config(filepath: str) -> SetoolConfig:
    with open(filepath, "r") as f:
        data = json.load(f)
    return SetoolConfig.model_validate(data)
