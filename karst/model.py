import inspect
from karst.stmt import *
from typing import Callable


class Memory:
    def __init__(self, size: int, parent):
        self._data = [0 for _ in range(size)]
        self.parent = parent

    def __getitem__(self, item: Value) -> "MemoryAccess":
        assert isinstance(item, Value)
        return self.MemoryAccess(self, item, self.parent)

    @enum.unique
    class MemoryAccessType(enum.Enum):
        Read = enum.auto()
        Write = enum.auto()

    class MemoryAccess(Value):
        def __init__(self, mem: "Memory", var: Value, parent):
            super().__init__(f"mem_{var.name}")
            self.mem = mem
            self.var = var

            self.parent = parent

        def eval(self):
            v = self.var.eval()
            return self.mem._data[v]

        def __call__(self, other: Union[Value, int]):
            if isinstance(other, Value):
                value = other.eval()
            else:
                value = other
            index = self.var.eval()
            self.mem._data[index] = value
            return AssignStatement(self, other, self.parent)

        def __repr__(self):
            return f"memory[{self.var.name}]"

        def copy(self):
            return Memory.MemoryAccess(self.mem, self.var, self.parent)

        def eq(self, other: "Value"):
            return isinstance(other, Memory.MemoryAccess) and\
                   self.mem == other.mem and self.var == other.var


class MemoryModel:
    def __init__(self, size: int):
        self._initialized = False
        self._variables = {}
        self._ports = {}
        self._consts = {}

        self._actions = {}
        self._conditions = {}
        self._mem = Memory(size, self)
        self.mem_size = size

        self.ast_text = {}

        self._stmts = {}

        self.context = []

        self._initialized = True

    def set_mem_size(self, size: int):
        self._mem = Memory(size, self)
        self.mem_size = size

    def define_variable(self, name: str, bit_width: int,
                        value: int = 0) -> Variable:
        if name in self._variables:
            return self._variables[name]
        var = Variable(name, bit_width, self, value)
        self._variables[var.name] = var
        return var

    def define_port_in(self, name: str, bit_width: int) -> Port:
        if name in self._ports:
            return self._ports[name]
        port = Port(name, bit_width, PortType.In, self)
        self._ports[name] = port
        return port

    def define_port_out(self, name: str, bit_width: int,
                        value: int = 0) -> Port:
        if name in self._ports:
            return self._ports[name]
        port = Port(name, bit_width, PortType.Out, self)
        port.value = value
        self._ports[name] = port
        return port

    def define_const(self, name: str, value: Union[int, Variable]):
        if name in self._consts:
            return self._consts[name]
        const = Const(value)
        self._consts[name] = const
        return const

    def action(self, name: str, default_rdy_value: int = 0):
        # create ready-valid signals based on the function name
        self.Variable(f"EN_{name}", 1)
        self.Variable(f"RDY_{name}", 1, default_rdy_value)
        return self._Action(name, self)

    def __getitem__(self, item):
        if isinstance(item, Value):
            return self._mem[item]
        else:
            assert isinstance(item, str)
            return getattr(self, item)

    def __setitem__(self, key, value):
        if isinstance(key, Value):
            self._mem[key](value)
        else:
            return setattr(self, key, value)

    def __getattr__(self, item: str) -> Union[Variable]:
        if item in self._actions:
            return self.__eval_stmts(item)
        elif item in self._ports:
            return self._ports[item]
        elif item in self._variables:
            return self._variables[item]
        elif item in self._consts:
            return self._consts[item]
        else:
            return object.__getattribute__(self, item)

    def __setattr__(self, key, value):
        if key == "_initialized":
            self.__dict__[key] = value
        elif not self._initialized:
            self.__dict__[key] = value
        elif key in self.__dict__:
            self.__dict__[key] = value
        else:
            variable = self._ports[key] if key in self._ports else \
                self._variables[key]
            variable(value)

    def define_if(self, predicate: Union[Expression, bool], expr: Expression):
        if_ = If(self)
        return if_(predicate, expr)

    def define_return(self, value: Union[List[Value], Value]):
        return_ = ReturnStatement(value, self)
        return return_

    class _Action:
        def __init__(self, name: str, model: "MemoryModel"):
            self.name = name
            self.model = model

        def __call__(self, f):

            def wrapper():
                # we need to record every expressions here
                # TODO: fix this hack
                self.model.context.clear()
                v = f()
                # copy to the statement
                if v is not None:
                    self.model.Return(v)
                self.model._stmts[self.name] = self.model.context[:]
                return v
            self.model._actions[self.name] = wrapper
            # perform AST analysis to in order to lower it to RTL
            txt = inspect.getsource(f)
            self.model.ast_text[self.name] = txt
            return wrapper

    def get_action_names(self):
        return list(self._actions.keys())

    def produce_statements(self):
        for name, action in self._actions.items():
            if name not in self._stmts:
                # generate expressions
                action()
        return self._stmts

    def __eval_stmts(self, action_name: str):
        def wrapper():
            if action_name not in self._stmts:
                self.produce_statements()
            # use READY signal here
            # only execute the statement if it's valid
            ready_signal = self[f"RDY_{action_name}"]
            stmts = self._stmts[action_name]
            if ready_signal.eval() != 1:
                # latch out the return values
                for stmt in stmts:
                    if isinstance(stmt, ReturnStatement):
                        v = stmt.eval()
                        if len(v) == 1:
                            return v[0]
                        else:
                            return v
                return
            for stmt in stmts:
                v = stmt.eval()
                if isinstance(stmt, ReturnStatement):
                    if len(v) == 1:
                        return v[0]
                    else:
                        return v
        return wrapper

    # alias
    Variable = define_variable
    PortIn = define_port_in
    PortOut = define_port_out
    Constant = define_const
    If = define_if
    Return = define_return

    # decorator to wrap around the define function. this is need to allow
    # ast rewrite that respects to the scope
    @staticmethod
    def define(func: Callable[["MemoryModel"], None]):
        model = MemoryModel(0)
        func(model)

        class _Wrapper:
            def __call__(self):
                return model
        return _Wrapper()

