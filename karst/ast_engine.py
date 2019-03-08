from karst.model import MemoryModel, define_fifo
import textwrap
import ast
import astor


def parse_ast(model: MemoryModel):
    trees = {}
    for action_name, txt in model.ast_text.items():
        program_txt = textwrap.dedent(txt)
        tree = ast.parse(program_txt)
        trees[action_name] = tree
    return trees


def extract_action_conditions(model, trees):
    """extract expect command from the actions and then remove them
    since they are not required in the generated verilog"""
    conditions = {}
    for action_name, tree in trees.items():
        nodes_to_remove = set()
        conditions[action_name] = set()
        body = tree.body
        assert len(body) == 1
        context: ast.FunctionDef = body[0]
        for node in ast.walk(context):
            if isinstance(node, ast.Call):
                t = astor.to_source(node)
                if isinstance(node.func, ast.Attribute) \
                        and node.func.attr == "expect":
                    assert len(node.args) == 1
                    arg = node.args[0]
                    text = astor.to_source(arg).strip()
                    nodes_to_remove.add(node)
                    conditions[action_name].add(text)

        class RemoveNode(ast.NodeTransformer):
            def visit(self, n):
                if n in nodes_to_remove:
                    return None
                else:
                    return n
        context = RemoveNode().visit(context)
        print(astor.to_source(context))
        print()
    return conditions


if __name__ == "__main__":
    m = define_fifo(100)
    t = parse_ast(m)
    extract_action_conditions(m, t)
