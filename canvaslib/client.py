"""Small Canvas REST client shared by every recipe.

It handles the things beginners usually get wrong: following pagination
links, retrying when Canvas throttles you, refreshing an expired OAuth2
access token, and explaining 401 errors.
"""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

API_PREFIX = "api/v1"
TOKEN_PATH = "login/oauth2/token"
REQUEST_TIMEOUT_SECONDS = 30
REFRESH_VARS = ("CANVAS_CLIENT_ID", "CANVAS_CLIENT_SECRET", "CANVAS_REFRESH_TOKEN")


class CanvasError(Exception):
    """Base class for every error this client raises."""


class CanvasAuthError(CanvasError):
    """Canvas answered 401, or refreshing the token failed."""


class CanvasRateLimitError(CanvasError):
    """Canvas still throttled the request after all retries."""


@dataclass
class RefreshCredentials:
    client_id: str
    client_secret: str
    refresh_token: str


def load_env_file(path=".env"):
    """Load KEY=value lines from a .env file without overriding real env vars."""
    env_file = Path(path)
    if not env_file.is_file():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def read_refresh_credentials():
    """Return the three OAuth2 refresh values from the environment, or None if unset."""
    values = [os.environ.get(name, "") for name in REFRESH_VARS]
    if not any(values):
        return None
    missing = [name for name, value in zip(REFRESH_VARS, values) if not value]
    if missing:
        raise CanvasError(
            f"Token refresh needs all three values. Missing: {', '.join(missing)}."
        )
    return RefreshCredentials(*values)


def require_course_id():
    """Recipes that change data only run in the course you name in .env."""
    course_id = os.environ.get("CANVAS_COURSE_ID", "")
    if not course_id.isdigit():
        raise CanvasError(
            "This recipe changes data. Set CANVAS_COURSE_ID in .env to the numeric id "
            "of a course you are happy to test in (use a demo course, never a real one)."
        )
    return course_id


def require_enroll_user_id():
    """Recipe 6 enrolls this demo user. It must not be the user the token belongs to."""
    user_id = os.environ.get("CANVAS_ENROLL_USER_ID", "")
    if not user_id.isdigit():
        raise CanvasError(
            "Set CANVAS_ENROLL_USER_ID in .env to the numeric id of a demo user who may be "
            "enrolled in your demo course. It must be a different user than the token's user."
        )
    return user_id


def is_rate_limited(response):
    """Canvas signals throttling with 429, or with 403 and a rate limit message."""
    if response.status_code == 429:
        return True
    return response.status_code == 403 and "rate limit" in response.text.lower()


def is_rejected_token(response):
    """A 401 with a WWW-Authenticate header means the token itself was rejected."""
    return response.status_code == 401 and bool(response.headers.get("WWW-Authenticate"))


def backoff_seconds(response, attempt):
    """Wait as long as Retry-After says, otherwise 1s, 2s, 4s..."""
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return int(retry_after)
    return 2**attempt


def raise_for_error(response):
    """Turn an error response into a CanvasError with a useful message."""
    if response.ok:
        return
    if response.status_code == 401:
        if is_rejected_token(response):
            raise CanvasAuthError(
                "401: Canvas rejected the token. It is invalid, expired or revoked. "
                "It may also have been issued for a different Canvas domain. "
                "Generate a new one, or set the refresh values in .env."
            )
        raise CanvasAuthError(
            "401: the token is valid but this user may not access this resource."
        )
    raise CanvasError(f"{response.status_code} from Canvas: {response.text[:300]}")


class CanvasClient:
    def __init__(
        self,
        base_url,
        token=None,
        refresh=None,
        session=None,
        max_retries=3,
        sleep=time.sleep,
    ):
        if not token and not refresh:
            raise CanvasError("Provide an access token, or refresh credentials.")
        self.base_url = base_url.rstrip("/")
        self.refresh = refresh
        self.max_retries = max_retries
        self._sleep = sleep
        self.session = session or requests.Session()
        self.last_rate_limit = {}
        if token:
            self._set_token(token)

    @classmethod
    def from_env(cls, **kwargs):
        """Build a client from the environment (or a .env file).

        Needs CANVAS_BASE_URL plus either CANVAS_TOKEN, or all of CANVAS_CLIENT_ID,
        CANVAS_CLIENT_SECRET and CANVAS_REFRESH_TOKEN. With the refresh values
        set, the client gets a fresh access token whenever the old one expires.
        """
        load_env_file()
        base_url = os.environ.get("CANVAS_BASE_URL", "")
        token = os.environ.get("CANVAS_TOKEN", "")
        refresh = read_refresh_credentials()
        missing = [name for name, value in (("CANVAS_BASE_URL", base_url),) if not value]
        if not token and not refresh:
            missing.append("CANVAS_TOKEN")
        if missing:
            raise CanvasError(f"Set {', '.join(missing)} in .env (see .env.example).")
        if not base_url.startswith(("http://", "https://")):
            raise CanvasError("CANVAS_BASE_URL must start with https://")
        return cls(base_url, token or None, refresh, **kwargs)

    def get(self, path, **params):
        """GET one resource and return the decoded JSON."""
        return self._request("GET", self._url(path), params=params).json()

    def post(self, path, data=None):
        """POST form fields (Canvas style: {"assignment[name]": "x"}) and return the JSON."""
        return self._request("POST", self._url(path), data=data).json()

    def put(self, path, data=None):
        """PUT form fields and return the JSON."""
        return self._request("PUT", self._url(path), data=data).json()

    def delete(self, path):
        """DELETE a resource and return the JSON Canvas sends back."""
        return self._request("DELETE", self._url(path)).json()

    def get_all(self, path, per_page=100, **params):
        """GET a list endpoint and follow every `next` link in the Link header."""
        url = self._url(path)
        params = {**params, "per_page": per_page}
        items = []
        while url:
            response = self._request("GET", url, params=params)
            items.extend(response.json())
            url = response.links.get("next", {}).get("url")
            params = None  # the next link already carries the query string
        return items

    def _url(self, path):
        if path.startswith(("http://", "https://")):
            if not path.startswith(f"{self.base_url}/"):
                raise CanvasError(f"Refusing to send your token to another host: {path}")
            return path
        return f"{self.base_url}/{API_PREFIX}/{path.lstrip('/')}"

    def _set_token(self, token):
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _send(self, method, url, params, data):
        try:
            return self.session.request(
                method, url, params=params, data=data, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as err:
            raise CanvasError(f"Could not reach Canvas: {err}") from err

    def _post_refresh(self):
        data = {
            "grant_type": "refresh_token",
            "client_id": self.refresh.client_id,
            "client_secret": self.refresh.client_secret,
            "refresh_token": self.refresh.refresh_token,
        }
        try:
            # Plain requests.post: this call must not send the old Bearer token.
            return requests.post(
                f"{self.base_url}/{TOKEN_PATH}", data=data, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as err:
            raise CanvasError(f"Could not reach Canvas to refresh the token: {err}") from err

    def _refresh_access_token(self):
        """Exchange the refresh token for a new access token. Kept in memory only."""
        response = self._post_refresh()
        if not response.ok:
            raise CanvasAuthError(
                f"Could not refresh the token ({response.status_code}: {response.text[:200]}). "
                "The refresh token or client secret may be wrong, or the grant was revoked. "
                "Authorize again to get a new refresh token."
            )
        body = response.json()
        self._set_token(body["access_token"])
        new_refresh_token = body.get("refresh_token")
        if new_refresh_token and new_refresh_token != self.refresh.refresh_token:
            self.refresh.refresh_token = new_refresh_token
            print(
                "WARNING: Canvas issued a new refresh token. Update CANVAS_REFRESH_TOKEN "
                "in .env, because the old one may stop working.",
                file=sys.stderr,
            )

    def _remember_rate_limit(self, response):
        """Keep Canvas's quota headers so recipes can show them."""
        self.last_rate_limit = {
            "request_cost": response.headers.get("X-Request-Cost"),
            "rate_limit_remaining": response.headers.get("X-Rate-Limit-Remaining"),
        }

    def _request(self, method, url, params=None, data=None):
        attempt = 0
        refreshed = False
        if not self.session.headers.get("Authorization"):
            self._refresh_access_token()
            refreshed = True
        while True:
            response = self._send(method, url, params, data)
            self._remember_rate_limit(response)
            if is_rate_limited(response):
                if attempt >= self.max_retries:
                    raise CanvasRateLimitError(
                        f"Canvas throttled the request {attempt + 1} times. "
                        "Slow down and retry later."
                    )
                self._sleep(backoff_seconds(response, attempt))
                attempt += 1
                continue
            if self.refresh and not refreshed and is_rejected_token(response):
                self._refresh_access_token()
                refreshed = True
                continue
            raise_for_error(response)
            return response
