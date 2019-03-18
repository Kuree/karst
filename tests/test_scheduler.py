from karst.scheduler import *
from karst.basic import *


def test_basic_scheduler_fifo():
    fifo = define_fifo(42)
    scheduler = BasicScheduler(fifo)
    # this should be already tested in the backend, some asserts here
    # just to be sure it's doing the correct thing
    assert len(scheduler.update_spacing) == 2
    assert scheduler.update_spacing[fifo.read_addr] == 1
    assert scheduler.update_spacing[fifo.write_addr] == 1


def test_basic_scheduler_sram():
    sram = define_sram(42)
    scheduler = BasicScheduler(sram)
    assert len(scheduler.update_spacing) == 1
    assert scheduler.update_spacing[sram.addr] is None
    assert scheduler.access_spacing[sram.addr] is None


def test_basic_scheduler_lb():
    num_row = 4
    line_depth = 42
    lb = define_line_buffer(line_depth, num_row)
    scheduler = BasicScheduler(lb)
    assert len(scheduler.update_spacing) == 2
    assert scheduler.update_spacing[lb.read_addr] == 1
    assert scheduler.update_spacing[lb.write_addr] == 1
    # line buffer is more interesting
    assert len(scheduler.read_var) == num_row
    for exp, var in scheduler.read_var.items():
        assert var in scheduler.update_spacing
        assert scheduler.update_spacing[var] == 1
        assert scheduler.access_spacing[var] == line_depth
