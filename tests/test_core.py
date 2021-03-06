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


def test_bitstream(memory_core):
    capacity = 128
    instr = MemoryInstruction(MemoryMode.FIFO, {"capacity": capacity})
    bitstream = memory_core.get_bitstream(instr)
    assert len(bitstream) == 2
    ins1, ins2 = bitstream
    assert ins1[0] == 0 and ins1[1] == MemoryMode.FIFO.value
    assert ins2[0] == 2 and ins2[1] == capacity
