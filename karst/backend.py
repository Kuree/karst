import sympy
from karst.model import *
from typing import Dict


def construct_sym_expr_tree(expression: Expression,
                            symbol_table: Dict[str, sympy.Symbol]):
    left = expression.left
    right = expression.right

    if isinstance(left, Expression):
        left = construct_sym_expr_tree(left, symbol_table)
    elif isinstance(left, Const):
        left = left.value
    else:
        assert isinstance(left, Variable)
        if left.name not in symbol_table:
            symbol_table[left.name] = sympy.Symbol(left.name, integer=True)
        left = symbol_table[left.name]

    if isinstance(right, Expression):
        right = construct_sym_expr_tree(right, symbol_table)
    elif isinstance(right, Const):
        right = right.value
    else:
        assert isinstance(right, Variable)
        if right.name not in symbol_table:
            symbol_table[right.name] = sympy.Symbol(right.name, integer=True)
        right = symbol_table[right.name]

    if expression.op == operator.eq:
        op = sympy.Eq
    else:
        op = expression.op
    return op(left, right)


def extract_action_conditions(model: MemoryModel):
    conditions = model.get_conditions()
    if len(conditions) == 0:
        return
    sym_conditions = {}
    symbol_table = {}
    for name, condition in conditions.items():
        # create symbols for each of them
        sym_conditions[name] = []
        for cond in condition:
            sym_expr = construct_sym_expr_tree(cond, symbol_table)
            sym_conditions[name].append(sym_expr)

    return sym_conditions
