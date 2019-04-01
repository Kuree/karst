import pytest
from karst.macro import *


@pytest.mark.parametrize("ports", [(1, 1), (2, 1), (2, 2)])
@pytest.mark.parametrize("partial_write", [True, False])
@pytest.mark.parametrize("port_size", [1 << 4])
def test_port_generation(ports, port_size, partial_write):
    num_ports, num_en_ports = ports
    mem_size_log = 4
    sram = SRAMMacro(size=1 << mem_size_log, port_size=port_size,
                     partial_write=partial_write, num_en_ports=num_en_ports,
                     num_ports=num_ports)
    ports = sram.get_ports()
    wen_count = 0
    ren_count = 0
    addr_count = 0
    data_in_count = 0
    data_out_count = 0
    partial_write_count = 0

    def has_port(port_name_, expected_name):
        if port_name_[:len(expected_name)] == expected_name:
            if port_name[len(expected_name):].isdigit():
                return True
        return False
    for port_name, size_ in ports.items():
        if has_port(port_name, "wen"):
            wen_count += 1
        elif has_port(port_name, "ren"):
            ren_count += 1
        elif has_port(port_name, "addr"):
            addr_count += 1
            assert size_ == mem_size_log
        elif has_port(port_name, "data_in"):
            data_in_count += 1
        elif has_port(port_name, "data_out"):
            data_out_count += 1
        elif has_port(port_name, "wenb"):
            partial_write_count += 1
    assert wen_count == ren_count
    assert wen_count == num_en_ports
    if partial_write:
        assert partial_write_count == num_en_ports
    assert data_in_count == data_out_count
    assert data_in_count == num_en_ports
