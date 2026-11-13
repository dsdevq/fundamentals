from syslab.clock import ManualClock, SkewedClock


def test_manual_clock_moves_only_when_told_including_backwards():
    c = ManualClock(10)
    assert c() == 10
    c.advance(5)
    assert c() == 15
    c.set(3)
    assert c() == 3


def test_skewed_clock_offsets_add_up():
    base = ManualClock(100)
    c = SkewedClock(base)
    c.skew(50)
    c.skew(-20)
    assert c() == 130
    base.advance(1)
    assert c() == 131
