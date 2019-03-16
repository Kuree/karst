import ast


class AssignNodeVisitor(ast.NodeTransformer):
    def __init__(self):
        super().__init__()

    def visit_Assign(self, node):
        return ast.Expr(value=ast.Call(func=node.targets[0], args=[node.value],
                                       keywords=[]))


class IfNodeVisitor(ast.NodeTransformer):
    def __init__(self, model_variable_name: str):
        super().__init__()
        self.model_name = model_variable_name

    def visit_If(self, node: ast.If):
        predicate = node.test
        expression = node.body
        else_expression = node.orelse

        if_node = ast.Call(func=ast.Attribute(ast.Name(id=self.model_name,
                                                       ctx=ast.Load()),
                                              attr="If",
                                              cts=ast.Load()),
                           args=[predicate] + expression,
                           keywords=[],
                           ctx=ast.Load)
        else_node = ast.Call(func=ast.Attribute(attr="Else", value=if_node,
                                                cts=ast.Load()),
                             args=else_expression, keywords=[])

        return ast.Expr(value=else_node)


class FindActionDefine(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.decorator_list:
            # TODO:
            # change it to a more robust way to detect action definition
            self.nodes.append(node)
        self.generic_visit(node)


class FindModelVariableName(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.name = ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self.name and node.decorator_list:
            n = node.decorator_list[0]
            self.name = n.func.value.id
        self.generic_visit(node)
