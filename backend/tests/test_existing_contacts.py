def test_existing_contact_crud_still_works(client):
    created = client.post(
        "/api/contacts",
        json={"name": "Alice", "phone1": "100", "phone2": None, "phone3": None},
    )
    assert created.status_code == 201
    contact_id = created.json()["id"]

    updated = client.put(
        f"/api/contacts/{contact_id}",
        json={"name": "Alice Smith", "phone1": "101"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Alice Smith"
    assert updated.json()["phone1"] == "101"

    assert client.get(f"/api/contacts/{contact_id}").status_code == 200
    assert client.delete(f"/api/contacts/{contact_id}").status_code == 204
    assert client.get(f"/api/contacts/{contact_id}").status_code == 404


def test_yealink_xml_matches_phone_contact_export_and_escapes_attributes(client):
    client.post(
        "/api/contacts",
        json={
            "name": "R&D <Desk>",
            "phone1": '100&1"',
            "phone2": "1002",
            "phone3": "1003",
        },
    )

    response = client.get("/yealink/phonebook.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/octet-stream")
    assert response.headers["content-disposition"] == 'attachment; filename="contact.xml"'
    assert '<group display_name="All Contacts" />' in response.text
    assert '<group display_name="Blacklist" />' in response.text
    assert '<group display_name="Blocklist" ring="" />' in response.text
    assert response.text.count("<contact ") == 1
    assert 'display_name="R&amp;D &lt;Desk&gt;"' in response.text
    assert 'office_number="100&amp;1&quot;"' in response.text
    assert 'mobile_number="1002"' in response.text
    assert 'other_number="1003"' in response.text
    assert 'line="-1" ring="Auto" group_id_name="All Contacts"' in response.text


def test_web_ui_is_english_and_exposes_csv_import_and_export_controls(client):
    response = client.get("/")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "Add New Contact" in response.text
    assert "Office Number" in response.text
    assert "Mobile Number" in response.text
    assert "Other Number" in response.text
    assert "Import Contacts" in response.text
    assert "Export All Contacts" in response.text
    assert 'id="importForm"' in response.text
    assert 'id="duplicateStrategy"' in response.text
    assert 'href="/api/contacts/export.csv"' in response.text
    assert "Telefonbuch" not in response.text
