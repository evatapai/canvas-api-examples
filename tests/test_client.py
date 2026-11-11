import pytest
import responses

from canvaslib.client import (
    CanvasAuthError,
    CanvasClient,
    CanvasError,
    CanvasRateLimitError,
)

BASE = "https://canvas.example.com"


@pytest.fixture
def sleeps():
    return []


@pytest.fixture
def client(sleeps):
    return CanvasClient(BASE, "test-token", sleep=sleeps.append)


@responses.activate
def test_get_sends_bearer_token(client):
    responses.get(f"{BASE}/api/v1/users/self", json={"id": "1"})
    assert client.get("users/self") == {"id": "1"}
    assert responses.calls[0].request.headers["Authorization"] == "Bearer test-token"


@responses.activate
def test_get_all_follows_link_header(client):
    page2 = f"{BASE}/api/v1/courses?page=2&per_page=100"
    responses.get(
        f"{BASE}/api/v1/courses",
        json=[{"id": 1}],
        headers={"Link": f'<{page2}>; rel="next"'},
    )
    responses.get(page2, json=[{"id": 2}])
    assert client.get_all("courses") == [{"id": 1}, {"id": 2}]


@responses.activate
def test_retries_429_then_succeeds(client, sleeps):
    responses.get(f"{BASE}/api/v1/users/self", status=429)
    responses.get(f"{BASE}/api/v1/users/self", json={"id": "1"})
    assert client.get("users/self") == {"id": "1"}
    assert sleeps == [1]


@responses.activate
def test_retries_403_rate_limit_message(client, sleeps):
    responses.get(f"{BASE}/api/v1/users/self", status=403, body="403 Forbidden (Rate Limit Exceeded)")
    responses.get(f"{BASE}/api/v1/users/self", json={"id": "1"})
    assert client.get("users/self") == {"id": "1"}
    assert len(sleeps) == 1


@responses.activate
def test_plain_403_is_not_retried(client, sleeps):
    responses.get(f"{BASE}/api/v1/users/self", status=403, body="user not authorized")
    with pytest.raises(CanvasError, match="403"):
        client.get("users/self")
    assert sleeps == []


@responses.activate
def test_retry_after_header_sets_wait(client, sleeps):
    responses.get(f"{BASE}/api/v1/users/self", status=429, headers={"Retry-After": "7"})
    responses.get(f"{BASE}/api/v1/users/self", json={})
    client.get("users/self")
    assert sleeps == [7]


@responses.activate
def test_gives_up_after_max_retries(client, sleeps):
    responses.get(f"{BASE}/api/v1/users/self", status=429)
    with pytest.raises(CanvasRateLimitError):
        client.get("users/self")
    assert sleeps == [1, 2, 4]


@responses.activate
def test_401_with_www_authenticate_means_bad_token(client):
    responses.get(f"{BASE}/api/v1/users/self", status=401, headers={"WWW-Authenticate": "Bearer"})
    with pytest.raises(CanvasAuthError, match="rejected the token"):
        client.get("users/self")


@responses.activate
def test_401_without_header_means_not_authorized(client):
    responses.get(f"{BASE}/api/v1/users/self", status=401)
    with pytest.raises(CanvasAuthError, match="may not access"):
        client.get("users/self")


def test_from_env_requires_both_variables(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_TOKEN", raising=False)
    with pytest.raises(CanvasError, match="CANVAS_BASE_URL, CANVAS_TOKEN"):
        CanvasClient.from_env()


def test_from_env_reads_dotenv_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_TOKEN", raising=False)
    (tmp_path / ".env").write_text(f"# comment\nCANVAS_BASE_URL={BASE}/\nCANVAS_TOKEN='abc'\n")
    client = CanvasClient.from_env()
    assert client.base_url == BASE
    assert client.session.headers["Authorization"] == "Bearer abc"
    monkeypatch.delenv("CANVAS_BASE_URL")
    monkeypatch.delenv("CANVAS_TOKEN")


def test_from_env_rejects_base_url_without_scheme(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CANVAS_BASE_URL", "canvas.example.com")
    monkeypatch.setenv("CANVAS_TOKEN", "abc")
    with pytest.raises(CanvasError, match="https://"):
        CanvasClient.from_env()


# --- OAuth2 refresh ---------------------------------------------------------

from urllib.parse import parse_qs

from canvaslib.client import RefreshCredentials

TOKEN_URL = f"{BASE}/login/oauth2/token"
REJECTED = {"WWW-Authenticate": "Bearer"}


@pytest.fixture
def refreshing_client(sleeps):
    refresh = RefreshCredentials("client-1", "secret-1", "refresh-1")
    return CanvasClient(BASE, "old-token", refresh=refresh, sleep=sleeps.append)


@responses.activate
def test_refreshes_expired_token_and_retries(refreshing_client):
    responses.get(f"{BASE}/api/v1/users/self", status=401, headers=REJECTED)
    responses.post(TOKEN_URL, json={"access_token": "new-token"})
    responses.get(f"{BASE}/api/v1/users/self", json={"id": "1"})

    assert refreshing_client.get("users/self") == {"id": "1"}

    refresh_call = responses.calls[1].request
    assert parse_qs(refresh_call.body) == {
        "grant_type": ["refresh_token"],
        "client_id": ["client-1"],
        "client_secret": ["secret-1"],
        "refresh_token": ["refresh-1"],
    }
    assert "Authorization" not in refresh_call.headers
    assert responses.calls[2].request.headers["Authorization"] == "Bearer new-token"


@responses.activate
def test_refreshes_only_once(refreshing_client):
    responses.get(f"{BASE}/api/v1/users/self", status=401, headers=REJECTED)
    responses.post(TOKEN_URL, json={"access_token": "new-token"})
    with pytest.raises(CanvasAuthError, match="rejected the token"):
        refreshing_client.get("users/self")
    assert len([c for c in responses.calls if c.request.method == "POST"]) == 1


@responses.activate
def test_401_without_www_authenticate_does_not_refresh(refreshing_client):
    responses.get(f"{BASE}/api/v1/users/self", status=401)
    with pytest.raises(CanvasAuthError, match="may not access"):
        refreshing_client.get("users/self")
    assert len(responses.calls) == 1


@responses.activate
def test_failed_refresh_explains_what_to_do(refreshing_client):
    responses.get(f"{BASE}/api/v1/users/self", status=401, headers=REJECTED)
    responses.post(TOKEN_URL, status=400, json={"error": "invalid_grant"})
    with pytest.raises(CanvasAuthError, match="Could not refresh the token"):
        refreshing_client.get("users/self")


@responses.activate
def test_starts_with_refresh_when_there_is_no_access_token(sleeps):
    refresh = RefreshCredentials("client-1", "secret-1", "refresh-1")
    client = CanvasClient(BASE, refresh=refresh, sleep=sleeps.append)
    responses.post(TOKEN_URL, json={"access_token": "fresh-token"})
    responses.get(f"{BASE}/api/v1/users/self", json={"id": "1"})

    assert client.get("users/self") == {"id": "1"}
    assert responses.calls[1].request.headers["Authorization"] == "Bearer fresh-token"


@responses.activate
def test_warns_when_canvas_issues_a_new_refresh_token(refreshing_client, capsys):
    responses.get(f"{BASE}/api/v1/users/self", status=401, headers=REJECTED)
    responses.post(TOKEN_URL, json={"access_token": "new-token", "refresh_token": "refresh-2"})
    responses.get(f"{BASE}/api/v1/users/self", json={})
    refreshing_client.get("users/self")
    assert "new refresh token" in capsys.readouterr().err
    assert refreshing_client.refresh.refresh_token == "refresh-2"


def test_client_needs_a_token_or_refresh_values():
    with pytest.raises(CanvasError, match="access token, or refresh"):
        CanvasClient(BASE)


def test_from_env_accepts_refresh_values_without_token(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CANVAS_BASE_URL", BASE)
    monkeypatch.setenv("CANVAS_CLIENT_ID", "id")
    monkeypatch.setenv("CANVAS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("CANVAS_REFRESH_TOKEN", "refresh")
    assert CanvasClient.from_env().refresh.client_id == "id"


def test_from_env_rejects_partial_refresh_values(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CANVAS_BASE_URL", BASE)
    monkeypatch.setenv("CANVAS_TOKEN", "abc")
    monkeypatch.setenv("CANVAS_CLIENT_ID", "id")
    with pytest.raises(CanvasError, match="CANVAS_CLIENT_SECRET, CANVAS_REFRESH_TOKEN"):
        CanvasClient.from_env()


# --- writes, host guard, quota headers --------------------------------------

from canvaslib.client import require_course_id


@responses.activate
def test_post_sends_canvas_style_form_fields(client):
    responses.post(f"{BASE}/api/v1/courses/5/assignments", json={"id": 9})
    assert client.post("courses/5/assignments", data={"assignment[name]": "x"}) == {"id": 9}
    assert parse_qs(responses.calls[0].request.body) == {"assignment[name]": ["x"]}


@responses.activate
def test_put_and_delete(client):
    responses.put(f"{BASE}/api/v1/things/1", json={"ok": 1})
    responses.delete(f"{BASE}/api/v1/things/1", json={"deleted": 1})
    assert client.put("things/1", data={"a": "b"}) == {"ok": 1}
    assert client.delete("things/1") == {"deleted": 1}


def test_refuses_to_send_the_token_to_another_host(client):
    with pytest.raises(CanvasError, match="another host"):
        client.get("https://evil.example.com/api/v1/users/self")


@responses.activate
def test_remembers_quota_headers(client):
    responses.get(
        f"{BASE}/api/v1/users/self",
        json={},
        headers={"X-Request-Cost": "0.05", "X-Rate-Limit-Remaining": "599.9"},
    )
    client.get("users/self")
    assert client.last_rate_limit == {"request_cost": "0.05", "rate_limit_remaining": "599.9"}


def test_require_course_id(monkeypatch):
    with pytest.raises(CanvasError, match="CANVAS_COURSE_ID"):
        require_course_id()
    monkeypatch.setenv("CANVAS_COURSE_ID", "abc")
    with pytest.raises(CanvasError, match="CANVAS_COURSE_ID"):
        require_course_id()
    monkeypatch.setenv("CANVAS_COURSE_ID", "42")
    assert require_course_id() == "42"
