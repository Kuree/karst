from memgen.model import *
import pytest
import random


@pytest.mark.parametrize("addr_width", [4, 8])
@pytest.mark.parametrize("bit_width", [16])
def test_random_write_read(addr_width, bit_width):
    memory = Memory(addr_width, bit_width)
    rand = random.Random(0)
    batch_size = 1 << addr_width
    values = []
    for addr in range(batch_size):
        memory.ren.value = 0
        memory.wen.value = 1
        memory.addr.value = addr
        value = rand.randrange(1 << bit_width)
        values.append(value)
        memory.data_in.value = value
        memory.step()
        memory.step()

    # read out
    for addr in range(batch_size):
        memory.ren.value = 1
        memory.wen.value = 0
        memory.addr.value = addr
        memory.step()

        assert memory.data_out.value == values[addr]
        memory.step()
