from typing import Union, List
import enum
import operator
import abc


class Statement:
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.parent.context.append(self)

    @abc.abstractmethod
    def eval(self):
        pass

    @abc.abstractmethod
    def eq(self, other: "Statement"):
        pass


class Value:
    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    def eval(self):
        pass

    @abc.abstractmethod
    def copy(self):
        pass

    @abc.abstractmethod
    def eq(self, other: "Value"):
        pass

    # overload every operator that verilog supports
    def __eq__(self, other):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.eq)

    def __add__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.add)

    def __radd__(self, other: Union["Value", int]):
        return self + other

    def __sub__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.sub)

    def __rsub__(self, other):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(value, self, operator.sub)

    def __mul__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.mul)

    def __mod__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.mod)

    def __rmod__(self, other: int):
        value = Const(other)
        return Expression(value, self, operator.mod)

    def __gt__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.gt)

    def __ge__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.ge)

    def __lt__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.lt)

    def __le__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.le)

    def __rshift__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.rshift)

    def __lshift__(self, other: Union["Value", int]):
        if not isinstance(other, Value):
            assert isinstance(other, int)
            value = Const(other)
        else:
            value = other
        return Expression(self, value, operator.lshift)


class AssignStatement(Statement):
    def __init__(self, left: "Variable", right: Value, parent):
        super().__init__(parent)
        self.left = left
        self.right = right

    def __repr__(self):
        return f"{self.left} = {self.right}"

    def eval(self):
        # we update the parent values
        return self.left(self.right)

    def eq(self, other: "Statement"):
        if not isinstance(other, AssignStatement):
            return False
        if isinstance(self.right, int):
            return self.left.eq(other.left) and self.right == other.right
        else:
            return self.left.eq(other.left) and self.right.eq(other.right)


class Variable(Value):
    def __init__(self, name: str, bit_width: int, parent, value: int = 0):
        super().__init__(name)
        self.name = name
        self.bit_width = bit_width

        self.value = value
        self.parent = parent

    def __call__(self, value: Union["Value", "Const", int]):
        if isinstance(value, Value):
            self.value = value.eval()
        else:
            self.value = value
        # assignment is a statement
        return AssignStatement(self, value, self.parent)

    def eval(self):
        if isinstance(self.value, int):
            return self.value
        else:
            assert isinstance(self.value, Value)
            return self.value.eval()

    def __repr__(self):
        return self.name

    def copy(self):
        return self

    def eq(self, other: Value):
        if not isinstance(other, Variable):
            return False
        return self.name == other.name

    def __hash__(self):
        return self.name.__hash__()


@enum.unique
class PortType(enum.Enum):
    In = enum.auto()
    Out = enum.auto()


class Port(Variable):
    def __init__(self, name: str, bit_width: int, port_type: PortType, parent):
        super().__init__(name, bit_width, parent)
        self.port_type = port_type

    def __repr__(self):
        return self.name


class Const(Value):
    def __init__(self, value: int):
        if isinstance(value, Value):
            value = value.eval()
        super().__init__(f"const_{value}")
        self.value = value

    def eval(self):
        return self.value

    def __repr__(self):
        return str(self.value)

    def copy(self):
        return Const(self.value)

    def __int__(self):
        return self.value

    def eq(self, other: "Value"):
        if not isinstance(other, Const):
            return False
        return other.value == self.value


class Expression(Value):
    __counter = 0

    def __init__(self, left: Value, right: Value, op):
        super().__init__(f"exp_{Expression.__counter}")
        Expression.__counter += 1
        self.left = left
        self.right = right
        self.op = op

    def eval(self):
        left = self.left.eval()
        right = self.right.eval()
        v = self.op(left, right)
        while not isinstance(v, int):
            v = v.eval()
        return v

    def __bool__(self):
        v = self.eval()
        assert isinstance(v, int)
        return bool(v)

    def __repr__(self):
        return f"({self.left} {self.op.__name__} {self.right})"

    def copy(self):
        return Expression(self.left.copy(), self.right.copy(), self.op)

    def eq(self, other: "Expression"):
        if not isinstance(other, Expression):
            return False
        left = self.left.eq(other.left)
        right = self.right.eq(other.right)
        op = self.op == other.op
        return left and right and op
