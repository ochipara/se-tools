import ast
from typing import Dict, Optional, Tuple, List, Union
from ...graph.graph import ProgramGraph
from ...graph.nodes import NodeKind, Node
from ...graph.types import PythonType
from ...graph.edges import Edge, EdgeKind
from ...graph.provenance import Provenance

class ASTTypePropagator(ast.NodeVisitor):
    def __init__(self, graph: ProgramGraph, module_id: str):
        self.graph = graph
        self.module_id = module_id
        self.current_scope = [module_id]
        self.local_types: Dict[str, Dict[str, Tuple[PythonType, Provenance]]] = {module_id: {}}

    def _get_current_scope(self):
        return self.current_scope[-1]

    def _set_local_type(self, name: str, py_type: PythonType, prov: Provenance):
        scope = self._get_current_scope()
        if scope not in self.local_types:
            self.local_types[scope] = {}
        self.local_types[scope][name] = (py_type, prov)

    def _get_local_type(self, name: str) -> Optional[Tuple[PythonType, Provenance]]:
        # Walk up the scope chain
        for scope in reversed(self.current_scope):
            if scope in self.local_types and name in self.local_types[scope]:
                return self.local_types[scope][name]
        return None

    def _build_python_type(self, annotation: ast.AST, prov: Provenance) -> PythonType:
        # Very basic support for generics and unions
        if isinstance(annotation, ast.Subscript):
            base_name = ast.unparse(annotation.value)
            t = PythonType(name=base_name, provenance=prov)

            # Simple generics parsing
            if isinstance(annotation.slice, ast.Tuple):
                for elt in annotation.slice.elts:
                    t.generic_arguments.append(self._build_python_type(elt, prov))
            else:
                t.generic_arguments.append(self._build_python_type(annotation.slice, prov))

            if base_name in ("Union", "Optional"):
                t.kind = "Union"
                t.union_members = list(t.generic_arguments)
            return t
        elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # Python 3.10+ Union syntax: A | B
            t = PythonType(name="Union", kind="Union", provenance=prov)
            t.union_members.append(self._build_python_type(annotation.left, prov))
            t.union_members.append(self._build_python_type(annotation.right, prov))
            return t
        elif isinstance(annotation, ast.Name):
            return PythonType(name=annotation.id, provenance=prov)
        elif isinstance(annotation, ast.Attribute):
            return PythonType(name=ast.unparse(annotation), provenance=prov)
        else:
            return PythonType(name=ast.unparse(annotation), provenance=prov)

    def _get_attribute_type(self, target_type: PythonType, attr_name: str) -> Optional[PythonType]:
        # Very naive attribute lookup in the current file graph
        for nid, n in self.graph.nodes.items():
            if n.kind in (NodeKind.CLASS, NodeKind.PYTORCH_MODULE) and n.name == target_type.name:
                # Look for a method or class attribute matching attr_name
                child_id = f"{nid}.{attr_name}"
                if child_id in self.graph.nodes:
                    child_node = self.graph.nodes[child_id]
                    if child_node.kind == NodeKind.METHOD and child_node.python_type:
                        return child_node.python_type
                # Look for properties/instance attributes (assuming we store them on class later)
                break
        return None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = f"{self.current_scope[-1]}::{node.name}"
        self.current_scope.append(class_id)

        # Check if it inherits from nn.Module
        is_nn_module = False
        for base in node.bases:
            if isinstance(base, ast.Attribute) and base.attr == "Module":
                if isinstance(base.value, ast.Name) and base.value.id == "nn":
                    is_nn_module = True
            elif isinstance(base, ast.Name) and base.id == "Module":
                is_nn_module = True

        if class_id in self.graph.nodes:
            if is_nn_module:
                self.graph.nodes[class_id].kind = NodeKind.PYTORCH_MODULE
                self.graph.nodes[class_id].properties["is_pytorch_module"] = True

            # Simple inheritance tracking for type names
            bases_types = [ast.unparse(b) for b in node.bases]
            self.graph.nodes[class_id].properties["bases"] = bases_types

        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        parent_id = self.current_scope[-1]
        func_id = f"{parent_id}.{node.name}"
        self.current_scope.append(func_id)

        # Register parameter types
        for arg in node.args.args:
            if arg.arg == "self":
                # Inject 'self' type if in a class method
                if "::" in parent_id:
                    class_name = parent_id.split("::")[-1]
                    py_type = PythonType(name=class_name, provenance=Provenance.DECLARED_ANNOTATION)
                    self._set_local_type("self", py_type, Provenance.DECLARED_ANNOTATION)
                continue

            if arg.annotation:
                py_type = self._build_python_type(arg.annotation, Provenance.DECLARED_ANNOTATION)
                self._set_local_type(arg.arg, py_type, Provenance.DECLARED_ANNOTATION)

                # Create a VALUE node for the parameter
                val_id = f"{func_id}::param_{arg.arg}"
                if val_id not in self.graph.nodes:
                    self.graph.nodes[val_id] = Node(id=val_id, kind=NodeKind.VALUE, name=arg.arg, python_type=py_type)
                    self.graph.edges.append(Edge(source=func_id, target=val_id, kind=EdgeKind.CONTAINS, provenance=[Provenance.SOURCE_AST]))

        # Register return type on the function node
        if node.returns and func_id in self.graph.nodes:
            py_type = self._build_python_type(node.returns, Provenance.RETURN_ANNOTATION)
            self.graph.nodes[func_id].python_type = py_type

        self.generic_visit(node)
        self.current_scope.pop()

    def visit_AnnAssign(self, node: ast.AnnAssign):
        py_type = self._build_python_type(node.annotation, Provenance.ATTRIBUTE_ANNOTATION if isinstance(node.target, ast.Attribute) else Provenance.DECLARED_ANNOTATION)

        if isinstance(node.target, ast.Name):
            self._set_local_type(node.target.id, py_type, Provenance.DECLARED_ANNOTATION)
        elif isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == "self":
                self._set_local_type(f"self.{node.target.attr}", py_type, Provenance.ATTRIBUTE_ANNOTATION)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        resolved = False
        new_type = None

        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                func_name = node.value.func.id
                local_type_tuple = self._get_local_type(func_name)

                if local_type_tuple:
                    # e.g., model(x), instance_type is Encoder
                    instance_type, _ = local_type_tuple

                    target_class_id = None
                    for nid, n in self.graph.nodes.items():
                        if n.kind in (NodeKind.CLASS, NodeKind.PYTORCH_MODULE) and n.name == instance_type.name:
                            target_class_id = nid
                            break

                    if target_class_id:
                        class_node = self.graph.nodes[target_class_id]
                        if class_node.kind == NodeKind.PYTORCH_MODULE:
                            forward_id = f"{target_class_id}.forward"
                            if forward_id in self.graph.nodes and self.graph.nodes[forward_id].python_type:
                                ret_type = self.graph.nodes[forward_id].python_type
                                new_type = PythonType(name=ret_type.name, provenance=Provenance.PYTORCH_SEMANTICS)
                                resolved = True

                if not resolved:
                    # Is it a class instantiation in scope?
                    class_id = None
                    for nid, n in self.graph.nodes.items():
                        if n.kind in (NodeKind.CLASS, NodeKind.PYTORCH_MODULE) and n.name == func_name:
                            class_id = nid
                            break
                    if class_id:
                        new_type = PythonType(name=func_name, provenance=Provenance.CONSTRUCTOR)
                        resolved = True
                    else:
                        # Standard function call, do we know the return type?
                        func_id = None
                        for nid, n in self.graph.nodes.items():
                            if n.kind == NodeKind.FUNCTION and n.name == func_name:
                                func_id = nid
                                break
                        if func_id and self.graph.nodes[func_id].python_type:
                            new_type = PythonType(
                                name=self.graph.nodes[func_id].python_type.name,
                                provenance=Provenance.RETURN_ANNOTATION
                            )
                            resolved = True

            elif isinstance(node.value.func, ast.Attribute):
                # e.g. optimizer.step() or obj.method()
                obj = node.value.func.value
                attr_name = node.value.func.attr

                if isinstance(obj, ast.Name):
                    local_type_tuple = self._get_local_type(obj.id)
                    if local_type_tuple:
                        obj_type, _ = local_type_tuple
                        method_ret_type = self._get_attribute_type(obj_type, attr_name)
                        if method_ret_type:
                            new_type = PythonType(name=method_ret_type.name, provenance=Provenance.RETURN_ANNOTATION)
                            resolved = True

        if not resolved and isinstance(node.value, ast.Name):
            source_type_tuple = self._get_local_type(node.value.id)
            if source_type_tuple:
                source_type, _ = source_type_tuple
                new_type = PythonType(name=source_type.name, provenance=Provenance.ASSIGNMENT_PROPAGATION)
                resolved = True

        if not resolved and isinstance(node.value, ast.Attribute):
            # x = obj.attr
            if isinstance(node.value.value, ast.Name):
                source_type_tuple = self._get_local_type(node.value.value.id)
                if source_type_tuple:
                    if node.value.value.id == "self":
                        self_attr_tuple = self._get_local_type(f"self.{node.value.attr}")
                        if self_attr_tuple:
                            new_type = PythonType(name=self_attr_tuple[0].name, provenance=Provenance.ATTRIBUTE_ANNOTATION)
                            resolved = True

        if resolved and new_type:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._set_local_type(target.id, new_type, new_type.provenance)
                elif isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name) and target.value.id == "self":
                        self._set_local_type(f"self.{target.attr}", new_type, Provenance.ATTRIBUTE_ANNOTATION)

        self.generic_visit(node)

def run_type_analysis(graph: ProgramGraph):
    for node_id, node in list(graph.nodes.items()):
        if node.kind == NodeKind.MODULE and node.location:
            try:
                with open(node.location.file, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                propagator = ASTTypePropagator(graph, node_id)
                propagator.visit(tree)

                if "local_types" not in node.properties:
                    node.properties["local_types"] = {}
                for scope, typedict in propagator.local_types.items():
                    node.properties["local_types"][scope] = {k: v[0].name for k, v in typedict.items()}
            except Exception as e:
                pass
