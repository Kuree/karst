from karst.stmt import *
from karst.model import MemoryModel, Memory
from karst.codegen import CodeGen
import os


class CppCodeGen(CodeGen):
    CPP_INDENT = 4 * " "
    MEMORY_NAME = "mem"
    GLOBAL_EVAL_FUNC_NAME = "global_eval"

    def __init__(self, model: MemoryModel):
        super().__init__(model)

    def code_gen(self) -> str:
        # return a string
        s = ""
        template_class = "T"
        endl = os.linesep

        # class header
        s += f"template<class {template_class}>{endl}"
        s += f"class {self._model.model_name} {{{endl}"

        # declare everything as public
        s += f"public:{endl}"

        # output the variables
        s += self._code_gen_variables(1)
        # output memory
        s += self._code_gen_memory(template_class, 1)

        s += endl
        # functions
        use_global_eval = len(self._model.get_global_stmts()) > 0
        s += self._code_gen_actions(1, use_global_eval)

        # global statements
        if use_global_eval:
            s += self._code_gen_global_stmts(1)

        s += "};"

        return s

    def _code_gen_memory(self, t: str, indent_num: int):
        size = self._model.memory_size.eval()
        indent = indent_num * self.CPP_INDENT
        endl = os.linesep
        return f"{indent}{t} {self.MEMORY_NAME}[{size}];{endl}"

    def _code_gen_actions(self, indent_num: int,
                          use_global_eval: bool = False) -> str:
        indent = self.__get_indent(indent_num)
        endl = os.linesep
        s = ""

        action_stmts = self._model.produce_statements()
        for action_name in action_stmts:
            stmts = action_stmts[action_name]
            # FIXME: using all void for now
            s += f"{indent}void {action_name}() {{{endl}"
            for stmt in stmts:
                s += self._code_gen_stmts(stmt, indent_num + 1)
            if use_global_eval:
                indent_ = self.__get_indent(indent_num + 1)
                s += f"{endl}{indent_}{self.GLOBAL_EVAL_FUNC_NAME}();{endl}"
            s += f"{indent}}}{endl}{endl}"

        return s

    @classmethod
    def __get_indent(cls, indent_num):
        return indent_num * cls.CPP_INDENT

    def _code_gen_global_stmts(self, indent_num: int) -> str:
        indent = self.__get_indent(indent_num)
        endl = os.linesep
        s = ""

        stmts = self._model.get_global_stmts()
        s += f"{indent}void {self.GLOBAL_EVAL_FUNC_NAME}() {{{endl}"
        for stmt in stmts:
            s += self._code_gen_stmts(stmt, indent_num + 1)
        s += f"{indent}}}{endl}{endl}"
        return s

    @classmethod
    def _code_gen_stmts(cls, stmt: Statement, indent_num: int) -> str:
        indent = cls.__get_indent(indent_num)
        endl = os.linesep
        s = ""
        if isinstance(stmt, If):
            s += cls._code_gen_if(endl, indent, indent_num, stmt)
        elif isinstance(stmt, ReturnStatement):
            # we don't return in C++ code as we can't return a list of stuff
            # easily. maybe tuple? need to double check with HLS
            pass
        elif isinstance(stmt, AssignStatement):
            left = cls._code_gen_expr(stmt.left)
            right = cls._code_gen_expr(stmt.right)
            s += f"{indent}{left} = {right};{endl}"
        else:
            raise NotImplemented(stmt)
        return s

    @classmethod
    def _code_gen_if(cls, endl, indent, indent_num, stmt):
        s = ""
        predicate = cls._code_gen_expr(stmt.predicate)
        s += f"{indent}if ({predicate}) {{{endl}"
        for stmt_ in stmt.expressions:
            s += cls._code_gen_stmts(stmt_, indent_num + 1)
        if stmt.else_expressions:
            s += f"{indent}}} else {{{endl}"
            for stmt_ in stmt.else_expressions:
                s += cls._code_gen_stmts(stmt_, indent_num + 1)
        s += f"{indent}}}{endl}"
        return s

    def _code_gen_variables(self, indent_num: int):
        indent = self.__get_indent(indent_num)
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

    @classmethod
    def _code_gen_var(cls, var: Variable) -> str:
        if var.bit_width == 1:
            return f"bool {var.name}"
        else:
            return f"unsigned int {var.name}"

    @classmethod
    def _code_gen_mem_access(cls, mem_access: Memory.MemoryAccess) -> str:
        var = cls._code_gen_expr(mem_access.var)
        return f"{cls.MEMORY_NAME}[{var}]"

    def code_gen_to_file(self, filename: str):
        with open(filename, "w+") as f:
            f.write(self.code_gen())
