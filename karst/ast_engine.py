import ast
import textwrap
from karst.model import MemoryModel
import astor
import inspect


class AssignNodeVisitor(ast.NodeTransformer):
    def __init__(self):
        super().__init__()

    def visit_Assign(self, node):
        return ast.Call(func=node.targets[0], args=[node.value], keywords=[])


class IfNodeVisitor(ast.NodeTransformer):
    def __init__(self, model: MemoryModel):
        self.__model = model

    def visit_If(self, node: ast.If):
        assert isinstance(node, ast.If)
        # replace it with custom If call
        else_node = ast
        return ast.Call(func=self.__model.If)


def convert_ast(model: MemoryModel, python_src: str):
    program_txt = textwrap.dedent(python_src)
    tree = ast.parse(program_txt)

    if_visit = IfNodeVisitor(model)
    tree = if_visit.visit(tree)
    ast.fix_missing_locations(tree)
    co = compile(tree, "<ast>", "exec")
    exec(co)
