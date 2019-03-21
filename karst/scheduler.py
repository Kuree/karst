from typing import Dict
from karst.model import MemoryModel, Memory
from karst.backend import get_updated_variables, get_state_updates, \
    get_memory_access, get_var_memory_access, get_mem_access_temporal_spacing,\
    get_linear_spacing
from karst.values import Expression, Variable
import abc
import math
from typing import Union


class Scheduler:
    def __init__(self, model: MemoryModel, num_ports: int = 1):
        assert num_ports in (1, 2), f"{num_ports} ports not supported"
        self._model = model
        self._num_ports = num_ports

        # the only thing we care about
        self.update_spacing = {}
        self.access_spacing = {}
        self.read_var: Dict[Expression, Variable] = {}
        self.write_var: Dict[Expression, Variable] = {}

        # compute the memory access
        accesses = get_memory_access(model)
        statements = model.produce_statements()
        for action_name, stmts in statements.items():
            updates = get_state_updates(stmts)
            variable_update = get_updated_variables(updates)
            if action_name not in accesses:
                # e.g. clear
                continue
            access = accesses[action_name]
            access_vars = get_var_memory_access(access)
            temp_spacing = \
                get_mem_access_temporal_spacing(variable_update,
                                                list(access_vars.keys()))
            for var, spacing in temp_spacing.items():
                if var in self.update_spacing:
                    assert self.update_spacing[var] == spacing
                self.update_spacing[var] = spacing
            # compute the access spacing
            for var, patterns in access_vars.items():
                variables = []
                for ac_var, t in patterns:
                    if t == Memory.MemoryAccessType.Read:
                        self.read_var[ac_var] = var
                    else:
                        self.write_var[ac_var] = var
                    variables.append(ac_var)
                # compute the spacing
                spaced, spacing = get_linear_spacing(*variables)
                if spaced and spacing > 0:
                    self.access_spacing[var] = spacing
                else:
                    # no pattern, we assume it's random access
                    self.access_spacing[var] = None

    @abc.abstractmethod
    def schedule(self):
        """schedule for the memory resource"""


class State:
    def __init__(self, state_value: int,
                 state_transition: Dict[Expression,
                                        Union["State", None]] = None):
        self.state_value = state_value
        state_transition = {} if state_transition is None else state_transition
        self.state_transition = state_transition
        self.access_var: Expression = None

    def __hash__(self):
        return hash(self.state_value)


class BasicScheduler(Scheduler):
    def __init__(self, model: MemoryModel, num_ports: int = 1):
        super().__init__(model, num_ports)

    def get_minimum_cycle(self):
        """Get the minimum number of cycles needed to perform all the actions
        """
        num_read = {}
        num_write = {}
        for ac_var, root_var in self.read_var.items():
            assert root_var in self.access_spacing
            if self.access_spacing[root_var] is None:
                # random access
                num_read[root_var] = 1
            else:
                if root_var not in num_read:
                    num_read[root_var] = 0
                num_read[root_var] += 1
        for ac_var, root_var in self.write_var.items():
            assert root_var in self.access_spacing
            if self.access_spacing[root_var] is None:
                # random access
                num_write[root_var] = 1
            else:
                if root_var not in num_write:
                    num_write[root_var] = 0
                num_write[root_var] += 1
        # compute the cycle based on if the root variable access is random
        # access or not
        r_result = 0
        w_result = 0
        for _, v in num_read.items():
            r_result += v
        for _, v in num_write.items():
            w_result += v
        if self._num_ports == 1:
            return r_result + w_result
        else:
            return max(r_result, w_result)

    def get_port_size(self, throughput_cycle: int, total_cycle: int):
        # we need to compute the how many read and write throughput
        # in total
        # notice that due to stride we need to extra careful how the throughput
        # is defined
        assert total_cycle >= throughput_cycle
        assert throughput_cycle >= self.get_minimum_cycle()
        read_throughput = 0
        for ac_var, root_var in self.read_var.items():
            var_throughput = 1
            if self.update_spacing[root_var] is not None:
                spacing = self.update_spacing[root_var]
                var_throughput += spacing * (throughput_cycle - 1)
            read_throughput += var_throughput

        write_throughput = 0
        for ac_var, root_var in self.write_var.items():
            var_throughput = 1
            if self.update_spacing[root_var] is not None:
                spacing = self.update_spacing[root_var]
                var_throughput += spacing * (throughput_cycle - 1)
            write_throughput += var_throughput
        if self._num_ports == 1:
            # single port memory. need to satisfy the throughput
            port_size = int(math.ceil((read_throughput + write_throughput)
                                      / total_cycle))
            return port_size
        else:
            max_throughput = max(read_throughput, write_throughput)
            port_size = int(math.ceil(max_throughput / total_cycle))
            return port_size

    def schedule(self):
        """The basic scheduler tries its best to schedule for minimum cycle
        delay"""
        cycle = self.get_minimum_cycle()
        port_size = self.get_port_size(cycle, cycle)
        total_num_state = len(self.read_var) + len(self.write_var)
        # state 0 is always do nothing
        states = [State(0, None)]
        for state_id in range(1, total_num_state + 1):
            states.append(State(state_id, None))
        # for now we can only do one read and one write
        print(self.update_spacing)
        assert len(self.update_spacing) <= 2
        (read_var, num_read_vars), (write_var, num_write_vars)\
            = self.__get_read_write_var()
        assert read_var is not None and write_var is not None
        # should we prefetch the read?
        if self.update_spacing[read_var] is not None:
            # we need to prefetch them, starting
            pass

    def __get_read_write_var(self):
        # get the read variable name
        read_var: Variable = None
        write_var: Variable = None
        num_read_vars = 0
        num_write_vars = 0
        for _, root in self.read_var.items():
            assert read_var is None or read_var.eq(root)
            read_var = root
            num_read_vars += 1
        for _, root in self.write_var.items():
            assert write_var is None or write_var.eq(root)
            write_var = root
            num_write_vars += 1
        return (read_var, num_read_vars), (write_var, num_write_vars)
