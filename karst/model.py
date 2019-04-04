import inspect
from karst.stmt import *
from typing import Callable
from karst.ast_codegen import *
import astor
import textwrap


class Memory:
    def __init__(self, size: int, parent):
        assert size != 0 and ((size & (size - 1)) == 0), \
            f"{size} has to be 2's power"
        self._data = [0 for _ in range(size)]
        self.parent = parent

    def __getitem__(self, item: Value) -> "MemoryAccess":
        assert isinstance(item, Value)
        return self.MemoryAccess(self, item, self.parent)

    def resize(self, new_size: int):
        assert new_size != 0 and ((new_size & (new_size - 1)) == 0),\
            f"{new_size} has to be 2's power"
        self._data = [0 for _ in range(new_size)]

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
    MEMORY_SIZE = "memory_size"

    def __init__(self, size: int = 1):
        self._initialized = False
        self._variables = {}
        self._ports = {}
        self._consts = {}
        self._config_vars = {}

        self._preprocess = {}

        self._actions = {}
        self._conditions = {}
        self._mem = Memory(size, self)

        self._stmts = {}
        self._global_stmts = []

        self.context = []

        # add configurable memory_size for all memory models
        self._config_vars[self.MEMORY_SIZE] = Configurable(self.MEMORY_SIZE,
                                                           16, self, size)
        # config variables used to generate hardware
        self._loop_vars = set()

        self._initialized = True

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

    def define_config(self, name: str, bit_width: int,
                      value: int = 0) -> Configurable:
        assert name != self.MEMORY_SIZE, f"{self.MEMORY_SIZE} is reserved"
        if name in self._config_vars:
            return self._config_vars[name]
        config = Configurable(name, bit_width, self, value)
        self._config_vars[name] = config
        return config

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            if key == self.MEMORY_SIZE:
                self._mem.resize(value)
            self._config_vars[key].value = value

        for _, func in self._preprocess.items():
            func()

    def add_loop_var(self, *args: str):
        for var_name in args:
            if var_name in self._config_vars:
                self._loop_vars.add(self[var_name])

    def action(self, en_port_name: str = "", rdy_port_name: str = ""):
        if self.context:
            self._global_stmts += self.context
            self.context.clear()
        return self._Action(self, en_port_name, rdy_port_name)

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
        elif item in self._config_vars:
            return self._config_vars[item]
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
            if key in self._ports:
                variable = self._ports[key]
            elif key in self._variables:
                variable = self._variables[key]
            else:
                variable = self._config_vars[key]
            variable(value)

    def __contains__(self, item):
        return item in self._variables or item in self._ports or \
               item in self._config_vars

    def define_if(self, predicate: Union[Expression, bool], expr: Expression):
        if_ = If(self)
        return if_(predicate, expr)

    def define_return(self, value: Union[List[Value], Value]):
        return_ = ReturnStatement(value, self)
        return return_

    class _Action:
        def __init__(self, model: "MemoryModel",
                     en_port_name: str, rdy_port_name: str):
            self.name = ""
            self.model = model
            self.en_port_name = en_port_name
            self.rdy_port_name = rdy_port_name

        def __call__(self, f):
            self.name = f.__name__
            assert self.name != "" and self.name not in self.model._actions
            en_port_name = self.en_port_name if self.en_port_name \
                else f"EN_{self.name}"
            rdy_port_name = self.rdy_port_name if self.rdy_port_name else \
                f"RDY_{self.name}"
            # create ready-valid signals based on the function name
            # we need to be very careful about the port aliasing
            if en_port_name in self.model:
                # port aliasing
                self.model._ports[f"EN_{self.name}"] = \
                    self.model[en_port_name]
            else:
                self.model.Variable(f"EN_{self.name}", 1)
            if rdy_port_name in self.model:
                # port aliasing
                self.model._ports[f"RDY_{self.name}"] = \
                    self.model[rdy_port_name]
            else:
                self.model.Variable(f"RDY_{self.name}", 1)

            def wrapper():
                # we need to record every expressions here
                # TODO: fix this hack
                self.model.context.clear()
                v = f()
                # copy to the statement
                if v is not None:
                    self.model.Return(v)
                self.model._stmts[self.name] = self.model.context[:]
                self.model.context.clear()
                return v
            self.model._actions[self.name] = wrapper
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
            stmts = self._stmts[action_name] + self._global_stmts
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
            return_v = None
            for stmt in stmts:
                v = stmt.eval()
                if isinstance(stmt, ReturnStatement):
                    if len(v) == 1 and return_v is None:
                        return_v = v[0]
                    elif return_v is None:
                        return_v = v
            return return_v
        return wrapper

    @classmethod
    def mark(cls, func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
        return wrapper

    def after_config(self, func):
        name = func.__name__
        self._preprocess[name] = func

    @classmethod
    def async_reset(cls, func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper

    def get_loop_vars(self):
        return self._loop_vars.copy()

    # alias
    Variable = define_variable
    PortIn = define_port_in
    PortOut = define_port_out
    Constant = define_const
    Configurable = define_config
    If = define_if
    Return = define_return


# decorator to wrap around the define function. this is need to allow
# ast rewrite that respects to the scope
def define_memory(func: Callable[["MemoryModel"], None]):
    func_src = inspect.getsource(func)
    func_tree = ast.parse(textwrap.dedent(func_src))
    # remove the decorator
    func_tree.body[0].decorator_list = []
    # find the model name
    find_model_name = FindModelVariableName()
    find_model_name.visit(func_tree)
    assert find_model_name.name, "unable to find model variable name"
    model_name = find_model_name.name
    action_visitor = FindActionDefine()
    action_visitor.visit(func_tree)
    assert len(action_visitor.nodes) > 0
    # get all the marked as well
    mark_visitor = FindMarkedFunction("mark")
    mark_visitor.visit(func_tree)
    after_config_visitor = FindLoopRangeVar("after_config", model_name)
    after_config_visitor.visit(func_tree)
    nodes = action_visitor.nodes + mark_visitor.nodes +\
        after_config_visitor.nodes
    for action_node in nodes:
        # two passes
        # the first one convert all the assignment into function
        assign_visitor = AssignNodeVisitor()
        action_node = assign_visitor.visit(action_node)
        ast.fix_missing_locations(action_node)
        # second pass to convert if statement
        if_visitor = IfNodeVisitor(model_name)
        if_visitor.visit(action_node)
        ast.fix_missing_locations(action_node)
        # third pass to add int() call for every for loop
        for_transform = ForVarVisitor()
        for_transform.visit(action_node)

    # let the model know which config variables are used on loop generation
    # it's done through adding extra line to the source code
    if after_config_visitor.range_vars:
        node = add_model_loop_vars(model_name, after_config_visitor.range_vars,
                                   "add_loop_var")
        assert isinstance(func_tree.body[0].body[-1], ast.Return)
        func_tree.body[0].body.insert(-1, node)

    new_src = astor.to_source(func_tree, indent_with=" " * 2)
    func_name = func.__name__
    code_obj = compile(new_src, "<ast>", "exec")
    exec(code_obj, globals(), locals())
    namespace = locals()
    return namespace[func_name]
