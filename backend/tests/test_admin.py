from app.core.config import get_settings
from tests.conftest import create_listing


def test_admin_routes_require_admin(client, buyer_h, seller_h):
    for h in (buyer_h, seller_h, {}):
        r = client.get("/api/v1/admin/properties/pending", headers=h)
        assert r.status_code in (401, 403)
    assert client.get("/api/v1/admin/stats", headers=seller_h).status_code == 403


def test_review_queue_and_actions(client, seller_h, admin_h):
    a = create_listing(client, seller_h)
    b = create_listing(client, seller_h, title="Second test plot")
    queue = client.get("/api/v1/admin/properties/pending", headers=admin_h).json()
    assert queue["total"] == 2
    assert "documentation_completeness" in queue["items"][0]

    assert client.post(f"/api/v1/admin/properties/{a['id']}/reject", headers=admin_h, json={}).status_code == 400
    r = client.post(f"/api/v1/admin/properties/{a['id']}/reject", headers=admin_h,
                    json={"reason": "Missing photos"})
    assert r.status_code == 200 and r.json()["listing_status"] == "rejected"
    # The owner sees why.
    mine = client.get(f"/api/v1/properties/{a['id']}", headers=seller_h).json()
    assert mine["review_reason"] == "Missing photos"

    r = client.post(f"/api/v1/admin/properties/{b['id']}/flag", headers=admin_h, json={"reason": "Check price"})
    assert r.json()["listing_status"] == "flagged"
    assert client.get("/api/v1/properties").json()["total"] == 0
    flagged = client.get("/api/v1/admin/properties", params={"status": "flagged"}, headers=admin_h).json()
    assert flagged["total"] == 1

    stats = client.get("/api/v1/admin/stats", headers=admin_h).json()
    assert stats["listings_by_status"] == {"rejected": 1, "flagged": 1}


def test_verified_status_blocked_without_process(client, seller_h, admin_h):
    p = create_listing(client, seller_h, approve_with=admin_h)
    url = f"/api/v1/admin/properties/{p['id']}/documents/verification"
    r = client.post(url, headers=admin_h, json={"document_type": "rtc_pahani", "verification_status": "verified",
                                                "verification_reference": "X-1"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "verification_unavailable"
    r = client.post(url, headers=admin_h, json={"document_type": "rtc_pahani", "verification_status": "pending"})
    assert r.status_code == 200
    docs = {d["document_type"]: d for d in r.json()["documents"]}
    assert docs["rtc_pahani"]["display_status"] == "verification_pending"
    # Not-provided documents cannot enter verification.
    r = client.post(url, headers=admin_h, json={"document_type": "khata", "verification_status": "pending"})
    assert r.status_code == 409


def test_verified_allowed_only_with_process_and_reference(client, seller_h, admin_h, monkeypatch):
    monkeypatch.setattr(get_settings(), "document_verification_process_enabled", True)
    p = create_listing(client, seller_h, approve_with=admin_h)
    url = f"/api/v1/admin/properties/{p['id']}/documents/verification"
    r = client.post(url, headers=admin_h, json={"document_type": "rtc_pahani", "verification_status": "verified"})
    assert r.status_code == 400
    r = client.post(url, headers=admin_h, json={"document_type": "rtc_pahani", "verification_status": "verified",
                                                "verification_reference": "Bhoomi check 2026-10-14"})
    assert r.status_code == 200
    docs = {d["document_type"]: d for d in r.json()["documents"]}
    assert docs["rtc_pahani"]["display_status"] == "verified"
