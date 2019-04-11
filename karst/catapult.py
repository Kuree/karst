from karst.cpp import *
from typing import Set


class CatapultCodeGen(CppCodeGen):
    def __init__(self, model: MemoryModel):
        super().__init__(model)

        # if it uses any inputs or outputs name
        self._ports = self._model.get_ports()

    def code_gen(self) -> str:
        # return a string
        s = ""
        template_class = "T"
        endl = os.linesep

        # class header
        # include ac_int
        s += f'#include "ac_int.h"{endl}'
        s += f"{self._code_gen_template(template_class)}{endl}"
        s += f"class {self._model.model_name} {{{endl}"

        # declare everything as public
        s += f"public:{endl}"

        # output the variables
        s += self._code_gen_variables(1, use_ports=False, include_rdy_en=False)
        # output memory
        s += self._code_gen_memory(template_class, 1)

        s += endl
        # functions
        param_list = self._get_action_param()
        use_global_eval = len(self._model.get_global_stmts()) > 0
        s += self._code_gen_actions(1, use_global_eval, param_list)

        s += "};"

        return s

    def _code_gen_template(self, template_class: str):
        # configs
        configs = [""]
        config_vars = self._model.get_config_vars()
        for var_name in config_vars:
            if var_name == self._model.MEMORY_SIZE:
                # we don't need that here
                continue
            var = config_vars[var_name]
            # no aliasing here
            assert var.name == var_name
            configs.append(self._code_gen_var(var, use_ac_int=False,
                                              in_func_signature=True,
                                              use_reference=False))
        config_str = ", ".join(configs)
        return f"template<class {template_class}{config_str}>"

    @classmethod
    def _code_gen_var(cls, var: Variable, use_ac_int: bool = True,
                      use_reference: bool = True,
                      signed: bool = False,
                      in_func_signature: bool = False) -> str:
        if not in_func_signature:
            return var.name
        ref = "&" if (use_reference and in_func_signature) else ""
        if use_ac_int and signed:
            sign = "true"
        elif use_ac_int and not signed:
            sign = "false"
        elif not use_ac_int and signed:
            sign = "signed"
        else:
            sign = "unsigned"
        if var.bit_width == 1:
            return f"bool {ref}{var.name}"
        else:
            if use_ac_int:
                return f"ac_int<{var.bit_width}, {sign}> {ref}{var.name}"
            else:
                return f"{sign} int {ref}{var.name}"

    def _code_gen_var_name(self, var: Value) -> str:
        # we want it configurable to the hls
        if isinstance(var, Const):
            return var.eval()
        elif var.name == self._model.MEMORY_SIZE:
            return var.eval()
        return var.name

    def _get_action_param(self):
        action_stmts = self._model.produce_statements().copy()
        result = {}
        if self._model.get_global_stmts():
            action_stmts[self.GLOBAL_EVAL] = \
                self._model.get_global_stmts()
        for action_name, stmts in action_stmts.items():
            s = self._get_func_signature(stmts)
            param = list(s)
            param.sort()
            result[action_name] = param

        return result

    def _get_func_signature(self, stmts: List[Statement]) -> Set[Variable]:
        port_names = set()
        # we need to carefully about port aliasing
        for _, port in self._ports.items():
            port_names.add(port.name)

        def get_port_var(expr: Union[Expression, Value]) -> List[Variable]:
            if isinstance(expr, Expression):
                left_var = get_port_var(expr.left)
                right_var = get_port_var(expr.right)
                return left_var + right_var
            elif isinstance(expr, Memory.MemoryAccess):
                return get_port_var(expr.var)
            elif isinstance(expr, Variable):
                if expr.name in port_names:
                    return [expr]
            return []

        def get_port_var_stmt(statement: Union[Statement, Expression]):
            if isinstance(statement, If):
                result_ = get_port_var(statement.predicate)
                for stmt_ in statement.expressions:
                    result_ += get_port_var_stmt(stmt_)
                for stmt_ in statement.else_expressions:
                    result_ += get_port_var_stmt(stmt_)
                return result_
            elif isinstance(statement, ReturnStatement):
                result_ = []
                for var_ in statement.values:
                    result_.append(var_)
                return result_
            else:
                assert isinstance(statement, AssignStatement)
                left_var = get_port_var(statement.left)
                right_var = get_port_var(statement.right)
                return left_var + right_var

        result = set()
        for stmt in stmts:
            r = get_port_var_stmt(stmt)
            for var in r:
                result.add(var)
        return result


class CatapultTester(CPPTester):
    def __init__(self, codegen: CppCodeGen):
        super().__init__(codegen)
        # download the ac_int and put it to the
        # I hope this file exists forever
        ac_int = "ac_int.h"
        url = "https://cdn.jsdelivr.net/gh/jonmcdonald/" \
              "imagep/fpga_sw/jpegcpp/catapult/ac_int.h"
        import os
        path = os.path.dirname(os.path.abspath(__file__))
        ac_int_path = os.path.join(path, ac_int)
        if not os.path.isfile(ac_int_path):
            import urllib.request
            urllib.request.urlretrieve(url, ac_int_path)
            assert os.path.isfile(ac_int_path)

        self._files_to_copy.append(ac_int_path)
