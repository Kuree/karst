from typing import Dict, Set
from karst.model import MemoryModel, Memory
from karst.backend import get_updated_variables, get_state_updates, \
    get_memory_access, get_var_memory_access, get_mem_access_temporal_spacing,\
    get_linear_spacing
from karst.values import Expression, Variable


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
                if spaced:
                    self.access_spacing[var] = spacing
                else:
                    # no pattern, we assume it's random access
                    self.access_spacing[var] = None


class BasicScheduler(Scheduler):
    def __init__(self, model: MemoryModel, num_ports: int = 1):
        super().__init__(model, num_ports)
