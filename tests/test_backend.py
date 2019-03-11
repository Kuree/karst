from karst.backend import *


def test_condition_extraction():
    fifo = define_fifo(10)
    extract_action_conditions(fifo)


def test_exclusive_expression():
    parent = MemoryModel(10)
    a = Variable("a", 16, parent)
    b = Variable("b", 16, parent)

    exp1 = a > 6
    exp2 = b + a > 5

    assert not is_exclusive_condition(exp1, exp2)
    assert is_exclusive_condition(a > 6, b < 3, a < b)


def test_linear_spacing():
    parent = MemoryModel(10)
    a = Variable("a", 16, parent)

    assert get_linear_spacing(a, a + Const(1), a + Const(2))
    assert get_linear_spacing(a, a + Const(2), a + Const(1))
    assert get_linear_spacing(a + 1, a + 4, a + 7)

    assert not get_linear_spacing(a, a + 3, a + 5)
