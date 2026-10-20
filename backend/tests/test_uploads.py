import io

from app.core.config import get_settings
from tests.conftest import create_listing

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _upload(client, pid, headers, data, name="photo.png", ctype="image/png"):
    return client.post(f"/api/v1/properties/{pid}/images", headers=headers,
                       files={"file": (name, io.BytesIO(data), ctype)})


def test_image_upload_and_serving(client, seller_h, admin_h):
    p = create_listing(client, seller_h, approve_with=admin_h)
    r = _upload(client, p["id"], seller_h, PNG)
    assert r.status_code == 201, r.text
    url = r.json()["url"]
    assert url.startswith("/media/properties/") and url.endswith(".png") and "photo" not in url
    assert client.get(url).content == PNG
    detail = client.get(f"/api/v1/properties/{p['id']}").json()
    assert detail["cover_image_url"] == url and len(detail["images"]) == 1


def test_upload_rejects_spoofed_type_and_other_users(client, seller_h, seller_b_h, admin_h):
    p = create_listing(client, seller_h, approve_with=admin_h)
    r = _upload(client, p["id"], seller_h, b"<?php echo 'x'; ?>", name="evil.jpg", ctype="image/jpeg")
    assert r.status_code == 415
    assert _upload(client, p["id"], seller_b_h, PNG).status_code == 403
    assert _upload(client, p["id"], {}, PNG).status_code == 401


def test_upload_size_and_count_limits(client, seller_h, admin_h, monkeypatch):
    p = create_listing(client, seller_h, approve_with=admin_h)
    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (1024 * 1024 + 10)
    assert _upload(client, p["id"], seller_h, big).status_code == 413
    monkeypatch.setattr(get_settings(), "max_images_per_property", 2)
    assert _upload(client, p["id"], seller_h, PNG).status_code == 201
    assert _upload(client, p["id"], seller_h, PNG).status_code == 201
    assert _upload(client, p["id"], seller_h, PNG).status_code == 409
