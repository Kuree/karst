from karst.stmt import *
from karst.model import MemoryModel, Memory
from karst.codegen import CodeGen
import os
from typing import Dict


class CppCodeGen(CodeGen):
    CPP_INDENT = 4 * " "
    MEMORY_NAME = "mem"
    GLOBAL_EVAL = "global_eval"

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

        s += "};"

        return s

    def _code_gen_memory(self, t: str, indent_num: int):
        size = self._model.memory_size.eval()
        indent = indent_num * self.CPP_INDENT
        endl = os.linesep
        return f"{indent}{t} {self.MEMORY_NAME}[{size}];{endl}"

    def _code_gen_actions(self, indent_num: int,
                          use_global_eval: bool = False,
                          param_list: Dict[str, List[Variable]] = None) -> str:
        indent = self._get_indent(indent_num)
        endl = os.linesep
        s = ""

        if param_list is None:
            param_list = {}

        action_stmts = self._model.produce_statements()
        global_param = [] if self.GLOBAL_EVAL not in param_list \
            else param_list[self.GLOBAL_EVAL]
        for action_name in action_stmts:
            stmts = action_stmts[action_name]
            param = [] if action_name not in param_list else \
                param_list[action_name]
            if use_global_eval:
                param = self._merge_function_params(param, global_param)
            param = self._get_function_params(param, True)
            s += f"{indent}void {action_name}({param}) {{{endl}"
            for stmt in stmts:
                s += self._code_gen_stmts(stmt, indent_num + 1)
            if use_global_eval:
                indent_ = self._get_indent(indent_num + 1)
                param = self._get_function_params(global_param, False)
                s += f"{endl}{indent_}{self.GLOBAL_EVAL}({param});{endl}"
            s += f"{indent}}}{endl}{endl}"

        if use_global_eval:
            stmts = self._model.get_global_stmts()
            param = [] if self.GLOBAL_EVAL not in param_list else \
                param_list[self.GLOBAL_EVAL]
            param = self._get_function_params(param, True)
            s += f"{indent}void {self.GLOBAL_EVAL}({param}) {{{endl}"
            for stmt in stmts:
                s += self._code_gen_stmts(stmt, indent_num + 1)
            s += f"{indent}}}{endl}{endl}"

        return s

    def _get_function_params(self, param, in_signature: bool):
        param = [self._code_gen_var(var, in_func_signature=in_signature)
                 for var in param]
        param.sort()
        param = ", ".join(param)
        return param

    @classmethod
    def _merge_function_params(cls, params1, params2):
        result_set = set()
        for param in params1:
            result_set.add(param)
        for param in params2:
            result_set.add(param)
        result = list(result_set)
        return result

    @classmethod
    def _get_indent(cls, indent_num):
        return indent_num * cls.CPP_INDENT

    def _code_gen_stmts(self, stmt: Statement, indent_num: int) -> str:
        indent = self._get_indent(indent_num)
        endl = os.linesep
        s = ""
        if isinstance(stmt, If):
            s += self._code_gen_if(endl, indent, indent_num, stmt)
        elif isinstance(stmt, ReturnStatement):
            # we don't return in C++ code as we can't return a list of stuff
            # easily. maybe tuple? need to double check with HLS
            pass
        elif isinstance(stmt, AssignStatement):
            content = self._code_gen_assign(stmt, eq="=")
            s += f"{indent}{content};{endl}"
        else:
            raise NotImplemented(stmt)
        return s

    def _code_gen_if(self, endl, indent, indent_num, stmt):
        s = ""
        predicate = self._code_gen_expr(stmt.predicate)
        s += f"{indent}if ({predicate}) {{{endl}"
        for stmt_ in stmt.expressions:
            s += self._code_gen_stmts(stmt_, indent_num + 1)
        if stmt.else_expressions:
            s += f"{indent}}} else {{{endl}"
            for stmt_ in stmt.else_expressions:
                s += self._code_gen_stmts(stmt_, indent_num + 1)
        s += f"{indent}}}{endl}"
        return s

    def _code_gen_var(self, var: Variable,
                      in_func_signature: bool = False) -> str:
        if not in_func_signature:
            return var.name
        if var.bit_width == 1:
            return f"bool {var.name}"
        else:
            return f"unsigned int {var.name}"

    def _code_gen_mem_access(self, mem_access: Memory.MemoryAccess) -> str:
        var = self._code_gen_expr(mem_access.var)
        return f"{self.MEMORY_NAME}[{var}]"

    def code_gen_to_file(self, filename: str):
        with open(filename, "w+") as f:
            f.write(self.code_gen())


class CPPTester:
    def __init__(self, codegen: CppCodeGen):
        self.codegen = codegen
        self._files_to_copy = []

    def test(self):
        import tempfile
        import subprocess
        import os
        import shutil

        with tempfile.TemporaryDirectory() as dir_name:
            for filename in self._files_to_copy:
                assert os.path.isfile(filename)
                shutil.copy(filename, dir_name)
            src_filename = os.path.join(dir_name, "src.cc")
            self.codegen.code_gen_to_file(src_filename)
            subprocess.check_call(["g++", "-c", src_filename], cwd=dir_name)
