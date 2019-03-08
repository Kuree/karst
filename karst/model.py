import inspect
from karst.values import *


class Memory:
    def __init__(self, size: int):
        self._data = [0 for _ in range(size)]

    def __getitem__(self, item: Variable) -> "__MemoryAccess":
        assert isinstance(item, Variable)
        return self.__MemoryAccess(self, item)

    class __MemoryAccess(Value):
        def __init__(self, mem: "Memory", var: Variable):
            super().__init__()
            self.mem = mem
            self.var = var

        def eval(self):
            return self.mem._data[self.var.eval()]

        def __le__(self, other: Union[Value, int]):
            if isinstance(other, Value):
                value = other.eval()
            else:
                value = other
            self.mem._data[self.var.eval()] = value


class MemoryModel:
    def __init__(self, size: int):
        self._variables = {}
        self._ports = {}
        self._consts = {}

        self._actions = {}
        self._mem = Memory(size)

        self.ast_text = {}
        self.mem_size = size

    def define_variable(self, name: str, bit_width: int,
                        value: int = 0) -> Variable:
        if name in self._variables:
            return self._variables[name]
        var = Variable(name, bit_width, value)
        self._variables[var.name] = var
        return var

    def define_port_in(self, name: str, bit_width: int) -> Port:
        if name in self._ports:
            return self._ports[name]
        port = Port(name, bit_width, PortType.In)
        self._ports[name] = port
        return port

    def define_port_out(self, name: str, bit_width: int) -> Port:
        if name in self._ports:
            return self._ports[name]
        port = Port(name, bit_width, PortType.Out)
        self._ports[name] = port
        return port

    def define_const(self, name: str, value: int):
        if name in self._consts:
            return self._consts[name]
        const = Const(value)
        self._consts[name] = const
        return const

    def action(self, name: str):
        return self._Action(name, self)

    def __getitem__(self, item):
        return self._mem[item]

    def __getattr__(self, item: str) -> Union[Variable]:
        if item in self._actions:
            return self._actions[item]
        elif item in self._ports:
            return self._ports[item]
        elif item in self._variables:
            return self._variables[item]
        elif item in self._consts:
            return self._consts[item]
        else:
            return object.__getattribute__(self, item)

    def _get_variable_read_mem(self):
        pass

    def expect(self, _):
        # TODO parse the expression and set the expected values
        pass

    class _Action:
        def __init__(self, name: str, model: "MemoryModel"):
            self.name = name
            self.model = model

        def __call__(self, f):
            def wrapper():
                f()
            self.model._actions[self.name] = wrapper
            # perform AST analysis to in order to lower it to RTL
            txt = inspect.getsource(f)
            self.model.ast_text[self.name] = txt
            return wrapper

    # alias
    Variable = define_variable
    PortIn = define_port_in
    PortOut = define_port_out
    Constant = define_const


def define_sram(size: int):
    """Models the functional behavior of an one-output sram"""
    sram_model = MemoryModel(size)
    # define ports here
    ren = sram_model.PortIn("ren", 1)
    data_out = sram_model.PortOut("data_out", 16)
    addr = sram_model.PortIn("addr", 16)
    wen = sram_model.PortIn("wen", 1)
    data_in = sram_model.PortIn("data_in", 16)

    @sram_model.action("read")
    def read():
        # specify action conditions
        sram_model.expect(ren == 1)
        sram_model.expect(wen == 0)
        data_out(sram_model[addr])

    @sram_model.action("write")
    def write():
        # specify action conditions
        sram_model.expect(ren == 0)
        sram_model.expect(wen == 1)
        sram_model[addr] <= data_in

    return sram_model


def define_fifo(size: int):
    fifo_model = MemoryModel(size)
    # define ports here
    ren = fifo_model.PortIn("ren", 1)
    data_out = fifo_model.PortOut("data_out", 16)
    wen = fifo_model.PortIn("wen", 1)
    data_in = fifo_model.PortIn("data_in", 16)
    almost_empty = fifo_model.PortOut("almost_empty", 1)
    almost_full = fifo_model.PortOut("almost_full", 1)

    # state control variables
    read_addr = fifo_model.Variable("read_addr", 16, 0)
    write_addr = fifo_model.Variable("write_addr", 16, 0)
    word_count = fifo_model.Variable("word_count", 16, 0)

    mem_size = fifo_model.Constant("mem_size", size)

    @fifo_model.action("enqueue")
    def enqueue():
        fifo_model.expect(wen == 1)
        fifo_model.expect(word_count < mem_size)
        fifo_model[write_addr] <= data_in
        # state update
        write_addr((write_addr + 1) % mem_size)
        word_count((word_count + 1) % mem_size)

        # set the control flag. this will also test ast parsing
        if word_count > mem_size - 3:
            almost_full(1)
        else:
            almost_full(0)

    @fifo_model.action("dequeue")
    def dequeue():
        fifo_model.expect(ren == 1)
        fifo_model.expect(word_count > 0)
        data_out(fifo_model[read_addr])
        # state update
        read_addr(read_addr + 1)

        if word_count < 3:
            almost_empty(1)
        else:
            almost_empty(0)

    @fifo_model.action("evaluate")
    def evaluate():
        # update state that can be changed in other actions
        # this is just to make RTL generation easier
        if ren == 1 and wen == 0:
            word_count(word_count - 1)
        elif ren == 0 and wen + 1:
            word_count(word_count + 1)

    return fifo_model


def define_line_buffer(depth):
    lb_model = MemoryModel(depth)
    data_out = lb_model.PortOut("data_out", 16)
    wen = lb_model.PortIn("wen", 1)
    data_in = lb_model.PortIn("data_in", 16)
    valid = lb_model.PortOut("valid", 1)
    # state control variables
    read_addr = lb_model.Variable("read_addr", 16, 0)
    write_addr = lb_model.Variable("write_addr", 16, 0)
    word_count = lb_model.Variable("word_count", 16, 0)

    depth = lb_model.Constant("depth", depth)

    @lb_model.action("enqueue")
    def enqueue():
        lb_model.expect(wen == 1)
        lb_model[write_addr] <= data_in
        # state update
        write_addr((write_addr + 1) % depth)

    @lb_model.action("dequeue")
    def dequeue():
        lb_model.expect(valid == 1)
        lb_model.expect(word_count > 0)
        data_out(lb_model[read_addr])

    @lb_model.action("evaluate")
    def evaluate():
        if word_count >= depth and wen:
            valid(1)
        elif word_count < depth:
            word_count(word_count + 1)
        else:
            # not wen
            valid(0)
            word_count(word_count - 1)
