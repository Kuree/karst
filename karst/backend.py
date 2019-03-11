from karst.model import *
from typing import Dict
import z3


def construct_sym_expr_tree(expression: Expression,
                            symbol_table: Dict[str, z3.Int]):
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
