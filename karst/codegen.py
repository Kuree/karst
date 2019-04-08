from karst.stmt import *
from karst.model import MemoryModel, Memory
import abc
import os


class CodeGen:
    def __init__(self, model: MemoryModel):
        self._model = model

    def code_gen(self) -> str:
        """return the code as a str"""

    @classmethod
    def _code_gen_expr(cls, expr: Union[Expression,
                                        Value,
                                        int]) -> str:
        if isinstance(expr, Expression):
            left = cls._code_gen_expr(expr.left)
            right = cls._code_gen_expr(expr.right)
            use_parentheses_left = isinstance(expr.left, Expression)
            use_parentheses_right = isinstance(expr.right, Expression)
            if use_parentheses_left:
                left = f"({left})"
            if use_parentheses_right:
                right = f"({right})"
            op = Value.ops[expr.op]
            return f"{left} {op} {right}"
        elif isinstance(expr, Memory.MemoryAccess):
            return cls._code_gen_mem_access(expr)
        elif isinstance(expr, Value):
            return cls._code_gen_var_name(expr)
        else:
            assert isinstance(expr, int)
            return str(expr)

    @classmethod
    def _code_gen_var_name(cls, var: Value) -> str:
        if isinstance(var, (Const, Configurable)):
            return var.eval()
        else:
            assert isinstance(var, Value)
            return var.name

    @classmethod
    @abc.abstractmethod
    def _code_gen_var(cls, var: Variable) -> str:
        """return variable declaration"""

    @classmethod
    @abc.abstractmethod
    def _code_gen_mem_access(cls, mem_access: Memory.MemoryAccess) -> str:
        """return memory access code"""

    @classmethod
    def _code_gen_assign(cls, stmt: AssignStatement, eq: str = "="):
        left = cls._code_gen_expr(stmt.left)
        right = cls._code_gen_expr(stmt.right)
        return f"{left} {eq} {right}"

    @classmethod
    @abc.abstractmethod
    def _get_indent(cls, indent_num) -> str:
        """return indentation"""

    def _code_gen_variables(self, indent_num: int):
        indent = self._get_indent(indent_num)
        endl = os.linesep
        s = ""

        variables = self._model.get_variables().copy()
        variables.update(self._model.get_ports().copy())
        used_vars = set()

        for var_name in variables:
            var = variables[var_name]
            if var.name in used_vars:
                continue
            else:
                used_vars.add(var.name)
            s += f"{indent}{self._code_gen_var(var)};{endl}"
        return s
