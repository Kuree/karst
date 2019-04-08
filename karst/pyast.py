import ast
import astor


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

        if_node = ast.Call(func=ast.Attribute(value=ast.Name(id=self.model_name,
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


class ReplaceLoopVar(ast.NodeTransformer):
    def __init__(self, var_name, model_name):
        self.var_name = var_name
        self.model_name = model_name

    def visit_Name(self, node: ast.Name):
        if node.id == self.var_name:
            # convert to attributes
            result = ast.Attribute(value=ast.Name(id=self.model_name,
                                                  ctx=ast.Load()),
                                   attr=self.var_name,
                                   cts=ast.Load())
            return result
        else:
            return node


class ForVarVisitor(ast.NodeTransformer):
    def __init__(self):
        super().__init__()

    def visit_For(self, node: ast.For):
        iter_ = node.iter
        if isinstance(iter_, ast.Call) and isinstance(iter_.func, ast.Name) \
                and iter_.func.id == "range":
            iter_.args = [ast.Call(func=ast.Name(id="int", ctx=ast.Load()),
                                   args=iter_.args,
                                   keywords=[],
                                   ctx=ast.Load())]

        return node


class ForNodeVisitor(ast.NodeTransformer):
    def __init__(self, model_variable_name: str):
        super().__init__()
        self.model_name = model_variable_name
        self.loop_vars = []

    def visit_For(self, node: ast.For):
        iter_ = node.iter
        assert isinstance(iter_, ast.Call) and isinstance(iter_.func, ast.Name)\
            and iter_.func.id == "range",\
            f"only range() is supported, got {astor.to_source(iter_)}"
        range_var = iter_.args[0]
        loop_var = ast.Str(s=node.target.id)
        self.loop_vars.append(node.target.id)
        body = node.body
        for_node = \
            ast.Call(func=ast.Attribute(value=ast.Name(id=self.model_name,
                                                       ctx=ast.Load()),
                                        attr="For",
                                        cts=ast.Load()),
                     args=[range_var, loop_var] + body,
                     keywords=[],
                     ctx=ast.Load)
        return ast.Expr(value=for_node)


class TransformForVisitor:
    def __init__(self, model_name):
        self.model_name = model_name

    def visit(self, node):
        for_ = ForNodeVisitor(self.model_name)
        for_.visit(node)
        for var in for_.loop_vars:
            replace_var = ReplaceLoopVar(var, self.model_name)
            replace_var.visit(node)


class FindActionDefine(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.decorator_list:
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute) and \
                            decorator.func.attr == "action":
                        self.nodes.append(node)
        self.generic_visit(node)


class FindMarkedFunction(ast.NodeVisitor):
    def __init__(self, decorator_name):
        super().__init__()
        self.nodes = []
        self.decorator_name = decorator_name

        self._in_marked_function = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.decorator_list:
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute):
                    if decorator.attr == self.decorator_name:
                        self.nodes.append(node)
                        self._in_marked_function = True
        self.generic_visit(node)
        self._in_marked_function = False


class FindLoopRangeVar(FindMarkedFunction):
    def __init__(self, decorator_name, model_name):
        super().__init__(decorator_name)
        self.model_name = model_name
        self.range_vars = []

    def visit_For(self, node: ast.For):
        if not self._in_marked_function:
            self.generic_visit(node)
            return
        iter_ = node.iter
        if isinstance(iter_, ast.Call) and isinstance(iter_.func, ast.Name) \
                and iter_.func.id == "range":
            # trying to see if there is any model related vars
            # FIXME:
            #       currently only work on range(model.var)
            range_var = iter_.args[0]
            if isinstance(range_var, ast.Attribute):
                if isinstance(range_var.value, ast.Name) \
                        and range_var.value.id == self.model_name:
                    self.range_vars.append(range_var.attr)
        self.generic_visit(node)


class FindModelVariableName(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.name = ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self.name and node.decorator_list:
            n = node.decorator_list[0]
            if isinstance(n, ast.Call):
                self.name = n.func.value.id
                return
        self.generic_visit(node)


def add_model_loop_vars(model_name: str, variables, func_name):
    args = []
    for var in variables:
        assert isinstance(var, str)
        args.append(ast.Str(s=var))
    node = ast.Call(func=ast.Attribute(value=ast.Name(id=model_name,
                                                      ctx=ast.Load()),
                                       attr=func_name,
                                       cts=ast.Load()),
                    args=args,
                    keywords=[],
                    ctx=ast.Load)
    return ast.Expr(value=node)


def add_model_name(model_name: str):
    node = ast.Assign(targets=[ast.Attribute(value=ast.Name(id=model_name,
                                                            ctx=ast.Load()),
                                             attr="model_name",
                                             cts=ast.Load())],
                      value=ast.Str(s=model_name))
    return ast.Expr(value=node)
