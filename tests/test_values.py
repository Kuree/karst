from karst.values import *


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
