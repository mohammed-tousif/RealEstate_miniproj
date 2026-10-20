from decimal import Decimal

from tests.conftest import create_listing, listing_payload, locality_id

API = "/api/v1/properties"


def test_buyer_cannot_create_listing(client, buyer_h):
    r = client.post(API, json=listing_payload(), headers=buyer_h)
    assert r.status_code == 403


def test_guest_cannot_create_listing(client):
    assert client.post(API, json=listing_payload()).status_code == 401


def test_seller_listing_is_pending_and_hidden_until_approved(client, seller_h, seller_b_h, admin_h):
    prop = create_listing(client, seller_h)
    assert prop["listing_status"] == "pending"
    assert prop["normalized_area_sqft"] == "1200.0000"
    assert prop["is_synthetic"] is False and prop["is_owner"] is True
    # Hidden from guests, other sellers and search; visible to owner and admin.
    assert client.get(f"{API}/{prop['id']}").status_code == 404
    assert client.get(f"{API}/{prop['id']}", headers=seller_b_h).status_code == 404
    assert client.get(f"{API}/{prop['id']}", headers=seller_h).status_code == 200
    assert client.get(f"{API}/{prop['id']}", headers=admin_h).status_code == 200
    assert client.get(API).json()["total"] == 0
    mine = client.get(API, params={"mine": True}, headers=seller_h).json()
    assert mine["total"] == 1 and mine["items"][0]["listing_status"] == "pending"
    # Approval publishes it.
    client.post(f"/api/v1/admin/properties/{prop['id']}/approve", headers=admin_h)
    assert client.get(f"{API}/{prop['id']}").status_code == 200
    assert client.get(API).json()["total"] == 1


def test_area_unit_normalisation_on_create(client, seller_h):
    prop = create_listing(client, seller_h, property_type="agricultural_land", area_value="2.25", area_unit="acre",
                          land_classification="agricultural", conversion_status="not_applicable",
                          layout_approval_status="not_applicable", plot_width_ft=None, plot_length_ft=None,
                          intended_land_use="agricultural")
    assert Decimal(prop["normalized_area_sqft"]) == Decimal("98010")
    assert prop["area_unit"] == "acre" and Decimal(prop["area_value"]) == Decimal("2.25")


def test_validation_errors(client, seller_h):
    cases = [
        {"asking_price_inr": "-10"},
        {"asking_price_inr": "12.345"},
        {"area_value": "0"},
        {"area_unit": "hectare"},
        {"property_type": "industrial"},
        {"consent_to_store": False},
        {"latitude": "15.4", "longitude": None},
        {"title": "abc"},
        {"documents": [{"document_type": "khata", "availability": "provided"},
                       {"document_type": "khata", "availability": "not_provided"}]},
    ]
    for override in cases:
        r = client.post(API, json=listing_payload(**override), headers=seller_h)
        assert r.status_code == 422, (override, r.text)
        assert r.json()["error"]["code"] == "validation_error"


def test_business_validation(client, seller_h):
    assert client.post(API, json=listing_payload(locality_id=99999), headers=seller_h).status_code == 422
    assert client.post(API, json=listing_payload(amenities=["helipad"]), headers=seller_h).status_code == 422
    r = client.post(API, json=listing_payload(latitude="28.6139", longitude="77.2090"), headers=seller_h)
    assert r.status_code == 422 and "outside" in r.json()["error"]["message"]


def test_only_owner_can_edit_and_edit_resubmits(client, seller_h, seller_b_h, admin_h):
    prop = create_listing(client, seller_h, approve_with=admin_h)
    assert prop["listing_status"] == "approved"
    # Other seller gets 403 (listing is public, so it is not hidden).
    r = client.patch(f"{API}/{prop['id']}", json={"asking_price_inr": "1.00"}, headers=seller_b_h)
    assert r.status_code == 403
    r = client.patch(f"{API}/{prop['id']}", json={"asking_price_inr": "1900000", "area_value": "111.48",
                                                  "area_unit": "sqm"}, headers=seller_h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["listing_status"] == "pending"
    assert body["asking_price_inr"] == "1900000.00"
    assert Decimal(body["normalized_area_sqft"]) == Decimal("1199.9607")  # 111.48 x 10.7639104
    assert client.patch(f"{API}/{prop['id']}", json={"title": None}, headers=seller_h).status_code == 400


def test_archive_hides_listing(client, seller_h, admin_h):
    prop = create_listing(client, seller_h, approve_with=admin_h)
    assert client.delete(f"{API}/{prop['id']}", headers=seller_h).status_code == 204
    assert client.get(f"{API}/{prop['id']}").status_code == 404
    assert client.get(API).json()["total"] == 0
    r = client.patch(f"{API}/{prop['id']}", json={"title": "Changed title"}, headers=seller_h)
    assert r.status_code == 409


def _seed_variety(client, seller_h, admin_h):
    specs = [
        dict(title="Cheap plot Saptapur", asking_price_inr="900000", area_value="600"),
        dict(title="Mid plot Kalyan", asking_price_inr="2400000", area_value="1500",
             locality_id=locality_id("Kalyan Nagar"), road_access="main_road"),
        dict(title="Big plot Vidyanagar", asking_price_inr="5200000", area_value="2400",
             locality_id=locality_id("Vidyanagar"), latitude="15.369000", longitude="75.129000",
             documents=[{"document_type": "khata", "availability": "provided"}]),
        dict(title="Farm near Garag", property_type="agricultural_land", asking_price_inr="3000000",
             area_value="2", area_unit="acre", land_classification="agricultural",
             conversion_status="not_applicable", layout_approval_status="not_applicable",
             intended_land_use="agricultural", plot_width_ft=None, plot_length_ft=None,
             locality_id=locality_id("Garag"), latitude="15.565000", longitude="74.932000", road_access="unpaved"),
        dict(title="Shop plot Gokul Road", property_type="commercial_plot", asking_price_inr="8000000",
             area_value="2400", land_classification="non_agricultural_commercial", intended_land_use="commercial",
             locality_id=locality_id("Gokul Road"), latitude="15.356000", longitude="75.096000",
             road_access="main_road"),
    ]
    return [create_listing(client, seller_h, approve_with=admin_h, **s) for s in specs]


def test_filters_sorting_and_pagination(client, seller_h, admin_h):
    _seed_variety(client, seller_h, admin_h)
    q = lambda **p: client.get(API, params=p).json()  # noqa: E731

    assert q()["total"] == 5
    assert [i["title"] for i in q(max_price=2500000)["items"]] == ["Mid plot Kalyan", "Cheap plot Saptapur"]
    assert q(min_price=2500000, max_price=6000000)["total"] == 2
    assert q(city="hubballi")["total"] == 2
    assert q(locality_id=locality_id("Garag"))["items"][0]["title"] == "Farm near Garag"
    assert q(property_type=["agricultural_land", "commercial_plot"])["total"] == 2
    assert q(land_classification="agricultural")["total"] == 1
    assert q(intended_land_use="commercial")["total"] == 1
    assert q(road_access="main_road")["total"] == 2
    assert q(min_area_sqft=2000, max_area_sqft=50000)["total"] == 2
    assert q(min_area_sqft=80000)["items"][0]["title"] == "Farm near Garag"
    assert q(has_document="khata")["items"][0]["title"] == "Big plot Vidyanagar"
    assert q(has_document="encumbrance_certificate")["total"] == 4
    assert q(layout_approval_status="approved_layout_claimed")["total"] == 4
    assert q(q="gokul")["total"] == 1
    assert q(is_synthetic=True)["total"] == 0

    prices = [Decimal(i["asking_price_inr"]) for i in q(sort="price_asc")["items"]]
    assert prices == sorted(prices)
    areas = [Decimal(i["normalized_area_sqft"]) for i in q(sort="area_desc")["items"]]
    assert areas == sorted(areas, reverse=True)

    p1, p2, p3 = (q(sort="price_asc", page=n, page_size=2) for n in (1, 2, 3))
    assert p1["total_pages"] == 3 and len(p3["items"]) == 1
    ids = [i["id"] for p in (p1, p2, p3) for i in p["items"]]
    assert len(set(ids)) == 5


def test_empty_results_and_bad_ranges(client):
    r = client.get(API, params={"max_price": 1})
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0
    assert client.get(API, params={"min_price": 500, "max_price": 100}).status_code == 400
    assert client.get(API, params={"page_size": 500}).status_code == 422
    assert client.get(API, params={"sort": "random"}).status_code == 422
    assert client.get(API, params={"property_type": "castle"}).status_code == 422
    assert client.get(f"{API}/not-a-uuid").status_code == 422


def test_non_admin_cannot_browse_by_status(client, buyer_h):
    assert client.get(API, params={"status": "pending"}, headers=buyer_h).status_code == 403
    assert client.get(API, params={"mine": True}).status_code == 401


def test_detail_contains_document_checklist_and_warnings(client, seller_h, admin_h):
    prop = create_listing(client, seller_h, approve_with=admin_h, conversion_status="unknown",
                          plot_length_ft="60", road_access="unknown")
    docs = {d["document_type"]: d for d in prop["documents"]}
    assert docs["rtc_pahani"]["display_status"] == "provided_unverified"
    assert docs["khata"]["display_status"] == "unknown"  # applicable but never declared
    assert "occupancy_certificate" not in docs  # not applicable to a vacant plot
    assert prop["documents_applicable"] == len([d for d in prop["documents"] if d["applicable"]])
    warnings = " ".join(prop["data_warnings"])
    assert "Conversion" in warnings and "dimensions" in warnings and "Road access" in warnings
    assert prop["distance_to_city_centre_km"] is not None


def test_document_declarations_never_become_verified_by_seller(client, seller_h, admin_h):
    prop = create_listing(client, seller_h, approve_with=admin_h)
    r = client.put(f"{API}/{prop['id']}/documents", headers=seller_h, json={"documents": [
        {"document_type": "khata", "availability": "provided"},
        {"document_type": "sale_deed", "availability": "not_provided"}]})
    assert r.status_code == 200
    body = r.json()
    docs = {d["document_type"]: d for d in body["documents"]}
    assert docs["khata"]["display_status"] == "provided_unverified"
    assert docs["sale_deed"]["display_status"] == "not_provided"
    assert body["listing_status"] == "pending"  # changes go back to review


def test_favorites(client, seller_h, admin_h, buyer_h):
    prop = create_listing(client, seller_h, approve_with=admin_h)
    pending = create_listing(client, seller_h)
    assert client.put(f"/api/v1/users/me/favorites/{prop['id']}", headers=buyer_h).status_code == 204
    assert client.put(f"/api/v1/users/me/favorites/{prop['id']}", headers=buyer_h).status_code == 204  # idempotent
    assert client.put(f"/api/v1/users/me/favorites/{pending['id']}", headers=buyer_h).status_code == 404
    favs = client.get("/api/v1/users/me/favorites", headers=buyer_h).json()
    assert [f["id"] for f in favs] == [prop["id"]]
    assert client.delete(f"/api/v1/users/me/favorites/{prop['id']}", headers=buyer_h).status_code == 204
    assert client.get("/api/v1/users/me/favorites", headers=buyer_h).json() == []


def test_meta_and_localities(client):
    meta = client.get("/api/v1/meta/enums").json()
    assert meta["enums"]["PropertyType"]["agricultural_land"] == "Agricultural land"
    assert meta["area_unit_sqft_factor"]["gunta"] == "1089"
    assert any(a["code"] == "borewell" for a in meta["amenities"])
    locs = client.get("/api/v1/localities", params={"city": "Dharwad"}).json()
    assert locs and all(l["city"] == "Dharwad" for l in locs)
    assert client.get("/api/v1/health").json()["database"] is True
