from karst.bluespec import *
from karst.basic import *
import tempfile
import subprocess


def test_fifo_codegen():
    fifo = define_fifo()
    fifo.configure(memory_size=128, capacity=64)

    codegen = BlueSpecCodeGen(fifo)
    codegen.code_gen()


def test_sram_codegen():
    sram = define_sram()
    sram.configure(memory_size=128)

    codegen = BlueSpecCodeGen(sram)
    codegen.code_gen()


def test_lb_codegen():
    lb = define_line_buffer()
    lb.configure(memory_size=128, num_rows=2, depth=64)

    codegen = BlueSpecCodeGen(lb)
    codegen.code_gen()
