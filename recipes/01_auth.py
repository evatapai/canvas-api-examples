"""Recipe 1: authenticate and call GET /api/v1/users/self."""

from canvaslib.runner import main

TITLE = "Authenticate and call GET /api/v1/users/self"
DESCRIPTION = (
    "Sends your access token as a Bearer header and asks Canvas who you are. "
    "If this works, your base URL and token are set up correctly."
)


def run(client):
    profile = client.get("users/self")
    return {"id": profile["id"], "name": profile["name"]}


if __name__ == "__main__":
    main(run)
