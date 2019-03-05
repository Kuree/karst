from typing import Union, Dict, List
from hwtypes import Bit, BitVector
import enum
import math


@enum.unique
class PortType(enum.Enum):
    In = enum.auto()
    Out = enum.auto()


class ClockGenerator:
    def __init__(self):
        self.__circuits = []

    def get_clk(self, circuit: "Circuit"):
        clk = Port("clk", PortType.In, 1)
        self.__circuits.append(circuit)
        return clk

    def step(self):
        for circuit in self.__circuits:
            circuit.step()


CLOCK_GENERATOR = ClockGenerator()


class Port:
    def __init__(self, name: str, port_type: PortType, bit_width: int):
        assert isinstance(port_type, PortType)
        assert isinstance(name, str)
        assert isinstance(bit_width, int)
        self.type = port_type
        self.name = name
        self.bit_width = bit_width

        self.__connections: List["Port"] = []
        # default to 0
        if bit_width == 1:
            self.__value = Bit(0)
        else:
            self.__value = BitVector[bit_width](0)

    def wire(self, port: "Port"):
        assert isinstance(port, Port)
        assert self.bit_width == port.bit_width
        self.__connections.append(port)

    @property
    def value(self) -> BitVector:
        return self.__value

    @value.setter
    def value(self, v: Union[BitVector, int]):
        if isinstance(v, int):
            v = BitVector[self.bit_width](v)
        assert isinstance(v, (BitVector, Bit))
        self.__value = v
        # propagate through the connections
        for p in self.__connections:
            p.value = v


class Circuit:
    def __init__(self):
        self.__clk = CLOCK_GENERATOR.get_clk(self)

    @property
    def clk(self) -> Port:
        return self.__clk

    @clk.setter
    def clk(self, value: Union[bool, int, Bit, BitVector]):
        if isinstance(value, int):
            assert value in {0, 1}
            self.__clk.value = Bit(value)
        elif isinstance(value, bool):
            self.__clk.value = Bit(value)
        elif isinstance(value, Bit):
            self.__clk.value = value
        elif isinstance(value, BitVector):
            assert len(value) == 1
            self.__clk.value = Bit(value)
        else:
            raise ValueError(f"Unsupported value type {type(value)}")

        if self.__clk.value == 1:
            self.rise_edge()

    def step(self):
        self.clk = ~self.__clk.value

    def rise_edge(self):
        pass

    def combinational(self):
        pass


class Memory(Circuit):
    """Memory model. This is basically SRAM"""
    def __init__(self, addr_width: int, bit_width: int):
        super().__init__()
        assert isinstance(addr_width, int)
        assert isinstance(bit_width, int)
        size = 2 << addr_width
        self.__addr_width = addr_width
        self.__size = size
        self.__bit_width = bit_width

        self.__data = [BitVector[bit_width](0) for _ in range(size)]

        self.wen = Port("wen", PortType.In, bit_width)
        self.ren = Port("ren", PortType.In, bit_width)
        self.addr = Port("addr", PortType.In, addr_width)

        self.data_out = Port("data_out", PortType.Out, bit_width)
        self.data_in = Port("data_in", PortType.In, bit_width)

    @property
    def size(self):
        return self.__size

    @property
    def bit_width(self):
        return self.__bit_width

    @property
    def addr_width(self):
        return self.__addr_width

    def rise_edge(self):
        addr = self.addr.value
        data_in = self.data_in.value
        wen = self.wen.value
        ren = self.ren.value
        assert not wen & ren
        if ren:
            self.data_out.value = self.__data[addr.as_uint()]
        if wen:
            self.__data[addr.as_uint()] = data_in


class MemoryBackend(Circuit):
    """Models single port memory"""
    def __init__(self, num_ports: int, bit_width: int, mems: List[Memory]):
        super().__init__()

        assert isinstance(num_ports, int)
        assert isinstance(bit_width, int)
        self._num_ports = num_ports
        self._bit_width = bit_width

        # this is how many memory banks you have
        # making sure it has the same size
        self._mems = mems
        for i, mem in enumerate(mems):
            assert mem.bit_width == mems[0].bit_width
            assert mem.addr_width == mems[0].addr_width
        # power of two
        num_mem = len(mems)
        assert ((num_mem & (num_mem - 1)) == 0) and num_mem > 0, "power of 2"
        assert bit_width >= mems[0].bit_width

        # we already check the num of memories
        extra_addr = int(math.log2(num_mem))
        self.__addr_width = extra_addr + mems[0].addr_width
        self._extra_addr = extra_addr

        self.ports: Dict[str, Port] = {}

    @property
    def addr_width(self):
        return self.__addr_width

    def reset(self):
        pass

    def __getitem__(self, item) -> Port:
        assert isinstance(item, str)
        return self.ports[item]


class SRAM(MemoryBackend):
    """Models SRAM"""
    def __init__(self, num_ports: int, bit_width: int, mems: List[Memory]):
        super().__init__(num_ports, bit_width, mems)

        # current SRAM implementation only supports one output port
        assert num_ports == 1, "Only support 1 output port"
        # determine whether we use wide-bank implementation
        self.__is_wide_bank = bit_width != mems[0].bit_width

        self.__wen = Port("wen", PortType.In, bit_width)
        self.__ren = Port("ren", PortType.In, bit_width)
        self.__addr = Port("addr", PortType.In, self.addr_width)

        self.__data_out = Port("data_out", PortType.Out, bit_width)
        self.__data_in = Port("data_in", PortType.In, bit_width)

        for mem in self._mems:
            self.__data_in.wire(mem.data_in)

    # any properties are combination logics
    @property
    def ren(self):
        return self.__ren

    @ren.setter
    def ren(self, value):
        self.__ren.value = value
        assert not (self.__ren.value and self.__wen.value)
        self.combinational()

    @property
    def wen(self):
        return self.__wen

    @wen.setter
    def wen(self, value):
        self.__wen.value = value
        assert not (self.__ren.value and self.__wen.value)
        self.combinational()

    @property
    def addr(self):
        return self.__addr

    @addr.setter
    def addr(self, value):
        self.__addr.value = value
        self.combinational()

    def combinational(self):
        # combinational logic here
        addr = self.__addr.value
        bank = addr // self._mems[0].addr_width
        # transform this into a case statement in verilog
        for index, mem in enumerate(self._mems):
            if index == bank:
                mem.ren.value = self.__ren.value
                mem.wen.value = self.__wen.value
            else:
                mem.ren.value = 0
                mem.wen.value = 0
            mem.addr.value = \
                BitVector[mem.addr_width](((1 << mem.addr_width)
                                           - 1) & addr.as_uint())

    @property
    def data_out(self):
        bank = self.__addr.value // self._mems[0].addr_width
        for index, mem in enumerate(self._mems):
            if index == bank:
                return mem.data_out

    @property
    def data_in(self):
        return self.data_in

    @data_in.setter
    def data_in(self, value):
        self.__data_in.value = value


class FifoModel(MemoryBackend):
    """Models SRAM"""
    def __init__(self, num_ports: int, bit_width: int, mems: List[Memory]):
        super().__init__(num_ports, bit_width, mems)

        # current FIFO implementation only supports one output port
        assert num_ports == 1, "Only support 1 output port"
        # determine whether we use wide-bank implementation
        self.__is_wide_bank = bit_width != mems[0].bit_width

        self.__wen = Port("wen", PortType.In, bit_width)
        self.__ren = Port("ren", PortType.In, bit_width)
        self.__addr = Port("addr", PortType.In, self.addr_width)

        self.__data_out = Port("data_out", PortType.Out, bit_width)
        self.__data_in = Port("data_in", PortType.In, bit_width)


