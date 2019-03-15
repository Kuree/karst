from karst.backend import *
import pytest

from karst.basic import define_sram, define_fifo, define_line_buffer


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


def test_expression_preprocess():
    var1 = Variable("a", 1, None)
    var2 = Variable("b", 1, None)
    exp0 = var1
    exp1 = var1 % 5
    exp2 = var2 % 5
    exp3 = var1 % 10
    r = preprocess_expressions(exp1)
    assert r[0].eq(var1)
    r = preprocess_expressions(exp1, exp3)
    assert r[0].eq(exp1) and r[1].eq(exp3)
    r = preprocess_expressions(exp1, exp2)
    assert r[0].eq(var1) and r[1].eq(var2)
    r = preprocess_expressions(exp0, exp1, exp2)
    assert r[0].eq(var1) and r[1].eq(var1) and r[2].eq(var2)


def test_linear_spacing():
    parent = MemoryModel(10)
    a = parent.Variable("a", 16)

    assert get_linear_spacing(a, a + Const(1), a + Const(2)) == (True, 1)
    assert get_linear_spacing(a, a + Const(2), a + Const(1)) == (True, 1)
    assert get_linear_spacing(a + 4, a + 1, a + 7) == (True, 3)
    assert get_linear_spacing(a + 4, a + 1, a + 7, a + 7) == (True, 3)

    assert not get_linear_spacing(a, a + 3, a + 5)[0]


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
    read_var_expression = get_var_memory_access(read_access)
    write_var_expression = get_var_memory_access(write_access)
    assert len(read_var_expression) == 1
    assert len(write_var_expression) == 1
    addr = sram.addr
    assert addr in read_var_expression
    assert addr in write_var_expression
    assert len(read_var_expression[addr]) == 1
    assert len(write_var_expression[addr]) == 1
    assert read_var_expression[addr][0][0].name == "addr"
    assert read_var_expression[addr][0][1] == Memory.MemoryAccessType.Read
    assert write_var_expression[addr][0][0].name == "addr"
    assert write_var_expression[addr][0][1] == Memory.MemoryAccessType.Write


def test_fifo_memory_access():
    fifo = define_fifo(20)
    access = get_memory_access(fifo)
    assert len(access) == 2
    enqueue = access["enqueue"]
    dequeue = access["dequeue"]
    assert len(enqueue) == 1
    assert len(dequeue) == 1
    # it's the same as sram test, so we skip the rest
    assert fifo.write_addr in get_var_memory_access(enqueue)
    assert fifo.read_addr in get_var_memory_access(dequeue)


@pytest.mark.parametrize("num_row", [1, 4])
@pytest.mark.parametrize("line_size", [10, 20])
def test_line_buffer_memory_access(num_row, line_size):
    lb = define_line_buffer(line_size, num_row)
    access = get_memory_access(lb)
    enqueue = access["enqueue"]
    dequeue = access["dequeue"]
    assert len(enqueue) == 1
    assert len(dequeue) == num_row
    # we'll focus on dequeue since it's more interesting
    dequeue_exps = get_var_memory_access(dequeue)
    dequeue_exps = dequeue_exps[lb.read_addr]
    assert len(dequeue_exps) == num_row
    read_expr = []
    for exp, rw in dequeue_exps:
        assert rw == Memory.MemoryAccessType.Read
        read_expr.append(exp)
    pred, space = get_linear_spacing(*read_expr)
    assert pred
    if num_row > 1:
        assert space == line_size


def test_fifo_update_states():
    fifo = define_fifo(20)
    statements = fifo.produce_statements()
    stmts = statements["enqueue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 2
    stmts = statements["dequeue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 2


def test_lb_update_states():
    num_row = 4
    line_size = 10
    lb = define_line_buffer(line_size, num_row)
    statements = lb.produce_statements()
    stmts = statements["enqueue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 2
    stmts = statements["dequeue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 2
