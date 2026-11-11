import importlib
from urllib.parse import parse_qs

import pytest
import responses

from canvaslib.client import CanvasClient, CanvasError
from canvaslib.runner import run_recipe
from recipes import discover

BASE = "https://canvas.example.com"


@pytest.fixture
def client():
    return CanvasClient(BASE, "test-token", sleep=lambda _: None)


def test_discover_finds_every_recipe():
    ids = [recipe["id"] for recipe in discover()]
    assert ids == [
        "01_auth",
        "02_list_courses",
        "03_assignment_and_grade",
        "04_file_upload",
        "05_errors_and_limits",
        "06_enroll_and_roster",
        "07_module_with_items",
        "08_discussion_topic",
    ]


@responses.activate
def test_auth_recipe_returns_id_and_name(client):
    responses.get(f"{BASE}/api/v1/users/self", json={"id": 1, "name": "Panda Student", "extra": "x"})
    result = importlib.import_module("recipes.01_auth").run(client)
    assert result == {"id": 1, "name": "Panda Student"}


@responses.activate
def test_list_courses_recipe_reads_every_page(client):
    page2 = f"{BASE}/api/v1/courses?page=2"
    responses.get(
        f"{BASE}/api/v1/courses",
        json=[{"id": 1, "name": "Biology 101", "course_code": "BIO101"}],
        headers={"Link": f'<{page2}>; rel="next"'},
    )
    responses.get(page2, json=[{"id": 2}])  # restricted course without a name
    result = importlib.import_module("recipes.02_list_courses").run(client)
    assert result == [
        {"id": 1, "name": "Biology 101", "course_code": "BIO101"},
        {"id": 2, "name": None, "course_code": None},
    ]


@responses.activate
def test_assignment_recipe_grades_test_student_and_cleans_up(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    responses.get(f"{BASE}/api/v1/courses/5/student_view_student", json={"id": 77, "name": "Test Student"})
    responses.post(f"{BASE}/api/v1/courses/5/assignments", json={"id": 9, "name": "Demo"})
    responses.put(f"{BASE}/api/v1/courses/5/assignments/9/submissions/77", json={"score": 9.0, "grade": "9"})
    responses.delete(f"{BASE}/api/v1/courses/5/assignments/9", json={"id": 9})

    result = importlib.import_module("recipes.03_assignment_and_grade").run(client)

    assert result == {"assignment": {"id": 9, "name": "Demo"}, "student": "Test Student", "score": 9.0, "grade": "9"}
    assert responses.calls[-1].request.method == "DELETE"


@responses.activate
def test_assignment_recipe_deletes_assignment_even_when_grading_fails(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    responses.get(f"{BASE}/api/v1/courses/5/student_view_student", json={"id": 77, "name": "Test Student"})
    responses.post(f"{BASE}/api/v1/courses/5/assignments", json={"id": 9, "name": "Demo"})
    responses.put(f"{BASE}/api/v1/courses/5/assignments/9/submissions/77", status=500, body="boom")
    responses.delete(f"{BASE}/api/v1/courses/5/assignments/9", json={"id": 9})

    with pytest.raises(CanvasError, match="500"):
        importlib.import_module("recipes.03_assignment_and_grade").run(client)
    assert responses.calls[-1].request.method == "DELETE"


@responses.activate
def test_upload_recipe_runs_all_three_steps_without_sending_the_token(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    upload_url = "https://uploads.example.net/bucket"
    responses.post(
        f"{BASE}/api/v1/courses/5/files",
        json={"upload_url": upload_url, "upload_params": {"key": "abc", "signature": "sig"}},
    )
    responses.post(upload_url, status=301, headers={"Location": f"{BASE}/api/v1/files/1234/create_success?uuid=U"})
    responses.get(
        f"{BASE}/api/v1/files/1234/create_success",
        json={"id": 1234, "display_name": "canvas-api-examples-demo.txt", "size": 36, "content-type": "text/plain"},
    )
    responses.delete(f"{BASE}/api/v1/files/1234", json={"id": 1234})

    result = importlib.import_module("recipes.04_file_upload").run(client)

    assert result["id"] == 1234
    step2 = responses.calls[1].request
    assert "Authorization" not in step2.headers
    assert b'name="key"' in step2.body and b'name="file"' in step2.body
    assert step2.body.rindex(b'name="file"') > step2.body.rindex(b'name="signature"')


@responses.activate
def test_upload_recipe_stops_when_the_upload_fails(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    responses.post(f"{BASE}/api/v1/courses/5/files", json={"upload_url": "https://uploads.example.net/b", "upload_params": {}})
    responses.post("https://uploads.example.net/b", status=403, body="signature expired")
    with pytest.raises(CanvasError, match="Upload failed"):
        importlib.import_module("recipes.04_file_upload").run(client)


@responses.activate
def test_errors_recipe_shows_401_message_and_quota(client):
    responses.get(
        f"{BASE}/api/v1/users/self",
        json={},
        headers={"X-Request-Cost": "0.1", "X-Rate-Limit-Remaining": "500"},
    )
    result = importlib.import_module("recipes.05_errors_and_limits").run(client)
    assert result["quota_after_one_call"]["rate_limit_remaining"] == "500"
    assert "Unexpected" in result["invalid_token"]  # the mock accepted the fake token


@responses.activate
def test_enroll_recipe_enrolls_demo_user_lists_roster_and_removes_enrollment(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    monkeypatch.setenv("CANVAS_ENROLL_USER_ID", "9")
    responses.get(f"{BASE}/api/v1/users/self", json={"id": 4, "name": "Demo Teacher"})
    responses.post(f"{BASE}/api/v1/courses/5/enrollments", json={"id": 31, "type": "StudentEnrollment"})
    responses.get(
        f"{BASE}/api/v1/courses/5/users",
        json=[
            {"id": 4, "name": "Demo Teacher", "enrollments": [{"type": "TeacherEnrollment"}]},
            {"id": 9, "name": "Demo Student", "enrollments": [{"type": "StudentEnrollment"}]},
        ],
    )
    responses.delete(f"{BASE}/api/v1/courses/5/enrollments/31", json={"id": 31})

    result = importlib.import_module("recipes.06_enroll_and_roster").run(client)

    assert result["roster"] == [
        {"id": 4, "name": "Demo Teacher", "roles": ["TeacherEnrollment"]},
        {"id": 9, "name": "Demo Student", "roles": ["StudentEnrollment"]},
    ]
    enroll_body = parse_qs(responses.calls[1].request.body)
    assert enroll_body["enrollment[user_id]"] == ["9"]
    assert enroll_body["enrollment[notify]"] == ["false"]
    delete_call = responses.calls[-1].request
    assert delete_call.method == "DELETE"
    assert "task=delete" in delete_call.url


@responses.activate
def test_enroll_recipe_refuses_to_enroll_the_tokens_own_user(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    monkeypatch.setenv("CANVAS_ENROLL_USER_ID", "4")
    responses.get(f"{BASE}/api/v1/users/self", json={"id": 4, "name": "Demo Teacher"})
    with pytest.raises(CanvasError, match="different user"):
        importlib.import_module("recipes.06_enroll_and_roster").run(client)
    assert len(responses.calls) == 1  # nothing was created


def test_enroll_recipe_needs_a_demo_user_id(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    with pytest.raises(CanvasError, match="CANVAS_ENROLL_USER_ID"):
        importlib.import_module("recipes.06_enroll_and_roster").run(client)


@responses.activate
def test_module_recipe_builds_items_then_deletes_module_before_page(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    responses.post(f"{BASE}/api/v1/courses/5/pages", json={"url": "demo-page", "title": "Demo page"})
    responses.post(f"{BASE}/api/v1/courses/5/modules", json={"id": 8, "name": "Demo module"})
    responses.post(f"{BASE}/api/v1/courses/5/modules/8/items", json={"id": 1})
    responses.get(
        f"{BASE}/api/v1/courses/5/modules/8/items",
        json=[
            {"position": 1, "type": "SubHeader", "title": "Start here"},
            {"position": 2, "type": "Page", "title": "Demo page"},
            {"position": 3, "type": "ExternalUrl", "title": "Canvas developer docs"},
        ],
    )
    responses.delete(f"{BASE}/api/v1/courses/5/modules/8", json={"id": 8})
    responses.delete(f"{BASE}/api/v1/courses/5/pages/demo-page", json={"url": "demo-page"})

    result = importlib.import_module("recipes.07_module_with_items").run(client)

    assert [item["type"] for item in result["items"]] == ["SubHeader", "Page", "ExternalUrl"]
    deletes = [c.request.url for c in responses.calls if c.request.method == "DELETE"]
    assert deletes == [f"{BASE}/api/v1/courses/5/modules/8", f"{BASE}/api/v1/courses/5/pages/demo-page"]
    page_item = parse_qs(responses.calls[3].request.body)
    assert page_item["module_item[page_url]"] == ["demo-page"]


@responses.activate
def test_module_recipe_still_deletes_the_page_when_module_creation_fails(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    responses.post(f"{BASE}/api/v1/courses/5/pages", json={"url": "demo-page", "title": "Demo page"})
    responses.post(f"{BASE}/api/v1/courses/5/modules", status=500, body="boom")
    responses.delete(f"{BASE}/api/v1/courses/5/pages/demo-page", json={})
    with pytest.raises(CanvasError, match="500"):
        importlib.import_module("recipes.07_module_with_items").run(client)
    assert responses.calls[-1].request.method == "DELETE"


@responses.activate
def test_discussion_recipe_posts_entry_and_reply_then_reads_thread(client, monkeypatch):
    monkeypatch.setenv("CANVAS_COURSE_ID", "5")
    topics = f"{BASE}/api/v1/courses/5/discussion_topics"
    responses.post(topics, json={"id": 12, "title": "Demo topic"})
    responses.post(f"{topics}/12/entries", json={"id": 100})
    responses.post(f"{topics}/12/entries/100/replies", json={"id": 101})
    responses.get(f"{topics}/12/entries", json=[{"id": 100, "message": "Entry"}])
    responses.get(f"{topics}/12/entries/100/replies", json=[{"id": 101, "message": "Reply"}])
    responses.delete(f"{topics}/12", json={"id": 12})

    result = importlib.import_module("recipes.08_discussion_topic").run(client)

    assert result == {
        "topic": "Demo topic",
        "thread": [{"message": "Entry", "replies": [{"message": "Reply", "replies": []}]}],
    }
    assert responses.calls[-1].request.method == "DELETE"


def test_run_recipe_returns_error_message_when_env_is_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_TOKEN", raising=False)
    result, error = run_recipe(lambda client: {})
    assert result is None
    assert "CANVAS_BASE_URL" in error
