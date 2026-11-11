"""Recipe 6: enroll a user and list the course roster."""

from canvaslib.client import CanvasError, require_course_id, require_enroll_user_id
from canvaslib.runner import main
from canvaslib.temporary import temporary

TITLE = "Enroll a user and list the roster"
DESCRIPTION = (
    "Enrolls the demo user named by CANVAS_ENROLL_USER_ID as a Student in the course named by "
    "CANVAS_COURSE_ID (without sending any email), lists everyone in the course with their "
    "roles, then removes that enrollment again."
)
WRITES = True


def summarize(user):
    roles = {enrollment["type"] for enrollment in user.get("enrollments", [])}
    return {"id": user["id"], "name": user["name"], "roles": sorted(roles)}


def check_not_yourself(client, user_id):
    """Canvas does not let you remove your own enrollment, so the run could not clean up."""
    if str(client.get("users/self")["id"]) == user_id:
        raise CanvasError("CANVAS_ENROLL_USER_ID must be a different user than the token's user.")


def run(client):
    course_id = require_course_id()
    user_id = require_enroll_user_id()
    check_not_yourself(client, user_id)
    with temporary(
        client,
        f"courses/{course_id}/enrollments",
        data={
            "enrollment[user_id]": user_id,
            "enrollment[type]": "StudentEnrollment",
            "enrollment[enrollment_state]": "active",
            "enrollment[notify]": "false",
        },
        delete_path=f"courses/{course_id}/enrollments/{{id}}?task=delete",
    ) as enrollment:
        users = client.get_all(f"courses/{course_id}/users", **{"include[]": "enrollments"})
        return {
            "enrollment": {"id": enrollment["id"], "type": enrollment["type"]},
            "roster": [summarize(user) for user in users],
        }


if __name__ == "__main__":
    main(run)
