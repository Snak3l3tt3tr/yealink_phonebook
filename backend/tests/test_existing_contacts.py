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


def test_yealink_xml_still_exports_each_number_and_escapes_text(client):
    client.post(
        "/api/contacts",
        json={
            "name": "R&D <Desk>",
            "phone1": "100&1",
            "phone2": "1002",
            "phone3": None,
        },
    )

    response = client.get("/yealink/phonebook.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert response.text.count("<DirectoryEntry>") == 2
    assert "<Name>R&amp;D &lt;Desk&gt;</Name>" in response.text
    assert "<Telephone>100&amp;1</Telephone>" in response.text


def test_web_ui_exposes_csv_import_and_export_controls(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="importForm"' in response.text
    assert 'id="duplicateStrategy"' in response.text
    assert 'href="/api/contacts/export.csv"' in response.text
