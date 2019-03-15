from karst.model import *
from karst.stmt import *
from typing import Dict, Tuple
import z3
import operator


def construct_sym_expr_tree(expression: Union[Expression, Variable],
                            symbol_table: Dict[str, z3.Int]):
    if isinstance(expression, Const):
        return expression.value
    elif isinstance(expression, Variable):
        if expression.name not in symbol_table:
            symbol_table[expression.name] = z3.Int(expression.name)
        return symbol_table[expression.name]
    elif isinstance(expression, int):
        return expression

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


def preprocess_expressions(*args: Union[Expression, Variable]):
    """remove the mod expression at the end to help z3 to simplify
    expressions"""
    has_mod = True
    expressions = list(args)
    for exp in expressions:
        if isinstance(exp, Expression):
            if exp.op != operator.mod:
                has_mod = False
                break
    if not has_mod:
        return expressions
    mod_value = None
    for exp in expressions:
        if isinstance(exp, Expression):
            if mod_value is None:
                mod_value = exp.right
            else:
                if not mod_value.eq(exp.right):
                    return expressions
    # remove the mod at the end
    new_exps = []
    for exp in expressions:
        if isinstance(exp, Expression):
            new_exps.append(exp.left)
        else:
            new_exps.append(exp)
    return new_exps


def get_linear_spacing(*args: Union[Expression, Variable]):
    # this function only handles one single variable
    if len(args) == 1:
        # this is a special case
        return True, 0
    symbol_table = {}
    expressions = []
    # preprocess the expressions and variables
    processed = preprocess_expressions(*args)
    for exp in processed:
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
                return False, 1
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
        return False, 1
    result = opt.model()
    value = result.eval(gcd).as_long()
    # this is the actual gcd
    # now it's just a simple math trick to verify these are arithmetic
    # sequence
    minimum = min(int_set)
    int_sum = sum(int_set)
    expected_sum = minimum + (len(int_set) - 1) * value * len(int_set) // 2
    return int_sum == expected_sum, value


def visit_mem_access(tree: Union[Variable, Expression, Statement]):
    if isinstance(tree, If):
        # it has two expressions
        r_1 = []
        for exp in tree.expressions:
            r_1 += visit_mem_access(exp)
        r_2 = []
        for exp in tree.else_expressions:
            r_2 += visit_mem_access(exp)
        return r_1 + r_2
    elif isinstance(tree, ReturnStatement):
        # it can only be read access
        result = []
        for value in tree.values:
            if isinstance(value, Memory.MemoryAccess):
                result.append((value, Memory.MemoryAccessType.Read))
        return result
    elif isinstance(tree, AssignStatement):
        # this is probably the one we need to care about
        left = tree.left
        right = tree.right
        result = []
        if isinstance(left, Memory.MemoryAccess):
            result.append((left, Memory.MemoryAccessType.Write))
        if isinstance(right, Memory.MemoryAccess):
            result.append((right, Memory.MemoryAccessType.Read))
        return result
    elif isinstance(tree, Expression):
        r_left = visit_mem_access(tree.left)
        r_right = visit_mem_access(tree.right)
        return r_left + r_right
    else:
        return []


def get_memory_access(model: MemoryModel)-> \
        Dict[str, List[Tuple[Memory.MemoryAccess, Memory.MemoryAccessType]]]:
    statements = model.produce_statements()
    # recursive visit the statements
    result = {}
    for name, stmts in statements.items():
        entry = []
        for stmt in stmts:
            r = visit_mem_access(stmt)
            if len(r) > 0:
                entry += r
        # filter out the empty one
        if entry:
            result[name] = entry
    return result


def get_var_memory_access(access_pattern:
                          List[Tuple[Memory.MemoryAccess,
                                     Memory.MemoryAccessType]]):
    access_expressions = []
    for access, t in access_pattern:
        exp = access.var
        access_expressions.append((exp, t))

    # we need to separate the memory access by address lines
    # because the linear spacing only handles one variable
    def __get_variable(exp_: Union[Expression, Variable, Const]) \
            -> Union[Variable, None]:
        if isinstance(exp_, Expression):
            left = __get_variable(exp_.left)
            right = __get_variable(exp_.right)
            if left is None:
                return right
            elif right is None:
                return left
            else:
                assert left.name == right.name, "only one variable supported"
        elif isinstance(exp_, Variable):
            return exp_
        else:
            return None

    variable_access: Dict[Variable,
                          List[Tuple[Expression,
                                     Memory.MemoryAccessType]]] = {}
    for exp, t in access_expressions:
        v = __get_variable(exp)
        assert v is not None
        if v not in variable_access:
            variable_access[v] = []
        variable_access[v].append((exp, t))

    return variable_access


def get_state_updates(expressions):
    def __visit_assignments(node_):
        if isinstance(node_, Expression):
            return __visit_assignments(node_.left) +\
                   __visit_assignments(node_.right)
        elif isinstance(node_, AssignStatement):
            return [node_]
        elif isinstance(node_, If):
            r_1 = []
            for exp_ in node_.expressions:
                r_1 += __visit_assignments(exp_)
            r_2 = []
            for exp_ in node_.else_expressions:
                r_2 += __visit_assignments(exp_)
            return r_1 + r_2
        else:
            return []
    stmts = []
    for exp in expressions:
        r = __visit_assignments(exp)
        r = [node for node in r if not isinstance(node.left,
                                                  Memory.MemoryAccess)]
        if r:
            stmts += r
    # a brute force filter to avoid duplicates
    result = set()
    for stmt in stmts:
        for stmt_ in result:
            if stmt.eq(stmt_):
                continue
        result.add(stmt)
    return result


def get_updated_variables(stmts: List[AssignStatement]):
    """get a list of assignment statements that use variables to update
    the values"""
    result = []
    # we use z3 to simplifier the problem
    for stmt in stmts:
        right = stmt.right
        if isinstance(right, Memory.MemoryAccess):
            continue
        z3_exp = construct_sym_expr_tree(right, {})
        if isinstance(z3_exp, int):
            continue
        z3_exp = z3.simplify(z3_exp)
        if not isinstance(z3_exp, z3.IntNumRef) or not z3_exp.is_int():
            result.append(stmt)
    return result
