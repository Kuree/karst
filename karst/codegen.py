from karst.stmt import *
from karst.model import MemoryModel, Memory
import abc


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
