from karst.model import *


def test_sram():
    sram = define_sram(100)
    # inputs
    sram.data_in(42)
    sram.addr(24)
    # action
    sram.write()
    # action
    out = sram.read()
    assert out == 42


def test_fifo():
    fifo = define_fifo(100)
    fifo.data_in(42)
    fifo.enqueue()
    out = fifo.dequeue()
    fifo.update()
    assert out == 42
    assert fifo.almost_empty == 1