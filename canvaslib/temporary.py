"""Create something for a recipe and always delete it again."""

from contextlib import contextmanager


@contextmanager
def temporary(client, create_path, data, delete_path):
    """POST `data` to `create_path`, yield what Canvas created, then DELETE it.

    `delete_path` can use fields of the created object, for example
    "courses/5/modules/{id}". The delete runs even if the recipe fails halfway.
    """
    created = client.post(create_path, data=data)
    try:
        yield created
    finally:
        client.delete(delete_path.format(**created))
