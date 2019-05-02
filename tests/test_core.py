from karst.core import *
import pytest


@pytest.fixture
def memory_core():
    core = MemoryCore(1024)
    return core


def test_row_buffer_core(memory_core):
    depth = 10
    instr = MemoryInstruction(MemoryMode.RowBuffer, {"depth": depth})
    memory_core.configure(instr)

    for i in range(depth * 2):
        inputs = {"data_in": i, "wen": 1}
        result = memory_core.eval(**inputs)
        assert result["valid"] == (i >= depth)
        if i >= depth:
            data_out = result["data_out"]
            assert data_out == i - depth

    # also test if we can directly configure the address
    data_entries = [(i, i + 42) for i in range(42)]
    instr = MemoryInstruction(MemoryMode.SRAM, data_entries=data_entries)
    memory_core.configure(instr)

    for i in range(42):
        assert memory_core._mem.read_from_mem(i) == i + 42
