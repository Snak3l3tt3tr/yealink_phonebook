def test_login_protects_pages_and_contact_api(anonymous_client):
    page = anonymous_client.get("/", follow_redirects=False)
    assert page.status_code == 307
    assert page.headers["location"] == "/login.html"
    assert anonymous_client.get("/api/contacts").status_code == 401
    assert anonymous_client.get("/api").status_code == 200
    assert anonymous_client.get("/yealink/phonebook.xml").status_code == 200

    rejected = anonymous_client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert rejected.status_code == 401

    logged_in = anonymous_client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin"}
    )
    assert logged_in.status_code == 200
    assert logged_in.cookies.get("phonebook_session")
    assert "HttpOnly" in logged_in.headers["set-cookie"]
    assert "SameSite=strict" in logged_in.headers["set-cookie"]
    assert anonymous_client.get("/api/contacts").status_code == 200


def test_admin_can_change_password_and_old_sessions_are_invalidated(client):
    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "admin",
            "new_password": "new-secure-password",
            "confirm_password": "new-secure-password",
        },
    )
    assert changed.status_code == 200
    assert client.get("/api/contacts").status_code == 401

    old_password = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin"}
    )
    assert old_password.status_code == 401

    new_password = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "new-secure-password"},
    )
    assert new_password.status_code == 200


def test_login_and_password_management_controls_are_available(anonymous_client, client):
    login_page = anonymous_client.get("/login.html")
    assert login_page.status_code == 200
    assert 'id="loginForm"' in login_page.text
    assert 'id="username"' in login_page.text
    assert 'id="password"' in login_page.text

    app_page = client.get("/")
    assert app_page.status_code == 200
    assert 'id="logoutBtn"' in app_page.text
    assert 'id="changePasswordForm"' in app_page.text
    assert 'id="currentPassword"' in app_page.text
    assert 'id="newPassword"' in app_page.text
    assert 'id="confirmPassword"' in app_page.text
