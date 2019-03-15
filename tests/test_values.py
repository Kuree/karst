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
    model = MemoryModel(42)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    exp = v1 * v2
    assert exp.eval() == 2 * 3
    exp = v1 * 4
    assert exp.eval() == 2 * 4


def test_rmod():
    model = MemoryModel(42)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    exp = 3 % v1
    assert exp.eval() == 1


def test_le():
    model = MemoryModel(42)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)

    v1(2)
    v2(3)
    assert (v1 <= 4).eval()
    assert (v1 <= v2).eval()


def test_shift():
    model = MemoryModel(42)
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
    model = MemoryModel(42)
    v1 = model.Variable("a", 4)

    v1(5)
    assert (42 - v1).eval() == 42 - 5
    assert (v1 - 1).eval() == 5 - 1


def test_nested_eval():
    model = MemoryModel(42)
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
    model = MemoryModel(42)
    v1 = model.Variable("a", 4)
    v2 = model.Variable("b", 4)
    v1(1)
    v2(2)
    assert (v1 + v2).eval() == 1 + 2
    assert (1 + v1).eval() == 1 + 1


def test_const():
    model = MemoryModel(42)
    v1 = model.Variable("a", 4)
    v1(1)
    v2 = model.Constant("b", v1)
    assert v2.eval() == 1
