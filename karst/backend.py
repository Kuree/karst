from karst.model import *
from typing import Dict
import z3


def construct_sym_expr_tree(expression: Union[Expression, Variable],
                            symbol_table: Dict[str, z3.Int]):
    if isinstance(expression, Const):
        return expression.value
    elif isinstance(expression, Variable):
        if expression.name not in symbol_table:
            symbol_table[expression.name] = z3.Int(expression.name)
        return symbol_table[expression.name]

    left = expression.left
    right = expression.right

    if isinstance(left, Expression):
        left = construct_sym_expr_tree(left, symbol_table)
    elif isinstance(left, Const):
        left = left.value
    else:
        assert isinstance(left, Variable)
        if left.name not in symbol_table:
            symbol_table[left.name] = z3.Int(left.name)
        left = symbol_table[left.name]

    if isinstance(right, Expression):
        right = construct_sym_expr_tree(right, symbol_table)
    elif isinstance(right, Const):
        right = right.value
    else:
        assert isinstance(right, Variable)
        if right.name not in symbol_table:
            symbol_table[right.name] = z3.Int(right.name)
        right = symbol_table[right.name]

    return expression.op(left, right)


def extract_action_conditions(model: MemoryModel):
    conditions = model.get_conditions()
    if len(conditions) == 0:
        return
    sym_condition = {}
    symbol_table = {}
    for name, condition in conditions.items():
        # create symbols for each of them
        conditions = []
        for cond in condition:
            sym_expr = construct_sym_expr_tree(cond, symbol_table)
            conditions.append(sym_expr)

        # and all the expect
        cond = conditions[0]
        for next_cond in conditions[1:]:
            cond = z3.And(cond, next_cond)
        sym_condition[name] = cond
    return sym_condition, symbol_table


def is_exclusive_condition(*args):
    symbol_table = {}
    s = z3.Solver()
    for condition in args:
        cond = construct_sym_expr_tree(condition, symbol_table)
        s.add(cond)

    r = s.check()
    return r == z3.unsat


def __abs(x):
    return z3.If(x >= 0, x, -x)


def get_linear_spacing(*args):
    # this function only handles one single variable
    symbol_table = {}
    expressions = []
    for exp in args:
        smt_expr = construct_sym_expr_tree(exp, symbol_table)
        expressions.append(smt_expr)
    assert len(symbol_table) == 1, "Only one variable allowed"
    sym = symbol_table.popitem()
    ints = [0]
    assert sym is not None
    for idx, exp1 in enumerate(expressions):
        for exp2 in expressions[idx + 1:]:
            r = z3.simplify(__abs(exp1 - exp2))
            if not isinstance(r, z3.IntNumRef) or not r.is_int():
                return False
            ints.append(r.as_long())
    int_set = set(ints)
    opt = z3.Optimize()
    gcd = z3.Int("gcd")
    for idx, i in enumerate(int_set):
        v = z3.Int(f"int_{idx}")
        opt.add(v * gcd == i)
    opt.maximize(gcd)
    r = opt.check()
    if r != z3.sat:
        return False
    result = opt.model()
    value = result.eval(gcd).as_long()
    # this is the actual gcd
    # now it's just a simple math trick to verify these are arithmetic
    # sequence
    minimum = min(int_set)
    int_sum = sum(int_set)
    expected_sum = minimum + (len(int_set) - 1) * value * len(int_set) // 2
    return int_sum == expected_sum
