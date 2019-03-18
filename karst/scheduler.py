from typing import Dict, List, Tuple
from karst.model import Memory
from karst.values import Expression, Variable


class Scheduler:
    def __init__(self,
                 variable_access: Dict[Variable,
                                       List[Tuple[Expression,
                                                  Memory.MemoryAccessType]]]):
        self._variable_access = variable_access

    def _find_minimum_period(self, num_ports: int = 1):
        """find the minimum number of cycles to perform all the actions.
        default to single port"""


class BasicScheduler(Scheduler):
    def __init__(self,
                 variable_access: Dict[Variable,
                                       List[Tuple[Expression,
                                                  Memory.MemoryAccessType]]]):
        super().__init__(variable_access)
