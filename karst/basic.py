from karst.model import define_memory, MemoryModel


def define_sram():
    @define_memory
    def sram():
        """Models the functional behavior of an one-output sram"""
        sram_model = MemoryModel()
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

    return sram()


def define_fifo():
    @define_memory
    def fifo(delay_threshold: int = 0):
        fifo_model = MemoryModel()
        # define ports here
        fifo_model.PortOut("data_out", 16)
        fifo_model.PortIn("data_in", 16)
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

        # configurable used to define the functional model
        fifo_model.Configurable("almost_t", 16, delay_threshold)
        fifo_model.Configurable("capacity", 16)

        @fifo_model.action(en_port_name="wen")
        def enqueue():
            fifo_model[fifo_model.write_addr] = fifo_model.data_in
            # state update
            fifo_model.write_addr = (fifo_model.write_addr + 1
                                     ) % fifo_model.memory_size

            # notice that we can make function calls here as long as it's
            # marked with model.mark
            # the function calls will be executed as normal python code
            update_state()

        @fifo_model.action(en_port_name="ren")
        def dequeue():
            fifo_model.data_out = fifo_model[fifo_model.read_addr]
            # state update
            fifo_model.read_addr = (fifo_model.read_addr +
                                    1) % fifo_model.memory_size

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
                                     (fifo_model.capacity - fifo_model.almost_t)

        return fifo_model
    return fifo()


def define_line_buffer():
    @define_memory
    def line_buffer():
        lb_model = MemoryModel()

        data_outs = []

        lb_model.PortIn("data_in", 16)
        lb_model.PortIn("wen", 1)

        # state control variables
        read_addr = lb_model.Variable("read_addr", 16, 0)
        write_addr = lb_model.Variable("write_addr", 16, 0)

        lb_model.Configurable("depth", 16)
        lb_model.Configurable("num_rows", 16)

        # @after_config will be called every time it's reconfigured
        # it's build on top of @mark
        @lb_model.after_config
        def create_data_out():
            data_outs.clear()
            for i in range(lb_model.num_rows):
                data_outs.append(lb_model.PortOut(f"data_out_{i}", 16))

        @lb_model.action(en_port_name="wen")
        def enqueue():
            lb_model[lb_model.write_addr] = lb_model.data_in
            # state update
            lb_model.write_addr = (lb_model.write_addr
                                   + 1) % lb_model.memory_size

            for idx in range(lb_model.num_rows):
                data_outs[idx] = lb_model[(lb_model.read_addr +
                                           lb_model.depth * idx)
                                          % lb_model.memory_size]

            if write_addr - read_addr > lb_model.depth * lb_model.num_rows:
                lb_model.read_addr = (lb_model.read_addr
                                      + 1) % lb_model.memory_size

            return data_outs

        @lb_model.action(en_port_name="reset")
        @lb_model.async_reset
        def reset():
            lb_model.read_addr = 0
            lb_model.write_addr = 0
            # line buffer is already ready to enqueue
            lb_model.RDY_enqueue = 1

        return lb_model
    return line_buffer()


def define_row_buffer():
    @define_memory
    def row_buffer():
        rb_model = MemoryModel()

        rb_model.PortIn("data_in", 16)
        rb_model.PortOut("data_out", 16)
        rb_model.PortOut("valid", 1)
        wen = rb_model.PortIn("wen", 1)

        # state control variables
        read_addr = rb_model.Variable("read_addr", 16, 0)
        write_addr = rb_model.Variable("write_addr", 16, 0)

        depth = rb_model.Configurable("depth", 16)
        memory_size = rb_model["memory_size"]

        @rb_model.action(en_port_name="wen")
        def enqueue():
            rb_model[rb_model.write_addr] = rb_model.data_in

            # state update
            rb_model.write_addr = (rb_model.write_addr + 1) % memory_size

            rb_model.valid = (((write_addr - read_addr +
                                memory_size) % memory_size) > depth) & wen

            if write_addr - read_addr > rb_model.depth:
                rb_model.data_out = rb_model[read_addr]
                rb_model.read_addr = (rb_model.read_addr + 1) % memory_size
            else:
                rb_model.data_out = 0

            return rb_model.data_out

        @rb_model.action(en_port_name="reset")
        @rb_model.async_reset
        def reset():
            rb_model.read_addr = 0
            rb_model.write_addr = 0
            # line buffer is already ready to enqueue
            rb_model.RDY_enqueue = 1

        return rb_model

    return row_buffer()


def define_double_buffer():
    @define_memory
    def double_buffer():
        db = MemoryModel(size=2, num_memory=2)

        read_addr = db.Variable("read_addr", 16)
        write_addr = db.Variable("write_addr", 16)

        # iter
        cin_off = db.Variable("cin_off", 16)
        x_iter = db.Variable("x_iter", 16)
        y_iter = db.Variable("y_iter", 16)
        x_off = db.Variable("x_off", 16)
        y_off = db.Variable("y_off", 16)
        cout_off = db.Variable("cout_off", 16)

        data_in = db.PortIn("data_in", 16)
        db.PortOut("data_out", 16)
        db.PortIn("ren", 1)
        db.PortIn("wen", 1)

        select = db.Variable("select", 1, 0)
        threshold = db.Configurable("threshold", 16)
        db.Configurable("ext_chin", 16)
        db.Configurable("off_x", 16)
        db.Configurable("off_y", 16)
        db.Configurable("ext_chout", 16)
        db.Configurable("ext_x", 16)
        bound_ch = db.Configurable("bound_ch", 16)
        bound_x = db.Configurable("bound_x", 16)
        stride = db.Configurable("stride", 16, 1)

        db.read_addr = cin_off + (x_iter + x_off) * bound_ch +\
            (y_iter + y_off) * bound_ch * bound_x

        @db.mark
        def switch():
            if (db.write_addr >= threshold - 1) \
                    and (db.y_iter >= threshold - 1):
                db.select = select ^ 1

        @db.action(en_port_name="ren")
        def read():
            db.data_out = db[(select, read_addr)]
            db.cin_off = db.cin_off + 1

            if db.cin_off == db.ext_chin:
                db.cin_off = 0
                db.x_off = db.x_off + 1
                if db.x_off == db.off_x:
                    db.x_off = 0
                    db.y_off = db.y_off + 1
                    if db.y_off == db.off_y:
                        db.y_off = 0
                        db.cout_off = cout_off + 1
                        if db.cout_off == db.ext_chout:
                            db.cout_off = 0
                            db.x_iter = x_iter + stride
                            if db.x_iter == db.ext_x:
                                db.x_iter = 0
                                db.y_iter = y_iter + stride
            switch()

        @db.action(en_port_name="wen")
        def write():
            db[write_addr] = data_in
            db.write_addr = (db.write_addr + 1) % db.memory_size

            switch()

        @db.action(en_port_name="reset")
        @db.async_reset
        def reset():
            db.write_addr = 0
            db.RDY_write = 1
            db.RDY_read = 1
            db.ren = 1
            db.cin_off = 0
            db.x_iter = 0
            db.y_iter = 0
            db.x_off = 0
            db.y_off = 0
            db.cout_off = 0

        # global updates
        db.RDY_write = write_addr < threshold
        db.RDY_read = y_iter < threshold

        return db
    return double_buffer()
