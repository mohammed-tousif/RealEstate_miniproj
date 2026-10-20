"""Rule-based risk flags on the listing detail (M6)."""
from tests.conftest import create_listing


def codes(client, pid, headers=None):
    return {f["code"] for f in client.get(f"/api/v1/properties/{pid}", headers=headers).json()["risk_flags"]}


def test_missing_key_documents_and_access(client, seller_h, admin_h):
    p = create_listing(client, seller_h, approve_with=admin_h, documents=[], road_access="unknown",
                       conversion_status="not_converted")
    c = codes(client, p["id"])
    assert {"missing_key_documents", "road_access_unknown", "conversion_not_established"} <= c


def test_well_documented_listing_has_no_document_flag(client, seller_h, admin_h):
    docs = [{"document_type": t, "availability": "provided"} for t in
            ("rtc_pahani", "encumbrance_certificate", "sale_deed", "dc_conversion_order", "layout_approval")]
    p = create_listing(client, seller_h, approve_with=admin_h, documents=docs)
    c = codes(client, p["id"])
    assert "missing_key_documents" not in c and "road_access_unknown" not in c


def test_price_far_below_model_range_is_flagged(client, seller_h, admin_h):
    p = create_listing(client, seller_h, approve_with=admin_h, asking_price_inr="50000.00")
    assert "price_below_model_range" in codes(client, p["id"])


def test_unapproved_layout_and_no_access(client, seller_h, admin_h):
    p = create_listing(client, seller_h, approve_with=admin_h, layout_approval_status="unapproved_layout",
                       road_access="no_direct_access")
    assert {"unapproved_layout", "no_road_access"} <= codes(client, p["id"])
