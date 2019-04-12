from karst.model import *


def test_eq():
    v1 = Variable("a", 1, None)
    v2 = Variable("b", 1, None)
    c1 = Const(1)
    assert not v1.eq(v2)
    assert not v1.eq(c1)
    assert not c1.eq(v2)

    vv1 = Variable("a", 1, None)
    assert vv1.eq(v1)

    # test expressions
    exp1 = v1 % c1
    exp2 = v2 % c1
    exp3 = vv1 % c1

    assert not exp1.eq(exp2)
    assert exp1.eq(exp3)
    assert not exp1.eq(1)


def test_mul():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    exp = v1 * v2
    assert exp.eval() == 2 * 3
    exp = v1 * 4
    assert exp.eval() == 2 * 4


def test_rmod():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    exp = 3 % v1
    assert exp.eval() == 1


def test_le():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    assert (v1 <= 4).eval()
    assert (v1 <= v2).eval()


def test_shift():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    assert (v1 << 4) == 2 << 4
    assert (v1 << v2) == 2 << 3

    v1(2 << 4)
    assert (v1 >> 2).eval() == 2 << 2
    assert (v1 >> v2).eval() == 2 << 1


def test_sub():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)

    v1(5)
    assert (42 - v1).eval() == 42 - 5
    assert (v1 - 1).eval() == 5 - 1


def test_nested_eval():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)
    v2(4)
    v1.value = v2
    assert v1 == 4


def test_hash_repr():
    v1 = Variable("a", 4, None)
    v2 = Variable("b", 4, None)
    assert hash(v1) != hash(v2)
    assert str(v1) == "a"


def test_add():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)
    v1(1)
    v2(2)
    assert (v1 + v2).eval() == 1 + 2
    assert (1 + v1).eval() == 1 + 1


def test_mod():
    model = MemoryModel()
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)
    v1(3)
    v2(2)
    assert (v1 % 2).eval() == 1
    assert (v1 % v2).eval() == 1


def test_ge():
    model = MemoryModel()
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)
    v1(3)
    v2(2)
    assert (v1 >= v2).eval()
    assert (v1 >= 2).eval()
    assert (2 <= v1).eval()


def test_xor():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4, 4)
    v2 = model.Variable("b", 4, 4)
    assert (v1 ^ v2).eval() == (v1 ^ 4).eval()


def test_or():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4, 1)
    v2 = model.Variable("b", 4, 2)
    assert (v1 | v2).eval() == (v1 | 3).eval()
    assert (v1 | v2).eval() == 3


def test_and():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4, 1)
    v2 = model.Variable("b", 4, 2)
    assert (v1 & v2).eval() == 0
    assert (v1 & 3).eval() == 1


def test_const():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4)
    v1(1)
    v2 = model.Constant("b", v1)
    assert v2.eval() == 1


def test_copy():
    model = MemoryModel(4)
    v1 = model.Variable("a", 4, 4)
    v2 = v1.copy()
    v3 = model.Variable("b", 4, 4)
    assert id(v1) != id(v2)
    assert v1.eq(v2)
    v1(1)
    # because a variable is identified by the name, even the value changes
    # it's still the same variable
    assert v1.eq(v2) and v1.value != v2.value
    exp1 = v1 - v3
    exp2 = exp1.copy()
    assert exp1.eq(exp2)
    exp1.right.value = 2
    assert exp1.eq(exp2)
    assert exp2.right.eval() == 4 and exp1.right.eval() == 2


def test_assign():
    model = MemoryModel(4)
    model.Variable("a", 4, 4)
    model.a = 1
    assert model.context
    assert str(model.context[0]) == "a = 1"


def test_config():
    model = MemoryModel(4)
    model.Configurable("a", 4, 4)

    value = 0
    for i in range(int(model.a)):
        value += 1
    assert value == 4
