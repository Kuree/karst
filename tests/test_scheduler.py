from karst.scheduler import *
from karst.basic import *


def test_basic_scheduler():
    fifo = define_fifo(10)
    scheduler = BasicScheduler({})
