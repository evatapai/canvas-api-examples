import pytest

CANVAS_VARS = (
    "CANVAS_BASE_URL",
    "CANVAS_TOKEN",
    "CANVAS_CLIENT_ID",
    "CANVAS_CLIENT_SECRET",
    "CANVAS_REFRESH_TOKEN",
    "CANVAS_COURSE_ID",
    "CANVAS_ENROLL_USER_ID",
)


@pytest.fixture(autouse=True)
def clean_canvas_env(request, monkeypatch):
    """Mocked tests never see the developer's real Canvas settings.

    Live tests are the exception: they need those settings.
    """
    if request.node.get_closest_marker("live"):
        return
    for name in CANVAS_VARS:
        monkeypatch.delenv(name, raising=False)
