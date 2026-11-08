"""Regression test against the measured numbers in MASTER_PLAN section 2.2. Skips if data is absent."""
import collections, os, pytest
from src.parse import load_show, parse_episode_text, ParseError

DATA = os.environ.get("PROMO_DATA", "data/show1")
pytestmark = pytest.mark.skipif(not os.path.isdir(DATA), reason="episode data not present")


@pytest.fixture(scope="module")
def eps():
    return load_show(DATA)


def test_counts(eps):
    k = collections.Counter(b.kind for e in eps for b in e.blocks)
    assert len(eps) == 50
    assert sum(len(e.scenes) for e in eps) == 100
    assert sum(k.values()) == 3727
    assert k["camera"] == 1754 and k["action"] == 372
    assert k["speech"] + k["audio_cue"] == 1601 and k["audio_cue"] == 114
    assert round(sum(e.duration for e in eps)) == 6163


def test_no_anomalies_and_ids_unique(eps):
    assert all(not e.anomalies for e in eps)
    ids = [b.id for e in eps for b in e.blocks]
    assert len(ids) == len(set(ids))
    assert [e.number for e in eps] == list(range(1, 51))


def test_loud_failure():
    bad = "EPISODE NUMBER: Episode 1\nEPISODE LOGLINE: x\nCONTINUITY NOTES: y\n\n--- SCRIPT START ---\n\nSCENE 01\nScene heading: X\nScene start: 00:00.00\nScene end: 00:10.00\n\n**CAMERA:**\nnot a time line\n"
    with pytest.raises(ParseError):
        parse_episode_text(bad, "episode-001-x.txt")
