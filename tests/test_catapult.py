from karst.catapult import *
from karst.basic import *


def test_fifo_codegen():
    fifo = define_fifo()
    fifo.configure(memory_size=128, capacity=64)

    codegen = CatapultCodeGen(fifo)
    codegen.code_gen()
    tester = CatapultTester(codegen)
    tester.test()


def test_sram_codegen():
    sram = define_sram()
    sram.configure(memory_size=128)

    codegen = CatapultCodeGen(sram)
    s = codegen.code_gen()
    tester = CatapultTester(codegen)
    tester.test()


def test_lb_codegen():
    lb = define_line_buffer()
    lb.configure(memory_size=128, num_rows=2, depth=64)

    codegen = CatapultCodeGen(lb)
    codegen.code_gen()
    tester = CatapultTester(codegen)
    tester.test()
