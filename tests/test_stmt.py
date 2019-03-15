from karst.stmt import *
from karst.model import *


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


def test_if_bool():
    model = MemoryModel(42)
    v1 = model.Variable("a", 1)

    stmt = model.If(True, v1(1)).Else(v1(2))
    stmt.eval()
    assert v1 == 1


def test_return_eq():
    model = MemoryModel(42)
    v1 = model.Variable("a", 1)
    v2 = model.Variable("b", 1)

    r_1 = model.Return(v1)
    r_2 = model.Return(v2)
    r_3 = model.Return(v1)

    assert not r_1.eq(r_2)
    assert r_1.eq(r_3)
