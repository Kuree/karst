from memgen.model import *
import random


def test_sram():
    clk = Port("clk", PortType.In, 1)
    single_bank_width = 4
    bit_width = 16
    mems = []
    for i in range(2):
        mem = Memory(single_bank_width, bit_width)
        clk.wire(mem.clk)
        mems.append(mem)
    sram = SRAM(1, 16, mems, clk)
    assert sram.addr_width == single_bank_width + 1
    rand = random.Random(0)
    random_addr = set()
    for i in range(100):
        random_addr.add(rand.randrange(sram.addr_width))
    random_addr_list = list(random_addr)
    random_addr_list.sort()

    random_values = []
    for _ in range(len(random_addr_list)):
        random_values.append(random.randrange(bit_width))

    def step():
        clk.value = ~clk.value

    for i in range(len(random_addr_list)):
        # write to it
        sram.ren = 0
        sram.wen = 1
        sram.addr = random_addr_list[i]
        sram.data_in = random_values[i]

        step()
        step()

    for i in range(len(random_addr_list)):
        # read fromm it
        sram.wen = 0
        sram.ren = 1
        sram.addr = random_addr_list[i]

        step()
        assert sram.data_out.value == random_values[i]

        step()

