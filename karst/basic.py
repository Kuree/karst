from karst.model import define_memory, MemoryModel


def define_sram(*args, **kwargs):
    @define_memory
    def sram(size: int):
        """Models the functional behavior of an one-output sram"""
        sram_model = MemoryModel(size)
        # define ports here
        sram_model.PortIn("ren", 1)
        sram_model.PortOut("data_out", 16)
        addr = sram_model.PortIn("addr", 16)
        sram_model.PortIn("wen", 1)
        sram_model.PortIn("data_in", 16)

        @sram_model.action("read", 1)
        def read():
            sram_model.data_out = sram_model[sram_model.addr]
            return sram_model.data_out

        @sram_model.action("write", 1)
        def write():
            sram_model[addr] = sram_model.data_in

        return sram_model

    return sram(*args, **kwargs)


def define_fifo(*args, **kwargs):
    @define_memory
    def fifo(size):
        fifo_model = MemoryModel(size)
        # define ports here
        fifo_model.PortOut("data_out", 16)
        fifo_model.PortIn("wen", 1)
        fifo_model.PortIn("data_in", 16)
        fifo_model.PortOut("almost_empty", 1, 1)
        fifo_model.PortOut("almost_full", 1)

        # state control variables
        fifo_model.Variable("read_addr", 16, 0)
        fifo_model.Variable("write_addr", 16, 0)
        fifo_model.Variable("word_count", 16, 0)

        # some other constants
        fifo_model.Constant("almost_t", 3)

        mem_size = size

        @fifo_model.action("enqueue", 1)
        def enqueue():
            fifo_model[fifo_model.write_addr] = fifo_model.data_in
            # state update
            fifo_model.write_addr = (fifo_model.write_addr + 1) % mem_size
            fifo_model.word_count = fifo_model.word_count + 1

            # notice that we can make function calls here as long as it's not
            # annotated in action()
            # the function calls will be executed as normal python code, same
            # as if statement
            update_state()

        @fifo_model.action("dequeue")
        def dequeue():
            fifo_model.data_out = fifo_model[fifo_model.read_addr]
            # state update
            fifo_model.read_addr = fifo_model.read_addr + 1
            fifo_model.word_count = (fifo_model.word_count - 1) % mem_size

            update_state()

            return fifo_model.data_out

        @fifo_model.action("clear", 1)
        def clear():
            fifo_model.read_addr = 0
            fifo_model.write_addr = 0
            fifo_model.word_count = 0
            fifo_model.almost_empty = 1
            fifo_model.almost_full = 0

            fifo_model.RDY_enqueue = 1

        @fifo_model.mark
        def update_state():
            # There is an astor bug that prevent long if statements
            # being converted
            if fifo_model.word_count < fifo_model.almost_t:
                fifo_model.almost_empty = 1
            else:
                fifo_model.almost_empty = 0

            if fifo_model.word_count > (mem_size - fifo_model.almost_t):
                fifo_model.almost_full = 1
            else:
                fifo_model.almost_full = 0

            if fifo_model.word_count < mem_size:
                fifo_model.RDY_enqueue = 1
            else:
                fifo_model.RDY_enqueue = 0

            if fifo_model.word_count > 0:
                fifo_model.RDY_dequeue = 1
            else:
                fifo_model.RDY_dequeue = 0

        return fifo_model
    return fifo(*args, **kwargs)


def define_line_buffer(*args, **kwargs):
    @define_memory
    def line_buffer(depth: int, rows: int):
        lb_model = MemoryModel(depth * rows)
        data_outs = []
        for i in range(rows):
            data_outs.append(lb_model.PortOut(f"data_out_{i}", 16))
        lb_model.PortIn("data_in", 16)
        # state control variables
        lb_model.Variable("read_addr", 16, 0)
        lb_model.Variable("write_addr", 16, 0)
        lb_model.Variable("word_count", 16, 0)

        lb_model.Constant("depth", depth)
        lb_model.Constant("num_row", rows)
        buffer_size = depth * rows

        @lb_model.action("enqueue", 1)
        def enqueue():
            lb_model[lb_model.write_addr] = lb_model.data_in
            # state update
            lb_model.write_addr = (lb_model.write_addr + 1) % buffer_size

            for idx in range(rows):
                data_outs[idx](lb_model[(lb_model.read_addr + depth * idx)
                                        % buffer_size])

            if lb_model.word_count >= buffer_size - 1:
                lb_model.read_addr = (lb_model.read_addr + 1) % buffer_size

            if lb_model.word_count < buffer_size:
                lb_model.word_count = lb_model.word_count + 1

            return data_outs

        @lb_model.action("clear", 1)
        def clear():
            lb_model.read_addr = 0
            lb_model.write_addr = 0
            lb_model.word_count = 0
            # line buffer is already ready to enqueue
            lb_model.RDY_enqueue = 1

        return lb_model
    return line_buffer(*args, **kwargs)
