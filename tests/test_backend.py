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
    assert is_exclusive_condition(a > 6, b < 3, a - b < 0)
