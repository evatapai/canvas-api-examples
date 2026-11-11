"""Opt-in tests against a real Canvas account: pytest -m live

They use the settings in .env (or the environment). The recipes that change data
only run when CANVAS_COURSE_ID is set, and they clean up after themselves.
"""

import importlib
import os

import pytest

from canvaslib.client import CanvasClient, load_env_file

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    return CanvasClient.from_env()


@pytest.fixture
def demo_course():
    load_env_file()
    if not os.environ.get("CANVAS_COURSE_ID"):
        pytest.skip("Set CANVAS_COURSE_ID to a demo course to run recipes that change data")


@pytest.fixture
def demo_student(demo_course):
    if not os.environ.get("CANVAS_ENROLL_USER_ID"):
        pytest.skip("Set CANVAS_ENROLL_USER_ID to a demo user to run the enrollment recipe")


def recipe(name):
    return importlib.import_module(f"recipes.{name}")


def test_auth_recipe(client):
    assert recipe("01_auth").run(client)["id"]


def test_list_courses_recipe(client):
    assert isinstance(recipe("02_list_courses").run(client), list)


def test_assignment_recipe(client, demo_course):
    result = recipe("03_assignment_and_grade").run(client)
    assert result["score"] == 9.0
    assert result["grade"] == "9"


def test_file_upload_recipe(client, demo_course):
    result = recipe("04_file_upload").run(client)
    assert result["content_type"] == "text/plain"
    assert result["size"] == len(recipe("04_file_upload").FILE_BYTES)


def test_errors_recipe(client):
    result = recipe("05_errors_and_limits").run(client)
    assert "rejected the token" in result["invalid_token"]
    assert result["quota_after_one_call"]["rate_limit_remaining"]


def test_enroll_recipe(client, demo_student):
    result = recipe("06_enroll_and_roster").run(client)
    assert any("StudentEnrollment" in user["roles"] for user in result["roster"])


def test_module_recipe(client, demo_course):
    result = recipe("07_module_with_items").run(client)
    assert [item["type"] for item in result["items"]] == ["SubHeader", "Page", "ExternalUrl"]


def test_discussion_recipe(client, demo_course):
    result = recipe("08_discussion_topic").run(client)
    assert result["thread"][0]["replies"][0]["message"] == "Great, welcome!"
