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


def test_if_eq():
    model = MemoryModel(42)
    v1 = model.Variable("a", 1)
    v2 = model.Variable("b", 1)
    v3 = model.Variable("c", 1)
    v4 = model.Variable("d", 1)

    if_1 = model.If(v1 == v2, v1(0)).Else(v2(0))
    if_2 = model.If(v1 == v2, v1(0)).Else(v3(0))
    if_3 = model.If(v1 == v4, v1(0)).Else(v2(0))
    if_4 = model.If(v1 == v2, v1(0)).Else(v2(0))

    assert if_1.eq(if_4)
    assert not if_1.eq(if_2)
    assert not if_1.eq(if_3)


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
