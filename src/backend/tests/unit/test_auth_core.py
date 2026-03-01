import time

import pytest
from fastapi import HTTPException

import backend.shared.auth as auth


class TestAuthCore:
    def setup_method(self):
        auth.SESSION_TOKENS.clear()

    def test_is_valid_session_unknown_token_false(self):
        assert auth.is_valid_session("missing") is False

    def test_is_valid_session_expired_token_false_and_removed(self, monkeypatch):
        now = 1000.0
        monkeypatch.setattr(time, "time", lambda: now)
        auth.SESSION_TOKENS["t1"] = now - 1

        assert auth.is_valid_session("t1") is False
        assert "t1" not in auth.SESSION_TOKENS

    def test_is_valid_session_valid_token_true_and_sliding_window(self, monkeypatch):
        now = 1000.0
        monkeypatch.setattr(time, "time", lambda: now)
        auth.SESSION_TOKENS["t1"] = now + 10

        assert auth.is_valid_session("t1") is True
        assert auth.SESSION_TOKENS["t1"] == pytest.approx(now + auth.SESSION_DURATION)

    def test_require_token_master_token_ok(self, monkeypatch):
        monkeypatch.setattr(auth, "_get_master_token", lambda: "master")
        auth.require_token("master")

    def test_require_token_session_token_ok(self, monkeypatch):
        monkeypatch.setattr(auth, "_get_master_token", lambda: "master")
        monkeypatch.setattr(auth, "is_valid_session", lambda t: t == "sess")
        auth.require_token("sess")

    def test_require_token_server_not_configured_500(self, monkeypatch):
        monkeypatch.setattr(auth, "_get_master_token", lambda: "")
        with pytest.raises(HTTPException) as ex:
            auth.require_token("any")
        assert ex.value.status_code == 500

    def test_require_token_missing_header_401(self, monkeypatch):
        monkeypatch.setattr(auth, "_get_master_token", lambda: "master")
        with pytest.raises(HTTPException) as ex:
            auth.require_token(None)
        assert ex.value.status_code == 401

    def test_require_token_invalid_header_401(self, monkeypatch):
        monkeypatch.setattr(auth, "_get_master_token", lambda: "master")
        monkeypatch.setattr(auth, "is_valid_session", lambda t: False)
        with pytest.raises(HTTPException) as ex:
            auth.require_token("bad")
        assert ex.value.status_code == 401
