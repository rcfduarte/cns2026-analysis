from cns_scientometrics.http_cache import cached_get


def test_cache_returns_stored_without_refetch(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_fetch(url, params, user_agent=None):
        calls["n"] += 1
        return "<xml>ok</xml>"

    monkeypatch.setattr("cns_scientometrics.http_cache._raw_fetch", fake_fetch)
    a = cached_get("http://x", None, "k1", tmp_path)
    b = cached_get("http://x", None, "k1", tmp_path)
    assert a == b == "<xml>ok</xml>"
    assert calls["n"] == 1  # second call served from disk


def test_stable_key_is_deterministic():
    from cns_scientometrics.http_cache import stable_key

    assert stable_key("abc") == stable_key("abc")
    assert stable_key("a", "b") != stable_key("ab")
    assert len(stable_key("x")) == 16
