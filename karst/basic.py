from karst.model import define_memory, MemoryModel


def define_sram(size_):
    @define_memory
    def sram(size: int):
        """Models the functional behavior of an one-output sram"""
        sram_model = MemoryModel(size)
        # define ports here
        sram_model.PortIn("ren", 1)
        sram_model.PortOut("data_out", 16)
        sram_model.PortIn("addr", 16)
        sram_model.PortIn("wen", 1)
        sram_model.PortIn("data_in", 16)

        # declare the interface for read action. we create a port
        # aliasing here to alias EN_read with ren
        @sram_model.action(en_port_name="ren")
        def read():
            sram_model.data_out = sram_model[sram_model.addr]
            return sram_model.data_out

        @sram_model.action(en_port_name="wen")
        def write():
            sram_model[sram_model.addr] = sram_model.data_in

        @sram_model.action()
        @sram_model.async_reset
        def reset():
            sram_model.RDY_read = 1
            sram_model.RDY_write = 1

        return sram_model

    return sram(size_)


def define_fifo(size_):
    @define_memory
    def fifo(size, delay_threshold: int = 0):
        fifo_model = MemoryModel(size)
        # define ports here
        fifo_model.PortOut("data_out", 16)
        fifo_model.PortIn("data_in", 16)
        fifo_model.PortIn("reset", 1)
        fifo_model.PortOut("almost_empty", 1)
        fifo_model.PortOut("almost_full", 1)

        # state control variables
        read_addr = fifo_model.Variable("read_addr", 16, 0)
        write_addr = fifo_model.Variable("write_addr", 16, 0)

        # ready port name
        fifo_model.Variable("RDY_enqueue", 1)
        fifo_model.Variable("RDY_dequeue", 1)

        # convert the virtual ports to the ports that we care about
        # we invert the values here
        fifo_model.almost_full = fifo_model.RDY_enqueue ^ 1
        fifo_model.almost_empty = fifo_model.RDY_dequeue ^ 1

        # some other constants
        fifo_model.Constant("almost_t", delay_threshold)

        @fifo_model.action()
        def enqueue():
            fifo_model[fifo_model.write_addr] = fifo_model.data_in
            # state update
            fifo_model.write_addr = (fifo_model.write_addr + 1) % size

            # notice that we can make function calls here as long as it's
            # marked with model.mark
            # the function calls will be executed as normal python code
            update_state()

        @fifo_model.action()
        def dequeue():
            fifo_model.data_out = fifo_model[fifo_model.read_addr]
            # state update
            fifo_model.read_addr = (fifo_model.read_addr + 1) % size

            update_state()

            return fifo_model.data_out

        @fifo_model.action(en_port_name="reset")
        @fifo_model.async_reset
        def reset():
            fifo_model.read_addr = 0
            fifo_model.write_addr = 0
            fifo_model.RDY_dequeue = 0
            fifo_model.RDY_enqueue = 1

        @fifo_model.mark
        def update_state():
            fifo_model.RDY_dequeue = (write_addr - read_addr) > \
                                     fifo_model.almost_t
            fifo_model.RDY_enqueue = (write_addr - read_addr) < \
                                     (size - fifo_model.almost_t)

        return fifo_model
    return fifo(size_)


def define_line_buffer(depth_, rows_):
    @define_memory
    def line_buffer(depth: int, rows: int, mem_size: int = 0):
        if mem_size == 0:
            # get the minimal size
            mem_size = 1 << (depth * rows-1).bit_length()
        lb_model = MemoryModel(mem_size)

        data_outs = []
        for i in range(rows):
            data_outs.append(lb_model.PortOut(f"data_out_{i}", 16))

        lb_model.PortIn("data_in", 16)
        lb_model.PortIn("wen", 1)
        lb_model.PortIn("reset", 1)

        # state control variables
        read_addr = lb_model.Variable("read_addr", 16, 0)
        write_addr = lb_model.Variable("write_addr", 16, 0)

        lb_model.Constant("depth", depth)
        lb_model.Constant("num_row", rows)

        @lb_model.action(en_port_name="en")
        def enqueue():
            lb_model[lb_model.write_addr] = lb_model.data_in
            # state update
            lb_model.write_addr = (lb_model.write_addr + 1) % mem_size

            for idx in range(rows):
                data_outs[idx](lb_model[(lb_model.read_addr + depth * idx)
                                        % mem_size])

            if write_addr - read_addr > mem_size:
                lb_model.read_addr = (lb_model.read_addr + 1) % mem_size

            return data_outs

        @lb_model.action(en_port_name="reset")
        @lb_model.async_reset
        def reset():
            lb_model.read_addr = 0
            lb_model.write_addr = 0
            # line buffer is already ready to enqueue
            lb_model.RDY_enqueue = 1

        return lb_model
    return line_buffer(depth_, rows_)
