"""Recipe 3: create an assignment, then grade a submission."""

from contextlib import contextmanager

from canvaslib.client import require_course_id
from canvaslib.runner import main

TITLE = "Create an assignment and grade a submission"
DESCRIPTION = (
    "Creates a published assignment in the course named by CANVAS_COURSE_ID, grades the "
    "course's Test Student on it (so no real student is touched), then deletes the assignment."
)
WRITES = True


@contextmanager
def temporary_assignment(client, course_id):
    """Create an assignment and always delete it again, even if grading fails."""
    assignment = client.post(
        f"courses/{course_id}/assignments",
        data={
            "assignment[name]": "Canvas API Examples: demo assignment",
            "assignment[points_possible]": 10,
            "assignment[grading_type]": "points",
            "assignment[submission_types][]": "online_text_entry",
            "assignment[published]": "true",
        },
    )
    try:
        yield assignment
    finally:
        client.delete(f"courses/{course_id}/assignments/{assignment['id']}")


def run(client):
    course_id = require_course_id()
    # Canvas creates the course's Test Student the first time you ask for it.
    student = client.get(f"courses/{course_id}/student_view_student")
    with temporary_assignment(client, course_id) as assignment:
        submission = client.put(
            f"courses/{course_id}/assignments/{assignment['id']}/submissions/{student['id']}",
            data={"submission[posted_grade]": "9"},
        )
        return {
            "assignment": {"id": assignment["id"], "name": assignment["name"]},
            "student": student["name"],
            "score": submission["score"],
            "grade": submission["grade"],
        }


if __name__ == "__main__":
    main(run)
