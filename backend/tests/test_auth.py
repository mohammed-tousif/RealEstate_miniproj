def test_register_login_me(client):
    r = client.post("/api/v1/auth/register", json={"name": "New User", "email": "New@Test.example",
                                                   "password": "abcd1234", "role": "seller"})
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "new@test.example"
    token = r.json()["access_token"]
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["role"] == "seller"


def test_duplicate_email_conflict(client):
    body = {"name": "Dup", "email": "buyer@test.example", "password": "abcd1234"}
    r = client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


def test_weak_password_and_admin_self_registration_rejected(client):
    r = client.post("/api/v1/auth/register", json={"name": "X Y", "email": "x@test.example", "password": "short"})
    assert r.status_code == 422
    r = client.post("/api/v1/auth/register", json={"name": "X Y", "email": "x@test.example",
                                                   "password": "lettersonly"})
    assert r.status_code == 422
    r = client.post("/api/v1/auth/register", json={"name": "X Y", "email": "x@test.example",
                                                   "password": "abcd1234", "role": "admin"})
    assert r.status_code == 422


def test_wrong_password_and_unknown_user_same_error(client):
    a = client.post("/api/v1/auth/login", json={"email": "buyer@test.example", "password": "wrong-pass1"})
    b = client.post("/api/v1/auth/login", json={"email": "nobody@test.example", "password": "wrong-pass1"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


def test_protected_routes_require_valid_token(client):
    assert client.get("/api/v1/users/me").status_code == 401
    r = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "not_authenticated"


def test_preferences_round_trip(client, buyer_h):
    assert client.get("/api/v1/users/me/preferences", headers=buyer_h).json() is None
    body = {"maximum_budget": "2500000.00", "preferred_cities": ["Dharwad"], "objective": "long_term_appreciation",
            "investment_horizon_years": 5, "preferred_property_types": ["residential_plot"]}
    r = client.put("/api/v1/users/me/preferences", json=body, headers=buyer_h)
    assert r.status_code == 200
    got = client.get("/api/v1/users/me/preferences", headers=buyer_h).json()
    assert got["maximum_budget"] == "2500000.00" and got["preferred_cities"] == ["Dharwad"]
