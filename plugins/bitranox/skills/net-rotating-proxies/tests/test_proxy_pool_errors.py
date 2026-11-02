"""What proxy_pool's error handlers absorb: what a hostile list or a full disk raises, not a bug."""
import socket
import threading

import proxy_pool as pp
import pytest


def _closed_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


# An empty list would fall back to the public default sources and reach the internet.
_NO_NETWORK = ["not a url"]


class _StopAfter(threading.Event):
    """A stop event whose wait() lets the loop body run `rounds` times, with no real sleeping."""

    def __init__(self, rounds):
        super().__init__()
        self._rounds = rounds

    def wait(self, timeout=None):
        self._rounds -= 1
        return self._rounds < 0


# A proxy list is arbitrary text from the internet, and each of these raises something else out of
# httpx2: InvalidURL for the unparsable ones (not an HTTPError), ConnectError for the rest.
@pytest.mark.parametrize("proxy", ["256.256.256.256:99999", "1.2.3.4:notaport", "[bad", "a b:80",
                                   "a\nb:80", "x" * 70000 + ":1", "", ":"])
def test_a_hostile_proxy_string_reads_as_unreachable(proxy):
    assert pp._reachable(proxy, f"http://127.0.0.1:{_closed_port()}/", 0.5) == (False, None)


def test_a_proxy_refusing_the_connection_reads_as_unreachable():
    target = f"http://127.0.0.1:{_closed_port()}/"
    assert pp._reachable(f"127.0.0.1:{_closed_port()}", target, 0.5) == (False, None)


def test_a_bug_in_the_reachability_call_is_not_reported_as_a_dead_proxy():
    # A url of the wrong type is a programming error: reading it as (False, None) would ban every
    # proxy in the pool for it.
    with pytest.raises(TypeError):
        pp._reachable(f"127.0.0.1:{_closed_port()}", 12345, 0.5)


@pytest.mark.parametrize("source", ["not a url", "ftp://example.invalid/", "http://a\nb/",
                                    "http://x" + "y" * 70000])
def test_discover_survives_a_source_it_cannot_fetch(tmp_path, capsys, source):
    assert pp.discover(str(tmp_path), [source]) == 0
    assert "ERR" in capsys.readouterr().out


def test_discover_counts_a_refusing_source_as_unanswered(tmp_path):
    assert pp.discover(str(tmp_path), [f"http://127.0.0.1:{_closed_port()}/"]) == 0


class _FailingPool(pp.ProxyPool):
    def __init__(self, store, error):
        super().__init__(store, None, test_url="http://unused.invalid/", vtimeout=1)
        self.error = error
        self.calls = 0

    def benchmark_once(self):
        self.calls += 1
        raise self.error


def test_the_benchmark_loop_survives_a_file_error(tmp_path, capsys):
    pool = _FailingPool(str(tmp_path), OSError(28, "No space left on device"))
    pool.benchmark_loop(_StopAfter(2), 0)
    assert pool.calls == 2
    assert "No space left" in capsys.readouterr().out


def test_the_benchmark_loop_does_not_absorb_a_bug(tmp_path):
    pool = _FailingPool(str(tmp_path), KeyError("a bug"))
    with pytest.raises(KeyError):
        pool.benchmark_loop(_StopAfter(2), 0)


def test_the_refresh_loop_survives_a_file_error(tmp_path, capsys):
    # A store directory that does not exist: discover's merge fails with an OSError every round.
    missing = str(tmp_path / "gone")
    pp._bg_refresh(missing, "http://unused.invalid/", 1, 1, _StopAfter(2), interval=0,
                   sources=_NO_NETWORK)
    assert capsys.readouterr().out.count("bg refresh error") == 2


def test_the_refresh_loop_does_not_absorb_a_bug(tmp_path):
    # need of the wrong type: comparing it with a count is a programming error, not a bad minute.
    with pytest.raises(TypeError):
        pp._bg_refresh(str(tmp_path), "http://unused.invalid/", 1, 1, _StopAfter(1), need="five",
                       interval=0, sources=_NO_NETWORK)
