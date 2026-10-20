# PropWise AI API (v1)

Base path `/api/v1`. Interactive OpenAPI docs: `http://localhost:8000/docs`.

The examples below were captured from a real run against a freshly seeded demo database on 2026-10-18 (listing ids
differ between seeds). Long responses are shortened: `…` marks removed array items or truncated text.

## Conventions
- **Auth:** `Authorization: Bearer <access_token>` from `/auth/login` or `/auth/register`. Tokens last 120 minutes.
  The user's role is read from the database on every request, so a token cannot grant a role.
- **Money and area** are decimal strings (`"2500000"`, `"1200.0000"`), never floats. Prices are in INR.
- **Errors** always have one shape:
  ```json
  {"error": {"code": "not_found", "message": "Property not found", "details": []}}
  ```
  Validation errors list `{"field", "issue"}` in `details`. Status codes: 401 not signed in, 403 not allowed, 404 not
  found (also for listings the caller may not see), 409 conflict, 413 file too large, 415 unsupported file type,
  422 validation, 429 rate limited, 503 price model unavailable.
- **Visibility:** guests and buyers see only approved listings. Sellers also see their own; admins see everything.
- **Enums** are listed by `GET /meta/enums`, which is the single source the frontend uses.
- **Security headers** on every response: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `X-Frame-Options: DENY`.

## System

### `GET /health`
```json
{"status": "ok", "database": true, "environment": "development", "price_model_loaded": true, "llm_configured": false}
```
Render uses this as the API health check. `llm_configured` is false when no `ANTHROPIC_API_KEY` is set, in which case
the assistant answers in Basic search mode.

### `GET /model-info`
The saved price model's card: model name and version, training date, dataset hash, split sizes and all validation and
test metrics.
```json
{"price_model": {"model_name": "linear_regression", "model_label": "Linear Regression",
  "model_version": "20261014-f0c175ee-linear_regression", "trained_on_synthetic": true, "seed": 42,
  "split": {"method": "GroupShuffleSplit on near-duplicate group, 70/15/15", "train": 200, "validation": 44, "test": 44},
  "selection": "lowest validation MAE (INR) among trained models; test set used once, after selection",
  "test_metrics": {"linear_regression": {"n": 44, "mae_inr": 758786.9, "r2": 0.963, "mape": 0.152}, "…": "…"}}}
```

## Reference data

### `GET /meta/enums`
```json
{"enums": {"PropertyType": {"residential_plot": "Residential plot", "independent_house": "Independent house",
  "agricultural_land": "Agricultural land", "commercial_plot": "Commercial plot", "commercial_building": "Commercial building"},
  "RoadAccess": {"highway": "National/State highway frontage", "main_road": "Main road", "paved_internal": "Paved internal road",
  "unpaved": "Unpaved road / cart track", "no_direct_access": "No direct road access", "unknown": "Unknown"}, "…": "…"}}
```

### `GET /localities?city=Dharwad`
```json
[{"id": 21, "locality_name": "Amminabhavi", "city": "Dharwad", "district": "Dharwad", "state": "Karnataka",
  "center_lat": "15.530000", "center_lng": "75.070000", "coordinates_approximate": true}, "…"]
```

## Auth and account

### `POST /auth/register`
Buyers and sellers only; `role: "admin"` is rejected (admins are created with `scripts/create_admin.py`).
Passwords need 8+ characters with letters and digits.
```json
// request
{"name": "New Buyer", "email": "newbuyer@example.com", "password": "LongPassword1", "role": "buyer"}
// 201
{"access_token": "eyJhbGciOi…", "token_type": "bearer", "expires_in_minutes": 120,
 "user": {"id": "692ce33d-…", "name": "New Buyer", "email": "newbuyer@example.com", "role": "buyer", "created_at": "…"}}
```

### `POST /auth/login`
```json
// request
{"email": "buyer@demo.propwise.example", "password": "DemoPass123"}
// 200: same shape as register
// 401 on a wrong password
{"error": {"code": "not_authenticated", "message": "Incorrect email or password", "details": []}}
```
After 10 failed attempts in a minute for the same client and email, further attempts get 429 until the minute passes.

### `GET /users/me`
```json
{"id": "fb646491-…", "name": "Demo Buyer", "email": "buyer@demo.propwise.example", "role": "buyer", "created_at": "…"}
```

### `GET /users/me/preferences` · `PUT /users/me/preferences`
```json
{"maximum_budget": "2500000", "preferred_cities": ["Hubballi", "Dharwad"],
 "preferred_property_types": ["residential_plot"], "objective": "long_term_investment"}
```

### `GET /users/me/favorites` · `PUT /users/me/favorites/{id}` · `DELETE /users/me/favorites/{id}`
PUT and DELETE return 204. GET returns a list of listing summaries (the same shape as search results).

## Listings

### `GET /properties`
Filters: `q` (text), `city`, `locality_id`, `min_price`, `max_price`, `min_area_sqft`, `max_area_sqft`, and the
repeatable `property_type`, `land_classification`, `intended_land_use`, `layout_approval_status`, `conversion_status`,
`road_access` and `has_document`. `mine=true` lists the caller's own listings in any review status. Sorts: `newest`
(default), `oldest`, `price_asc`, `price_desc`, `area_asc`, `area_desc`. Pagination: `page`, `page_size` (default 12, max 50).

`GET /properties?city=Dharwad&property_type=residential_plot&max_price=2500000&sort=price_asc&page_size=2`
```json
{"page": 1, "page_size": 2, "total": 24, "total_pages": 12,
 "items": [{"id": "be33ac01-71e1-4453-a411-72ab845a284a",
   "title": "East-facing 30×40 ft residential plot in Amminabhavi", "property_type": "residential_plot",
   "land_classification": "non_agricultural_residential", "asking_price_inr": "865000.00",
   "area_value": "1200.0000", "area_unit": "sqft", "normalized_area_sqft": "1200.0000", "price_per_sqft_inr": "720.83",
   "road_access": "paved_internal", "locality": {"id": 21, "locality_name": "Amminabhavi", "city": "Dharwad", "…": "…"},
   "latitude": "15.527224", "longitude": "75.074946", "listing_status": "approved",
   "documentation_completeness": 0.3333, "documents_provided": 2, "documents_applicable": 7,
   "cover_image_url": null, "is_synthetic": true, "created_at": "2026-07-15T10:00:00"}, "…"],
 "applied_filters": {"max_price": "2500000", "city": "Dharwad", "property_type": ["residential_plot"], "sort": "price_asc", "page_size": 2}}
```

### `GET /properties/{id}`
The summary fields plus the full record, documents (with applicability for the property type and guidance), amenities,
data warnings and rule-based risk flags.
```json
{"id": "be33ac01-…", "…": "summary fields",
 "conversion_status": "converted_claimed", "layout_approval_status": "unknown",
 "plot_width_ft": "30.00", "plot_length_ft": "40.00", "road_frontage_ft": "30.00", "is_corner_plot": false,
 "data_source": "synthetic_generator_v1", "images": [],
 "documents": [{"document_type": "rtc_pahani", "label": "RTC / Pahani", "applicable": true, "availability": "provided",
   "verification_status": "unverified", "display_status": "provided_unverified", "display_label": "Provided – unverified",
   "guidance": "Record of Rights, Tenancy and Crops. … check it on the Karnataka Bhoomi land-records service."}, "…"],
 "amenities": ["…"], "distance_to_city_centre_km": "…", "data_warnings": [],
 "risk_flags": [{"code": "missing_key_documents", "severity": "high",
   "message": "Key documents not declared as provided: Encumbrance Certificate (EC), …"}]}
```
Risk flag codes: `missing_key_documents`, `conversion_not_established`, `unapproved_layout`, `no_road_access` (high);
`road_access_unknown`, `price_below_model_range` (medium); `price_above_model_range`, `no_location` (low).

### `POST /properties` (seller or admin)
New listings are stored as `pending`. `consent_to_store` must be true.
```json
// request
{"title": "Corner plot near Saptapur", "description": "East facing corner plot.", "property_type": "residential_plot",
 "locality_id": 21, "area_value": "1200", "area_unit": "sqft", "asking_price_inr": "2200000",
 "land_classification": "non_agricultural_residential", "conversion_status": "converted_claimed",
 "layout_approval_status": "approved_layout_claimed", "road_access": "paved_internal", "consent_to_store": true}
// 201: the listing detail with "listing_status": "pending", "is_synthetic": false, "data_source": "user_submitted"
```
Invalid enum values come back as 422 with the allowed values:
```json
{"error": {"code": "validation_error", "message": "Request validation failed", "details": [
  {"field": "road_access", "issue": "Input should be 'highway', 'main_road', 'paved_internal', 'unpaved', 'no_direct_access' or 'unknown'"}]}}
```

### `PATCH /properties/{id}` (owner or admin)
Partial update with the same validation; an owner's edit sends an approved listing back to `pending`.
```json
{"asking_price_inr": "2150000"}
```

### `PUT /properties/{id}/documents` (owner or admin)
Declares which documents the seller has. Declarations never set verification.
```json
{"documents": [{"document_type": "rtc_pahani", "availability": "provided"}]}
// 200: detail with "documents_provided": 1 and that document shown as "Provided – unverified"
```

### `POST /properties/{id}/images` (owner or admin; multipart field `file`)
JPEG, PNG or WebP, checked from the file bytes; 5 MB and 10 images per listing by default.
```json
{"id": 1, "url": "/media/properties/12486d63-…/3ea850fb55c04f8ab9438161c5657e0a.png", "ordering": 0}
```
`DELETE /properties/{id}/images/{image_id}` returns 204.

### `DELETE /properties/{id}` (owner or admin)
Archives the listing (204). It disappears from public search.

## Admin (admin role)

| Endpoint | Purpose |
|---|---|
| `GET /admin/properties?status=pending&page=1&page_size=20` | Review queue for any status, oldest first |
| `GET /admin/properties/pending` | Shortcut for the pending queue |
| `POST /admin/properties/{id}/approve` | Body optional: `{"reason": "Checked against the locality map."}` |
| `POST /admin/properties/{id}/reject` | Body required: `{"reason": "Location pin does not match the locality."}` |
| `POST /admin/properties/{id}/flag` | Body required: `{"reason": "Duplicate of an existing listing."}` |
| `POST /admin/properties/{id}/documents/verification` | Records `unverified`, `pending` or `not_applicable` |
| `GET /admin/stats` | Counts by status, type, city, origin and role |

Marking a document `verified` is refused while no authorised verification process exists:
```json
// request
{"document_type": "rtc_pahani", "verification_status": "verified"}
// 409
{"error": {"code": "verification_unavailable", "message": "No authorised document-verification process is configured, so documents cannot be marked verified. Use 'pending' to record that a review has started.", "details": []}}
```
`GET /admin/stats`:
```json
{"listings_by_status": {"approved": 275, "flagged": 6, "pending": 16, "rejected": 10},
 "listings_by_type": {"agricultural_land": 93, "commercial_building": 20, "commercial_plot": 30, "independent_house": 41, "residential_plot": 123},
 "listings_by_city": {"Dharwad": 155, "Hubballi": 152}, "listings_by_origin": {"genuine": 1, "synthetic": 306},
 "users_by_role": {"admin": 1, "buyer": 2, "seller": 3}, "total_listings": 307}
```
(One "genuine" listing here is the user-submitted example created above.)

## Price estimate

### `POST /predictions/price`
Either describe a property or pass an existing `property_id`.
```json
// request
{"locality_id": 21, "property_type": "residential_plot", "area_value": "1200", "area_unit": "sqft"}
// 200
{"predicted_asking_price_inr": "606300.00",
 "indicative_range_inr": {"low": "465000.00", "high": "796000.00", "nominal_coverage": 0.8, "measured_test_coverage": 0.841,
   "method": "empirical 10th–90th percentile of validation log-residuals"},
 "normalized_area_sqft": "1200.0000", "predicted_price_per_sqft": "505.25",
 "quoted_price_inr": null, "quoted_vs_estimate_pct": null, "quoted_position": null,
 "comparables": [{"id": "be33ac01-…", "title": "East-facing 30×40 ft residential plot in Amminabhavi", "asking_price_inr": "865000.00", "…": "…"}, "…"],
 "top_factors": [{"feature": "log_area_sqft", "description": "Natural log of the area in sq ft (after unit conversion)", "mae_increase_inr": "38014695"}, "…"],
 "model": {"name": "linear_regression", "label": "Linear Regression", "version": "20261014-f0c175ee-linear_regression", "trained_on_synthetic": true},
 "warnings": ["Demonstration model trained on synthetic data. Not a valuation.", "Road access is unknown; the model used a typical value.", "…"],
 "disclaimer": "Indicative estimate of an asking price from a demonstration model. It is not a valuation, …"}
```
With `{"property_id": "be33ac01-…"}` the response also compares the asking price:
`"quoted_price_inr": "865000.00", "quoted_vs_estimate_pct": 19.3, "quoted_position": "within_range"`.
Returns 503 if the saved model cannot be loaded.

## Recommendations and comparison

### `POST /recommendations`
```json
// request
{"max_budget": "2500000", "property_types": ["residential_plot"], "cities": ["Hubballi", "Dharwad"], "objective": "long_term_investment"}
// 200
{"results": [{"rank": 1,
   "property": {"id": "71bba52f-…", "title": "West-facing 40×60 ft residential plot in Garag", "asking_price_inr": "2220000.00", "…": "…"},
   "score": 94.75, "data_coverage": 1.0,
   "factors": [{"factor": "budget", "label": "Budget fit", "weight": 0.3, "score": 1.0, "contribution": 30.0, "data_known": 1.0}, "…"],
   "reasons": ["Budget fit: asking price is 89% of your maximum budget.", "Location: in Garag, Dharwad, your preferred city."],
   "tradeoffs": [], "missing_info": [],
   "verify_independently": ["Declared but not verified: RTC / Pahani, Encumbrance Certificate, sale deed, DC conversion order, layout approval. Check them with the issuing authority."],
   "price_check": {"position": "within_range", "estimate_inr": "2074000", "note": "Asking price is within the price model's indicative range. (Demonstration model; not a valuation.)"}}, "…"],
 "candidates_considered": "…", "matched": "…", "excluded": [{"reason": "…", "count": "…"}],
 "weights_used": {"…": "…"}, "factors_ignored": [], "notes": [], "engine_version": "weighted-v1",
 "score_label": "Suitability score for your stated preferences. It is not a probability of investment success and not a recommendation to buy."}
```
Other preference fields: `min_budget`, `budget_strict` (default true), `types_strict` (default true), `locality_ids`,
`location_strict`, `min_area_value` with `min_area_unit`, `area_strict`, and an `importance` setting per factor
(`very_important`, `important`, `somewhat`, `not_important`).

### `GET /recommendations/config`
All weights and scoring tables, as rendered on the Methodology page:
```json
{"engine_version": "weighted-v1",
 "default_weights": {"budget": 30, "location": 25, "purpose": 20, "connectivity": 15, "documentation": 10},
 "importance": {"very_important": 2.0, "important": 1.0, "somewhat": 0.5, "not_important": 0.0},
 "road_score": {"highway": 1.0, "main_road": 0.85, "paved_internal": 0.65, "unpaved": 0.35, "no_direct_access": 0.0, "unknown": 0.0},
 "location_scores": {"preferred_locality": 1.0, "preferred_city": 0.7, "other_city": 0.3},
 "purpose_base": {"build_house": {"residential_plot": 1.0, "…": "…"}, "…": "…"},
 "budget": {"sweet_spot_from": 0.6, "non_strict_overrun": 0.1}}
```

### `POST /properties/compare`
2–3 listings; with `preferences` each item also gets its match score and rank, or the strict requirement it fails.
```json
// request
{"property_ids": ["be33ac01-…", "0cd49460-…"], "preferences": {"max_budget": "2500000", "property_types": ["residential_plot"], "cities": ["Hubballi", "Dharwad"], "objective": "long_term_investment"}}
// 200
{"items": [{"property": {"id": "be33ac01-…", "…": "…"},
   "match": {"rank": 1, "score": 70.68, "data_coverage": 0.9, "factors": [{"factor": "budget", "score": 0.5767, "contribution": 17.3, "…": "…"}, "…"]},
   "excluded_reason": null}, "…"]}
```
A listing the caller cannot see gives 404 for the whole request.

### `GET /properties/{id}/similar`
```json
{"items": [{"property": {"id": "64870eda-…", "title": "West-facing 20×30 ft residential plot in Narayanpur", "…": "…"},
   "distance": 1.53, "similarities": ["Same type (residential plot)", "Same city (Dharwad)", "…"]}, "…"],
 "method": "k-nearest neighbours (Euclidean) on standardised log price, log area, approximate coordinates, road access and documentation, …"}
```

## Assistant

### `POST /ai/chat`
Optional auth (a signed-in seller can ask about their own pending listing). Rate limit: 12 requests per minute per
client (`AI_RATE_LIMIT_PER_MINUTE`), then 429.
```json
// request
{"message": "Residential plots in Dharwad under 25 lakh",
 "history": [{"role": "user", "content": "…"}, {"role": "assistant", "content": "…"}],
 "preferences": null}
// 200 (no API key configured)
{"answer": "24 listing(s) match residential plot in Dharwad up to ₹25 lakh; showing 5 (lowest price first):\n- [East-facing 30×40 ft residential plot in Amminabhavi](/properties/be33ac01-…) …",
 "mode": "basic_search", "tool_calls": ["search_properties"],
 "properties": [{"id": "be33ac01-…", "title": "East-facing 30×40 ft residential plot in Amminabhavi", "…": "…"}, "…"],
 "disclaimers": ["Demo listings are synthetic, not real properties or market prices.", "Not legal or financial advice. Verify documents with the issuing authority."],
 "grounded": true, "notice": null}
```
```json
// request
{"message": "What is an RTC?", "history": []}
// 200
{"answer": "**RTC / Pahani**: Record of Rights, Tenancy and Crops. Shows recorded owner, extent and land use in revenue records; check it on the Karnataka Bhoomi land-records service …",
 "mode": "basic_search", "tool_calls": ["explain_term"], "properties": [], "disclaimers": ["…"], "grounded": true, "notice": null}
```
- `mode` is `llm` when the Claude model wrote the answer, `basic_search` for the rule-based mode.
- `message` is 1–1000 characters; `history` at most 20 turns of 4000 characters; `preferences` takes the same shape as
  `POST /recommendations` and is used to explain rankings.
- `grounded: false` with a `notice` means the model's answer cited a listing no tool returned, so it was replaced by
  the rule-based answer.
- If the model call fails, the answer comes from Basic search mode with
  `"notice": "The AI assistant is unavailable right now, so this answer comes from Basic search mode."`
