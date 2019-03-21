from karst.scheduler import *
from karst.basic import *
import pytest


@pytest.mark.parametrize("num_ports", (1, 2))
def test_basic_scheduler_fifo(num_ports):
    fifo = define_fifo(4)
    scheduler = BasicScheduler(fifo, num_ports)
    # this should be already tested in the backend, some asserts here
    # just to be sure it's doing the correct thing
    assert len(scheduler.update_spacing) == 2
    assert scheduler.update_spacing[fifo.read_addr] == 1
    assert scheduler.update_spacing[fifo.write_addr] == 1
    assert scheduler.get_minimum_cycle() == 2 / num_ports
    port_size = scheduler.get_port_size(2, 2)
    assert port_size == 1 if num_ports == 2 else 2
    scheduler.schedule()


@pytest.mark.parametrize("num_ports", (1, 2))
def test_basic_scheduler_sram(num_ports):
    sram = define_sram(4)
    scheduler = BasicScheduler(sram, num_ports)
    assert len(scheduler.update_spacing) == 1
    assert scheduler.update_spacing[sram.addr] is None
    assert scheduler.access_spacing[sram.addr] is None
    assert scheduler.get_minimum_cycle() == 2 / num_ports
    port_size = scheduler.get_port_size(2, 2)
    # this is random access for the same address, so no matter how many number
    # of ports you have, you only need size 1
    assert port_size == 1
    scheduler.schedule()


@pytest.mark.parametrize("num_ports", (1, 2))
def test_basic_scheduler_lb(num_ports):
    num_row = 4
    line_depth = 4
    lb = define_line_buffer(line_depth, num_row)
    scheduler = BasicScheduler(lb, num_ports)
    assert len(scheduler.update_spacing) == 2
    assert scheduler.update_spacing[lb.read_addr] == 1
    assert scheduler.update_spacing[lb.write_addr] == 1
    # line buffer is more interesting
    assert len(scheduler.read_var) == num_row
    for exp, var in scheduler.read_var.items():
        assert var in scheduler.update_spacing
        assert scheduler.update_spacing[var] == 1
        assert scheduler.access_spacing[var] == line_depth
    minimum_cycle = scheduler.get_minimum_cycle()
    assert minimum_cycle == num_row if num_ports == 2 else \
        num_row + 1
    port_size = scheduler.get_port_size(minimum_cycle, minimum_cycle)
    assert port_size == minimum_cycle
    scheduler.schedule()
