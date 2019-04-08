from karst.hls import *
from karst.basic import *
import tempfile
import subprocess


def test_fifo_codegen():
    fifo = define_fifo()
    fifo.configure(memory_size=128, capacity=64)

    codegen = CppCodeGen(fifo)

    with tempfile.TemporaryDirectory() as dir_name:
        src_filename = os.path.join(dir_name, "src.cc")
        codegen.code_gen_to_file(src_filename)
        subprocess.check_call(["g++", "-c", src_filename], cwd=dir_name)


def test_sram_codegen():
    sram = define_sram()
    sram.configure(memory_size=128)

    codegen = CppCodeGen(sram)

    with tempfile.TemporaryDirectory() as dir_name:
        src_filename = os.path.join(dir_name, "src.cc")
        codegen.code_gen_to_file(src_filename)
        subprocess.check_call(["g++", "-c", src_filename], cwd=dir_name)


def test_lb_codegen():
    lb = define_line_buffer()
    lb.configure(memory_size=128, num_rows=2, depth=64)

    codegen = CppCodeGen(lb)

    with tempfile.TemporaryDirectory() as dir_name:
        src_filename = os.path.join(dir_name, "src.cc")
        codegen.code_gen_to_file(src_filename)
        subprocess.check_call(["g++", "-c", src_filename], cwd=dir_name)
