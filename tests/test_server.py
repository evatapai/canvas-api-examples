from server import is_allowed_request


def test_allows_localhost_without_origin():
    assert is_allowed_request({"Host": "localhost:3000"}, port=3000)


def test_allows_same_origin_post():
    headers = {"Host": "127.0.0.1:3000", "Origin": "http://127.0.0.1:3000"}
    assert is_allowed_request(headers, port=3000)


def test_blocks_other_websites():
    headers = {"Host": "localhost:3000", "Origin": "https://evil.example.com"}
    assert not is_allowed_request(headers, port=3000)


def test_blocks_dns_rebinding_host():
    assert not is_allowed_request({"Host": "evil.example.com:3000"}, port=3000)


def test_static_files_are_an_allowlist_that_exists():
    from server import STATIC_FILES

    assert set(STATIC_FILES) == {"/styles.css", "/app.js"}
    for file, content_type in STATIC_FILES.values():
        assert file.is_file()
        assert content_type.endswith("charset=utf-8")
