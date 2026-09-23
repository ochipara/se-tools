from setool.config.models import SetoolConfig, EntryPoint

def test_default_config():
    config = SetoolConfig()
    assert config.project_root == "."
    assert config.max_call_depth == 15

def test_config_parsing():
    config = SetoolConfig(
        project_root="/path/to/project",
        entry_points=[EntryPoint(name="main", target="src/main.py::main")]
    )
    assert config.project_root == "/path/to/project"
    assert config.entry_points[0].name == "main"
    assert config.entry_points[0].target == "src/main.py::main"
