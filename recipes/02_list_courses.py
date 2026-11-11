"""Recipe 2: list your courses with full pagination."""

from canvaslib.runner import main

TITLE = "List courses with full pagination"
DESCRIPTION = (
    "Calls GET /api/v1/courses and follows the Link header until there are no "
    "more pages, so you get every course and not just the first 100."
)


def run(client):
    courses = client.get_all("courses", enrollment_state="active")
    return [
        {"id": c["id"], "name": c.get("name"), "course_code": c.get("course_code")}
        for c in courses
    ]


if __name__ == "__main__":
    main(run)
