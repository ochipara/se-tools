import os
import tempfile
from setool.config.models import SetoolConfig
from setool.graph.graph import ProgramGraph
from setool.discovery.files import discover_files
from setool.discovery.modules import filepath_to_module, get_package_hierarchy
from setool.discovery.symbols import analyze_file
from setool.graph.nodes import NodeKind
from setool.graph.edges import EdgeKind

def test_file_discovery():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "src", "pkg"))
        open(os.path.join(d, "src", "pkg", "a.py"), "w").close()
        open(os.path.join(d, "src", "pkg", "b.txt"), "w").close()

        config = SetoolConfig(project_root=d, include=["src/**/*.py"])
        files = discover_files(config)
        assert len(files) == 1
        assert files[0].endswith("a.py")

def test_module_name_conversion():
    root = "/project"
    assert filepath_to_module("/project/src/a.py", root) == "src.a"
    assert filepath_to_module("/project/src/pkg/__init__.py", root) == "src.pkg"

def test_get_package_hierarchy():
    pkgs = get_package_hierarchy("src.pkg.mod")
    assert len(pkgs) == 2
    assert pkgs[0] == ("src", "src")
    assert pkgs[1] == ("src.pkg", "pkg")

    pkgs2 = get_package_hierarchy("mod")
    assert len(pkgs2) == 0

def test_symbol_discovery():
    source = """
import os
from typing import List

class MyClass(BaseClass):
    def my_method(self):
        pass

def my_func():
    pass
"""
    with tempfile.TemporaryDirectory() as d:
        filepath = os.path.join(d, "test_pkg", "test_mod.py")
        os.makedirs(os.path.dirname(filepath))
        with open(filepath, "w") as f:
            f.write(source)

        graph = ProgramGraph()
        analyze_file(filepath, d, graph)

        # Test package creation
        assert "test_pkg" in graph.nodes
        assert graph.nodes["test_pkg"].kind == NodeKind.PACKAGE

        assert "test_pkg.test_mod" in graph.nodes
        assert graph.nodes["test_pkg.test_mod"].kind == NodeKind.MODULE

        assert "test_pkg.test_mod::MyClass" in graph.nodes
        assert graph.nodes["test_pkg.test_mod::MyClass"].kind == NodeKind.CLASS

        assert "test_pkg.test_mod::MyClass.my_method" in graph.nodes
        assert graph.nodes["test_pkg.test_mod::MyClass.my_method"].kind == NodeKind.METHOD

        assert "test_pkg.test_mod.my_func" in graph.nodes
        assert graph.nodes["test_pkg.test_mod.my_func"].kind == NodeKind.FUNCTION

        # Check edges
        contains_edges = [e for e in graph.edges if e.kind == EdgeKind.CONTAINS]
        assert any(e.source == "test_pkg" and e.target == "test_pkg.test_mod" for e in contains_edges)
        assert any(e.source == "test_pkg.test_mod" and e.target == "test_pkg.test_mod::MyClass" for e in contains_edges)

        import_edges = [e for e in graph.edges if e.kind == EdgeKind.IMPORTS]
        assert any(e.target == "os" for e in import_edges)
        assert any(e.target == "typing" for e in import_edges)

        inherit_edges = [e for e in graph.edges if e.kind == EdgeKind.INHERITS]
        assert any(e.source == "test_pkg.test_mod::MyClass" and e.target == "BaseClass" for e in inherit_edges)
