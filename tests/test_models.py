from karst.basic import define_sram, define_fifo, define_line_buffer
from karst.model import MemoryModel, define_memory


def test_sram():
    sram = define_sram(64)
    sram.reset()
    # inputs
    sram.data_in = 42
    sram.addr = 24
    # action
    sram.write()
    # action
    out = sram.read()
    assert out == 42


def test_fifo():
    fifo_depth = 8
    fifo = define_fifo(fifo_depth)
    fifo.reset()
    # try to dequeue an empty queue
    fifo.dequeue()
    assert fifo.RDY_dequeue == 0
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
    # the queue is empty now
    # assert control signals
    # latch out the data
    assert fifo.dequeue() == 45

    # make it full
    for i in range(fifo_depth):
        fifo.enqueue()
    # nothing happens
    fifo.enqueue()


def test_line_buffer():
    lb = define_line_buffer(2, 2)
    lb.reset()
    lb.data_in = 42
    lb.enqueue()
    lb.data_in = 43
    lb.enqueue()
    lb.data_in = 44
    lb.enqueue()
    lb.data_in = 45
    outs = lb.enqueue()
    assert outs[0] == 42 and outs[1] == 44


def test_generic_memory():
    # just to test the interface
    @define_memory
    def define_mem():
        mem = MemoryModel(1)
        mem.Variable("a", 1, 0)

        @mem.action(en_port_name="en", rdy_port_name="rdy")
        def test():
            mem.a = 1

        return mem

    model = define_mem()
    model.test()
    assert model.a == 1
