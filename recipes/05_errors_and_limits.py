"""Recipe 5: handle 401 and 429 correctly."""

from canvaslib.client import CanvasAuthError, CanvasClient
from canvaslib.runner import main

TITLE = "Handle 401 and 429 errors"
DESCRIPTION = (
    "Sends a deliberately invalid token to see how a 401 looks, then shows the quota "
    "headers Canvas returns on a normal call. When Canvas throttles you (429), the "
    "client in canvaslib/client.py waits and retries on its own."
)


def explain_bad_token(base_url):
    """Return what the client says about an invalid token."""
    try:
        CanvasClient(base_url, "not-a-real-token").get("users/self")
    except CanvasAuthError as err:
        return str(err)
    return "Unexpected: Canvas accepted an invalid token."


def run(client):
    client.get("users/self")
    return {
        "invalid_token": explain_bad_token(client.base_url),
        "quota_after_one_call": client.last_rate_limit,
    }


if __name__ == "__main__":
    main(run)
