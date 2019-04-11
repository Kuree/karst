from karst.pyast import *
import astor
import inspect
import textwrap


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
                self.value = int(args[0]) - int(args[1])

    foo = Foo()
    val = 1

    def __test_func():
        if val == (1 + 1 - 1):
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
    src += f"{__test_func.__name__}()\n"
    code = compile(src, "<ast>", "exec")
    exec(code, {"foo": foo, "val": val})
    assert foo.value == 1 + 2
    val = 2
    exec(code, {"foo": foo, "val": val})
    assert foo.value == 2 - 2


def test_for_statement():
    class Value:
        def __init__(self, value):
            self.value = value

    class Foo:
        def __init__(self):
            self.value = 0
            self.idx = Value(0)

        def For(self, range_var, loop_var, *args):
            for __loop_var in range(range_var):
                self.idx.value = __loop_var
                for value in args:
                    self.value += value.value

    def __test_func():
        for idx in range(5):
            idx

    foo = Foo()
    src_text = inspect.getsource(__test_func)
    txt = textwrap.dedent(src_text)
    tree = ast.parse(txt)
    transform = TransformForVisitor("foo")
    transform.visit(tree)
    src = astor.to_source(tree)
    src += f"{__test_func.__name__}()\n"
    code = compile(src, "<ast>", "exec")
    exec(code, {"foo": foo})
    assert foo.value == 10


def test_index_statement():
    lst = [1, 2]

    class Foo:
        def __init__(self):
            self.value = 0

        def __setitem__(self, key, value):
            self.value = key + value

    foo = Foo()

    def __test_func():
        lst["0"] = 42
        foo[1] = 2

    src_text = inspect.getsource(__test_func)
    txt = textwrap.dedent(src_text)
    tree = ast.parse(txt)
    transform = ListIndex("foo")
    transform.visit(tree)
    src = astor.to_source(tree)
    src += f"{__test_func.__name__}()\n"
    code = compile(src, "<ast>", "exec")
    exec(code, {"foo": foo, "lst": lst})
    assert lst[0] == 42
    assert lst[1] == 2
    assert foo.value == 3
