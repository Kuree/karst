from karst.backend import *


def test_condition_extraction():
    fifo = define_fifo(10)
    extract_action_conditions(fifo)


def test_exclusive_expression():
    parent = MemoryModel(10)
    a = parent.Variable("a", 16)
    b = parent.Variable("b", 16)

    exp1 = a > 6
    exp2 = b + a > 5

    assert not is_exclusive_condition(exp1, exp2)
    assert is_exclusive_condition(a > 6, b < 3, a < b)


def test_linear_spacing():
    parent = MemoryModel(10)
    a = parent.Variable("a", 16)

    assert get_linear_spacing(a, a + Const(1), a + Const(2))
    assert get_linear_spacing(a, a + Const(2), a + Const(1))
    assert get_linear_spacing(a + 1, a + 4, a + 7)

    assert not get_linear_spacing(a, a + 3, a + 5)


def test_sram_memory_access():
    sram = define_sram(100)
    access = get_memory_access(sram)
    assert len(access) == 2
    read_access = access["read"]
    write_access = access["write"]
    assert len(read_access) == 1
    assert len(write_access) == 1
    assert read_access[0][1] == Memory.MemoryAccessType.Read
    assert write_access[0][1] == Memory.MemoryAccessType.Write
