from karst.codegen import *
import os


class BlueSpecCodeGen(CodeGen):
    BSV_INDENT = 3 * " "

    def __init__(self, model: MemoryModel):
        super().__init__(model)

    def code_gen(self) -> str:
        s = ""
        endl = os.linesep

        # write ( synthesize )
        s += f"(* synthesize *){endl}"

        s += f"module {self._model.model_name} (Empty);{endl}"
        # generate variables
        s += self._code_gen_variables(1)

        s += f"endmodule: {self._model.model_name}{endl}"
        return s

    @classmethod
    def _code_gen_var(cls, var: Variable) -> str:
        """return variable declaration"""
        return f"Reg #(Bit#({var.bit_width})) {var.name} <- mkReg({var.eval()})"

    @classmethod
    def _code_gen_mem_access(cls, mem_access: Memory.MemoryAccess) -> str:
        """return memory access code"""

    @classmethod
    def _get_indent(cls, indent_num):
        return indent_num * cls.BSV_INDENT

