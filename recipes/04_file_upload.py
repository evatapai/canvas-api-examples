"""Recipe 4: upload a file with Canvas's three-step flow."""

from urllib.parse import urljoin

import requests

from canvaslib.client import CanvasError, require_course_id
from canvaslib.runner import main

TITLE = "Upload a file (three steps)"
DESCRIPTION = (
    "Tells Canvas about the file, sends the bytes to the upload URL Canvas gives you "
    "(without your token), then confirms with Canvas. The file is deleted afterwards."
)
WRITES = True

FILE_NAME = "canvas-api-examples-demo.txt"
FILE_BYTES = b"Hello from the Canvas API examples.\n"
UPLOAD_TIMEOUT_SECONDS = 60


def start_upload(client, course_id):
    """Step 1: tell Canvas the file name and size. It answers with where to send the bytes."""
    return client.post(
        f"courses/{course_id}/files",
        data={
            "name": FILE_NAME,
            "size": len(FILE_BYTES),
            "content_type": "text/plain",
            "on_duplicate": "rename",  # never replace a file that already exists
        },
    )


def post_file_bytes(upload):
    try:
        # Send every upload_params field unchanged, and the file last.
        # Never send your Canvas token to this URL: it is often a different service.
        return requests.post(
            upload["upload_url"],
            data=upload["upload_params"],
            files={"file": (FILE_NAME, FILE_BYTES)},
            allow_redirects=False,
            timeout=UPLOAD_TIMEOUT_SECONDS,
        )
    except requests.RequestException as err:
        raise CanvasError(f"Could not send the file to the upload URL: {err}") from err


def send_file(upload):
    """Step 2: POST the bytes. Success is a redirect or 201, with a Location to confirm."""
    response = post_file_bytes(upload)
    location = response.headers.get("Location")
    if response.status_code not in (201, 301, 302, 303) or not location:
        raise CanvasError(f"Upload failed ({response.status_code}): {response.text[:300]}")
    return location


def confirm_upload(client, location):
    """Step 3: GET the Location from Canvas, with your token. The file stays pending without it."""
    return client.get(urljoin(client.base_url + "/", location))


def run(client):
    course_id = require_course_id()
    upload = start_upload(client, course_id)
    location = send_file(upload)
    uploaded = confirm_upload(client, location)
    client.delete(f"files/{uploaded['id']}")
    return {
        "id": uploaded["id"],
        "display_name": uploaded["display_name"],
        "size": uploaded["size"],
        "content_type": uploaded["content-type"],
    }


if __name__ == "__main__":
    main(run)
