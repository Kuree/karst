from karst.backend import *
import pytest

from karst.basic import define_sram, define_fifo, define_line_buffer


def test_exclusive_expression():
    parent = MemoryModel()
    a = parent.Variable("a", 16)
    b = parent.Variable("b", 16)

    exp1 = a > 6
    exp2 = b + a > 5

    assert not is_exclusive_condition(exp1, exp2)
    assert is_exclusive_condition(a > 6, b < 3, a < b)


def test_remove_mod():
    parent = MemoryModel()
    a = parent.Variable("a", 16)
    b = parent.Variable("b", 16)
    exp = (a % b) % b
    new_exp = remove_mod_op(exp)
    assert new_exp.eq(a)


def test_linear_spacing():
    parent = MemoryModel()
    a = parent.Variable("a", 16)

    assert get_linear_spacing(a, a + Const(1), a + Const(2)) == (True, 1)
    assert get_linear_spacing(a, a + Const(2), a + Const(1)) == (True, 1)
    assert get_linear_spacing(a + 4, a + 1, a + 7) == (True, 3)
    assert get_linear_spacing(a + 4, a + 1, a + 7, a + 7) == (True, 3)

    assert not get_linear_spacing(a, a + 3, a + 5)[0]


def test_simple_memory_access():
    parent = MemoryModel()
    a = parent.Variable("a", 16)
    b = parent.Variable("b", 16)
    r = visit_mem_access(a + b)
    assert not r


def test_construct_sym_expr_tree():
    symbol_table = {}
    parent = MemoryModel()
    a = parent.Variable("a", 16)
    b = parent.Constant("b", 2)
    construct_sym_expr_tree(b, symbol_table)
    assert len(symbol_table) == 0
    construct_sym_expr_tree(a, symbol_table)
    assert len(symbol_table) == 1


def test_sram_memory_access():
    sram = define_sram()
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
    fifo = define_fifo()
    access = get_memory_access(fifo)
    assert len(access) == 2
    enqueue = access["enqueue"]
    dequeue = access["dequeue"]
    assert len(enqueue) == 1
    assert len(dequeue) == 1
    # it's the same as sram test, so we skip the rest
    assert fifo.write_addr in get_var_memory_access(enqueue)
    assert fifo.read_addr in get_var_memory_access(dequeue)


@pytest.mark.parametrize("num_row", [4])
@pytest.mark.parametrize("line_size", [10, 20])
def test_line_buffer_memory_access(num_row, line_size):
    lb = define_line_buffer()
    lb.configure(memory_size=1, num_rows=num_row, depth=line_size)
    access = get_memory_access(lb)
    enqueue = access["enqueue"]
    assert len(enqueue) == num_row + 1
    dequeue_exps = get_var_memory_access(enqueue)
    # we'll focus on read out since it's more interesting
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


def test_sram_update_states():
    sram = define_sram()
    statements = sram.produce_statements()
    stmts = statements["read"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 0

    # compute the access pattern temporally
    access = get_memory_access(sram)
    read_access = access["read"]
    read_access_vars = get_var_memory_access(read_access)
    result = get_mem_access_temporal_spacing(variable_update,
                                             list(read_access_vars.keys()))
    assert len(result) == 1
    assert result[sram.addr] is None


def test_fifo_update_states():
    fifo = define_fifo()
    fifo.configure(memory_size=4, capacity=4)
    statements = fifo.produce_statements()
    stmts = statements["enqueue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 3
    stmts = statements["dequeue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 3

    access = get_memory_access(fifo)
    dequeue_access = access["dequeue"]
    dequeue_access_vars = get_var_memory_access(dequeue_access)
    result = get_mem_access_temporal_spacing(variable_update,
                                             list(dequeue_access_vars.keys()))
    assert len(result) == 1
    assert result[fifo.read_addr] == 1


def test_lb_update_states():
    num_row = 4
    line_size = 10
    lb = define_line_buffer()
    lb.configure(memory_size=64, num_rows=num_row, depth=line_size)
    statements = lb.produce_statements()
    stmts = statements["enqueue"]
    updates = get_state_updates(stmts)
    variable_update = get_updated_variables(updates)
    assert len(variable_update) == 2
