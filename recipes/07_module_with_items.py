"""Recipe 7: build a module with items."""

from canvaslib.client import require_course_id
from canvaslib.runner import main
from canvaslib.temporary import temporary

TITLE = "Build a module with items"
DESCRIPTION = (
    "Creates a page and a module in the course named by CANVAS_COURSE_ID, adds a heading, the "
    "page and an external link to the module, lists the items, then deletes the module and the page."
)
WRITES = True


def add_item(client, course_id, module_id, **fields):
    data = {f"module_item[{name}]": value for name, value in fields.items()}
    return client.post(f"courses/{course_id}/modules/{module_id}/items", data=data)


def run(client):
    course_id = require_course_id()
    with temporary(
        client,
        f"courses/{course_id}/pages",
        data={
            "wiki_page[title]": "Canvas API Examples: demo page",
            "wiki_page[body]": "<p>Created by the Canvas API examples.</p>",
            "wiki_page[published]": "true",
        },
        delete_path=f"courses/{course_id}/pages/{{url}}",
    ) as page, temporary(
        client,
        f"courses/{course_id}/modules",
        data={"module[name]": "Canvas API Examples: demo module"},
        delete_path=f"courses/{course_id}/modules/{{id}}",
    ) as module:
        add_item(client, course_id, module["id"], title="Start here", type="SubHeader")
        add_item(client, course_id, module["id"], title=page["title"], type="Page", page_url=page["url"])
        add_item(
            client,
            course_id,
            module["id"],
            title="Canvas developer docs",
            type="ExternalUrl",
            external_url="https://developerdocs.instructure.com",
        )
        items = client.get_all(f"courses/{course_id}/modules/{module['id']}/items")
        return {
            "module": {"id": module["id"], "name": module["name"]},
            "items": [
                {"position": item["position"], "type": item["type"], "title": item["title"]}
                for item in items
            ],
        }


if __name__ == "__main__":
    main(run)
