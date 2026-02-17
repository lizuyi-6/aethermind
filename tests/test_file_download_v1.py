import app


def test_file_download_not_found():
    client = app.app.test_client()
    resp = client.get("/api/v1/files/01ARZ3NDEKTSV4RRFFQ69G5FAV/download")
    assert resp.status_code == 404


def test_file_detail_not_found():
    client = app.app.test_client()
    resp = client.get("/api/v1/files/01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert resp.status_code == 404
