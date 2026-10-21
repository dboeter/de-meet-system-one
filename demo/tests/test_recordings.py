import pytest

from jevdemo.judge import Judge
from jevdemo.stations import STATIONS


@pytest.mark.parametrize("station", STATIONS)
def test_every_station_request_is_recorded(station):
    judge = Judge(mode="recorded")
    missing = [
        state
        for state, questions in STATIONS[station]()
        if not judge.has(state, questions)
    ]
    assert missing == [], (
        f"{len(missing)} {station} requests lack a recording; run scripts/record.py"
    )
