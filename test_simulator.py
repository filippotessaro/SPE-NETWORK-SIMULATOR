from event import Event


def test_time():
    smaller = Event(event_time=1, event_type=0, destination=0, source=0)
    larger = Event(event_time=2, event_type=0, destination=0, source=0)
    assert (smaller < larger)
    assert (larger > smaller)
    assert (not (smaller == larger))


def test_id():
    smaller = Event(event_time=1, event_type=0, destination=0, source=0)
    larger = Event(event_time=1, event_type=0, destination=0, source=0)
    smaller.event_id = 1
    larger.event_id = 2
    assert (smaller < larger)
    assert (larger > smaller)
    assert (not (smaller == larger))


def test_equality():
    smaller = Event(event_time=1, event_type=0, destination=0, source=0)
    larger = Event(event_time=1, event_type=0, destination=0, source=0)
    smaller.event_id = 1
    larger.event_id = 1
    assert (not (smaller < larger))
    assert (not (larger > smaller))
    assert (smaller == larger)
