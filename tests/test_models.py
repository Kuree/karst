from karst.basic import define_sram, define_fifo, define_line_buffer, \
    define_row_buffer
from karst.model import MemoryModel, define_memory


def test_sram():
    sram = define_sram()
    sram.configure(memory_size=64)
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
    fifo = define_fifo()
    fifo.configure(memory_size=64, capacity=fifo_depth)
    fifo.reset()
    # try to dequeue an empty queue
    assert fifo.RDY_dequeue == 0
    fifo.dequeue()
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
    lb = define_line_buffer()
    lb.configure(memory_size=64, num_rows=2, depth=2)
    lb.reset()
    lb.data_in = 42
    lb.enqueue()
    lb.data_in = 43
    lb.enqueue()
    lb.data_in = 44
    lb.enqueue()
    lb.data_in = 45
    lb.enqueue()
    lb.data_in = 46
    outs = lb.enqueue()
    assert outs[0] == 42 and outs[1] == 44
    lb.data_in = 47
    outs = lb.enqueue()
    assert outs[0] == 43 and outs[1] == 45


def test_row_buffer():
    rb = define_row_buffer()
    rb.configure(memory_size=64, depth=4)
    # enable the wen
    rb.wen = 1
    rb.data_in = 42
    rb.enqueue()
    rb.data_in = 43
    rb.enqueue()
    rb.data_in = 44
    assert rb.valid == 0
    rb.enqueue()
    rb.data_in = 45
    rb.enqueue()
    assert rb.valid == 0
    rb.data_in = 46
    data_out = rb.enqueue()
    assert data_out == 42
    assert rb.valid == 1


def test_generic_memory():
    # just to test the interface
    @define_memory
    def define_mem():
        mem = MemoryModel(8)
        a = mem.Variable("a", 2, 0)
        mem.Constant("b", 1)
        a_ = mem.Variable("a", 2, 0)
        mem.Variable("c", 16, 0)
        assert a == a_

        @mem.action(en_port_name="en", rdy_port_name="rdy")
        def test():
            mem.a = 1

        @mem.global_func
        def global_test():
            mem.c = 42

        return mem

    model = define_mem()
    assert model.c == 0
    model.test()
    assert model.a == 1
    assert model.b == 1
    assert model.c == 42
    assert model["b"] == 1
    model["a"] = 2
    assert model.a == 2
    model[model.a] = 4
    assert model[model.a] == 4
    assert model.get_action_names() == ["test"]

    assert model.model_name == "mem"


def test_model_debug():
    mem = MemoryModel(8)
    mem.write_to_mem(2, 42)
    assert mem.read_from_mem(2) == 42
    assert mem.read_from_mem(3) == 0


def test_two_bank():
    # just to test the interface
    @define_memory
    def define_two_bank():
        model = MemoryModel(8, 2)
        select = model.PortIn("select", 1)
        read_addr = model.PortIn("read_addr", 3)
        write_addr = model.PortIn("write_addr", 3)
        data_in = model.PortIn("data_in", 16)
        model.PortOut("data_out", 16)

        @model.action()
        def read():
            model.data_out = model[(select, read_addr)]
            return model.data_out

        @model.action()
        def write():
            model[(select, write_addr)] = data_in

        return model

    mem = define_two_bank()

    mem.write_to_mem(2, 42, 0)
    mem.write_to_mem(3, 43, 1)

    mem.RDY_read = 1
    mem.read_addr = 2
    val = mem.read()
    assert val == 42
    mem.read_addr = 3
    mem.select = 1
    val = mem.read()
    assert val == 43

    # write
    mem.RDY_write = 1
    mem.write_addr = 2
    mem.data_in = 100
    mem.select = 0
    mem.write()
    assert mem.read_from_mem(2, 0) == 100
