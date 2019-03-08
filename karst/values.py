from typing import Union
import enum


class Value:
    def __init__(self):
        self.value = 0

    def eval(self):
        return self.value

    # overload every operator that verilog supports
    def __eq__(self, other):
        if isinstance(other, Value):
            return self.eval() == other.eval()
        else:
            return self.eval() == other

    def __add__(self, other: Union["Value", int]):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() + v)

    def __sub__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() - v)

    def __mul__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() * v)

    def __mod__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() % v)

    def __gt__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() > v)

    def __ge__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() >= v)

    def __lt__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() < v)

    def __le__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() < v)

    def __rshift__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() >> v)

    def __lshift__(self, other):
        if isinstance(other, Value):
            v = other.eval()
        else:
            v = other
        return Const(self.eval() << v)


class Variable(Value):
    def __init__(self, name: str, bit_width: int, value: int = 0):
        super().__init__()
        self.name = name
        self.bit_width = bit_width

        self.value = value

    def __call__(self, value: Union["Value", "Const", int]):
        if isinstance(value, int):
            value = value
        else:
            value = value.eval()
        self.value = value

    def eval(self):
        return self.value


@enum.unique
class PortType(enum.Enum):
    In = enum.auto()
    Out = enum.auto()


class Port(Variable):
    def __init__(self, name: str, bit_width: int, port_type: PortType):
        super().__init__(name, bit_width)
        self.port_type = port_type


class Const(Value):
    def __init__(self, value: int):
        super().__init__()
        self.value = value