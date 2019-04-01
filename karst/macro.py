import math
from typing import Dict


class SRAM:
    def __init__(self, size: int, port_size: int, partial_write: bool = True,
                 num_ports: int = 1, num_en_ports: int = 1):
        assert size != 0 and ((size & (size - 1)) == 0), \
            f"{size} has to be 2's power"
        self.size = size
        self.port_size = port_size
        self.partial_write = partial_write
        self.num_ports = num_ports
        assert num_en_ports <= num_ports, \
            f"number of enable ports ({num_en_ports} cannot be larger " \
            f"than number of ports (f{num_ports})"
        self.num_en_ports = num_en_ports

    def get_ports(self) -> Dict[str, int]:
        """:return dict of ports based on the SRAM configuration"""
        results = {}
        addr_size = int(math.log2(self.size))
        for idx in range(self.num_en_ports):
            results[f"wen{idx}"] = 1
        for idx in range(self.num_en_ports):
            results[f"ren{idx}"] = 1
        for idx in range(self.num_ports):
            results[f"addr{idx}"] = addr_size
        for idx in range(self.num_en_ports):
            results[f"data_in{idx}"] = self.port_size
        for idx in range(self.num_en_ports):
            results[f"data_out{idx}"] = self.port_size
        if self.partial_write:
            for idx in range(self.num_en_ports):
                results[f"wenb{idx}"] = 1
        # notice that cen signal will be generated from wen and ren
        # when lowering to verilog
        return results
