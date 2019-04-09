from karst.stmt import *
from karst.model import MemoryModel, Memory
import abc
import os


class CodeGen:
    def __init__(self, model: MemoryModel):
        self._model = model

    def code_gen(self) -> str:
        """return the code as a str"""

    def _code_gen_expr(self, expr: Union[Expression,
                                         Value,
                                         int]) -> str:
        if isinstance(expr, Expression):
            left = self._code_gen_expr(expr.left)
            right = self._code_gen_expr(expr.right)
            use_parentheses_left = isinstance(expr.left, Expression)
            use_parentheses_right = isinstance(expr.right, Expression)
            if use_parentheses_left:
                left = f"({left})"
            if use_parentheses_right:
                right = f"({right})"
            op = Value.ops[expr.op]
            return f"{left} {op} {right}"
        elif isinstance(expr, Memory.MemoryAccess):
            return self._code_gen_mem_access(expr)
        elif isinstance(expr, Value):
            return self._code_gen_var_name(expr)
        else:
            assert isinstance(expr, int)
            return str(expr)

    def _code_gen_var_name(self, var: Value) -> str:
        if isinstance(var, (Const, Configurable)):
            return var.eval()
        else:
            assert isinstance(var, Value)
            return var.name

    @abc.abstractmethod
    def _code_gen_var(self, var: Variable,
                      in_func_signature: bool = False) -> str:
        """return variable declaration"""

    @abc.abstractmethod
    def _code_gen_mem_access(self, mem_access: Memory.MemoryAccess) -> str:
        """return memory access code"""

    def _code_gen_assign(self, stmt: AssignStatement, eq: str = "="):
        left = self._code_gen_expr(stmt.left)
        right = self._code_gen_expr(stmt.right)
        return f"{left} {eq} {right}"

    @classmethod
    @abc.abstractmethod
    def _get_indent(cls, indent_num) -> str:
        """return indentation"""

    def _code_gen_variables(self, indent_num: int, use_ports: bool = True,
                            include_rdy_en: bool = True):
        indent = self._get_indent(indent_num)
        endl = os.linesep
        s = ""

        variables = self._model.get_variables().copy()
        if use_ports:
            variables.update(self._model.get_ports().copy())
        used_vars = set()
        if not include_rdy_en:
            # we need to filter out the rdy en signal
            for action_name in self._model.produce_statements():
                rdy_name = f"RDY_{action_name}"
                en_name = f"EN_{action_name}"
                used_vars.add(rdy_name)
                used_vars.add(en_name)
                used_vars.add(self._model[rdy_name].name)
                used_vars.add(self._model[en_name].name)

        for var_name in variables:
            var = variables[var_name]
            if var.name in used_vars:
                continue
            else:
                used_vars.add(var.name)
            var_str = self._code_gen_var(var, in_func_signature=True)
            s += f"{indent}{var_str};{endl}"
        return s
