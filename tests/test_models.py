from karst.basic import define_sram, define_fifo, define_line_buffer


def test_sram():
    sram = define_sram(100)
    # inputs
    sram.data_in = 42
    sram.addr = 24
    # action
    sram.write()
    # action
    out = sram.read()
    assert out == 42


def test_fifo():
    fifo = define_fifo(100)
    fifo.clear()
    fifo.data_in = 42
    fifo.enqueue()
    out = fifo.dequeue()
    assert out == 42
    assert fifo.almost_empty == 1
    fifo.data_in = 43
    fifo.enqueue()
    fifo.data_in = 44
    fifo.enqueue()
    fifo.data_in = 45
    fifo.enqueue()
    assert fifo.almost_empty == 0
    assert fifo.dequeue() == 43
    assert fifo.dequeue() == 44
    assert fifo.dequeue() == 45
    assert fifo.RDY_dequeue == 0
    # latch out the data
    assert fifo.dequeue() == 45


def test_line_buffer():
    lb = define_line_buffer(2, 2)
    lb.clear()
    lb.data_in = 42
    lb.enqueue()
    lb.data_in = 43
    lb.enqueue()
    # not ready
    assert lb.RDY_dequeue == 0
    # this dequeue should matter
    outs = lb.dequeue()
    # it should latch the zero result
    assert outs[0] == 0 and outs[1] == 0
    lb.data_in = 44
    lb.enqueue()
    lb.data_in = 45
    lb.enqueue()
    assert lb.RDY_dequeue == 1
    outs = lb.dequeue()
    assert outs[0] == 42 and outs[1] == 44
