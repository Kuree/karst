from .basic import define_row_buffer, define_sram, define_fifo,\
    define_double_buffer
from .model import MemoryModel
from .values import Configurable, Port, Value, PortType
from typing import Dict, Union, Tuple, List
import enum


@enum.unique
class MemoryMode(enum.Enum):
    SRAM = 0
    FIFO = 1
    RowBuffer = 2
    DoubleBuffer = 3


class MemoryInstruction:
    def __init__(self, memory_mode: MemoryMode,
                 values: Dict[str, int] = None,
                 data_entries: List[Tuple[int, int]] = None):
        self.memory_mode = memory_mode
        if values is None:
            values = {}
        self.values = values
        if data_entries is None:
            data_entries = []
        self.data_entries = data_entries


class MemoryCore:
    """functional model for memory core. we don't need to add configuration
    space as it's too low level"""

    def __init__(self, memory_size):
        self._sram = define_sram()
        self._fifo = define_fifo()
        self._row_buffer = define_row_buffer()
        self._double_buffer = define_double_buffer()

        self._models: Dict[MemoryMode, MemoryModel] = {
            MemoryMode.SRAM: self._sram,
            MemoryMode.FIFO: self._fifo,
            MemoryMode.RowBuffer: self._row_buffer,
            MemoryMode.DoubleBuffer: self._double_buffer
        }

        self.memory_size = memory_size

        self._action_names = {
            MemoryMode.SRAM: {"wen": "write", "ren": "read"},
            MemoryMode.FIFO: {"wen": "enqueue", "ren": "dequeue"},
            MemoryMode.RowBuffer: {"wen": "enqueue"}}

        # get all the configurables
        self.config_vars: Dict[str, Configurable] = {}
        # ports
        self.ports: Dict[str, Port] = {}

        self._mem: Union[MemoryModel, None] = None
        self._instr: Union[MemoryInstruction, None] = None

        # depends on the latency, we may latch out the data for next cycle
        self._last_values = {}

        # compute the address space
        # notice that we need multiple feature spaces
        # config_regs
        self._config_regs = []
        mode_keys = list(self._models.keys())
        mode_keys.sort(key=lambda m: m.value)
        for mode in mode_keys:
            model: MemoryModel = self._models[mode]
            vars = []
            for var_name in model.get_config_vars():
                if var_name == MemoryModel.MEMORY_SIZE:
                    continue
                assert var_name not in self._config_regs
                vars.append(var_name)
            vars.sort()
            self._config_regs += vars

    def __get_vars(self, model: MemoryModel):
        self.config_vars.clear()
        self.ports.clear()

        def _update(var_dict: Dict[str, Value], update_dict: Dict[str, Value]):
            for name, var in var_dict.items():
                if name in update_dict:
                    # double check if it's the same type
                    old_var = update_dict[name]
                    assert old_var.eq(var)
                else:
                    update_dict[name] = var
        # configurables
        variables = model.get_config_vars()
        _update(variables, self.config_vars)
        # ports
        variables = model.get_ports()
        _update(variables, self.ports)

    def configure(self, instr: MemoryInstruction):
        mode = instr.memory_mode
        values = instr.values.copy()
        self._mem = self._models[mode]
        values[MemoryModel.MEMORY_SIZE] = self.memory_size
        self._mem.configure(**values)
        self.__get_vars(self._mem)
        self._instr = instr
        self._mem.produce_statements()
        # write to memory
        for addr, data in instr.data_entries:
            self._mem.write_to_mem(addr, data)

    def eval(self, **kargs):
        for name, value in kargs.items():
            if name in self.ports \
                    and self.ports[name].port_type == PortType.In:
                self.ports[name](value).eval()
        actions = set()
        # figure out which action to trigger
        for name, var in self.ports.items():
            if name[:3] == "EN_":
                var_name = var.name
                if var.eval() == 1:
                    action_map = self._action_names[self._instr.memory_mode]
                    actions.add(action_map[var_name])

        for action_name in actions:
            self._mem[action_name]()
        result = {}
        for name, var in self.ports.items():
            if var.port_type == PortType.Out:
                result[name] = var.eval()

        if self._instr.memory_mode == MemoryMode.SRAM:
            temp = self._last_values
            self._last_values = result
            return temp
        return result

    def get_bitstream(self, instr: MemoryInstruction):
        # the first register is always the mode
        result = [(0, instr.memory_mode.value)]
        for var, value in instr.values.items():
            assert var in self._config_regs
            index = self._config_regs.index(var) + 1
            result.append((index, value))
        # TODO:
        # need to figure out how to deal with multiple features

        return result
