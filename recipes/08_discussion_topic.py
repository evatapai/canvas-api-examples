"""Recipe 8: post and read a discussion topic with replies."""

from canvaslib.client import require_course_id
from canvaslib.runner import main
from canvaslib.temporary import temporary

TITLE = "Post and read a discussion topic with replies"
DESCRIPTION = (
    "Creates a threaded discussion topic in the course named by CANVAS_COURSE_ID, posts an entry "
    "and a reply to it, reads the entry and its replies back, then deletes the topic."
)
WRITES = True


def read_thread(client, topic_path):
    """Read top-level entries, then the replies of each one.

    These two endpoints read straight from the database, so a new post shows up
    at once. The /view endpoint is built by a background job and can lag behind,
    which makes it a poor fit for read-after-write.
    """
    return [
        {
            "message": entry["message"],
            "replies": [
                {"message": reply["message"], "replies": []}
                for reply in client.get_all(f"{topic_path}/entries/{entry['id']}/replies")
            ],
        }
        for entry in client.get_all(f"{topic_path}/entries")
    ]


def run(client):
    course_id = require_course_id()
    with temporary(
        client,
        f"courses/{course_id}/discussion_topics",
        data={
            "title": "Canvas API Examples: demo topic",
            "message": "What did you learn today?",
            "discussion_type": "threaded",
            "published": "true",
        },
        delete_path=f"courses/{course_id}/discussion_topics/{{id}}",
    ) as topic:
        topic_path = f"courses/{course_id}/discussion_topics/{topic['id']}"
        entry = client.post(f"{topic_path}/entries", data={"message": "I learned how the API works."})
        client.post(f"{topic_path}/entries/{entry['id']}/replies", data={"message": "Great, welcome!"})
        return {"topic": topic["title"], "thread": read_thread(client, topic_path)}


if __name__ == "__main__":
    main(run)
