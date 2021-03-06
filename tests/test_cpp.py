from karst.cpp import *
from karst.basic import *


def test_fifo_codegen():
    fifo = define_fifo()
    fifo.configure(memory_size=128, capacity=64)

    codegen = CppCodeGen(fifo)
    tester = CPPTester(codegen)
    tester.test()


def test_sram_codegen():
    sram = define_sram()
    sram.configure(memory_size=128)

    codegen = CppCodeGen(sram)
    tester = CPPTester(codegen)
    tester.test()


def test_lb_codegen():
    lb = define_line_buffer()
    lb.configure(memory_size=128, num_rows=2, depth=64)

    codegen = CppCodeGen(lb)
    tester = CPPTester(codegen)
    tester.test()
