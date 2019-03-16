from karst.ast_codegen import *
import astor
import inspect


def test_assign_transform():
    class TestClass:
        def __init__(self):
            self.value = 0

        def __call__(self, *args, **kwargs):
            self.value = args[0]

    test = TestClass()

    txt = "test = 2"
    tree = ast.parse(txt)
    visitor = AssignNodeVisitor()
    visitor.visit(tree)
    ast.fix_missing_locations(tree)
    src = astor.to_source(tree)
    eval(src)
    assert test.value == 2


def test_if_else_transform():
    class Foo:
        def __init__(self):
            self.value = -1
            self.pred = False

        def If(self, pred, *args):
            self.pred = pred
            if pred:
                self.value = int(args[0]) + int(args[1])
            return self

        def Else(self, *args):
            if not self.pred:
                self.value = int(args[0])

    foo = Foo()
    
    def __test_func():
        if 1 == 1:
            1
            2
        else:
            2
            2

    src_text = inspect.getsource(__test_func)
    txt = textwrap.dedent(src_text)
    tree = ast.parse(txt)
    if_ = IfNodeVisitor("foo")
    if_.visit(tree)
    src = astor.to_source(tree)
    src += "__test_func()\n"
    code = compile(src, "<ast>", "exec")
    exec(code, {"foo": foo})
    assert foo.value == 1 + 2
