from xml.etree import ElementTree


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


def test_clear_all_contacts_requires_confirmation(client):
    for name in ("Alice", "Bob"):
        client.post("/api/contacts", json={"name": name})

    unconfirmed = client.delete("/api/contacts")
    assert unconfirmed.status_code == 422
    assert len(client.get("/api/contacts").json()) == 2

    cleared = client.delete("/api/contacts", params={"confirm": "DELETE ALL"})
    assert cleared.status_code == 200
    assert cleared.json() == {"deleted": 2}
    assert client.get("/api/contacts").json() == []


def test_t33_remote_phonebook_matches_yealink_directory_structure(client):
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
    assert response.headers["content-type"].startswith("application/xml")
    assert "content-disposition" not in response.headers
    root = ElementTree.fromstring(response.content)
    assert root.tag == "YealinkIPPhoneDirectory"
    entries = root.findall("DirectoryEntry")
    assert len(entries) == 1
    assert entries[0].findtext("Name") == "R&D <Desk>"
    assert [node.text for node in entries[0].findall("Telephone")] == [
        '100&1"',
        "1002",
        "1003",
    ]
    assert "<YealinkIPPhoneDirectory>" in response.text
    assert response.text.count("<DirectoryEntry>") == 1
    assert "<Name>R&amp;D &lt;Desk&gt;</Name>" in response.text
    assert "<Telephone>100&amp;1&quot;</Telephone>" in response.text
    assert "<Telephone>1002</Telephone>" in response.text
    assert "<Telephone>1003</Telephone>" in response.text


def test_remote_phonebook_setup_file_uses_the_app_network_address(client):
    response = client.get(
        "/yealink/remote-phonebook.cfg",
        headers={"host": "192.168.128.10:8681"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert (
        "remote_phonebook.data.1.url = "
        "http://192.168.128.10:8681/yealink/phonebook.xml"
    ) in response.text
    assert "remote_phonebook.data.1.name = Company Phonebook" in response.text
    assert "features.remote_phonebook.enable = 1" in response.text
    assert "features.remote_phonebook.flash_time = 3600" in response.text


def test_yealink_local_contact_export_remains_available(client):
    client.post("/api/contacts", json={"name": "Alice", "phone1": "100"})

    response = client.get("/yealink/local-contacts.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/octet-stream")
    assert response.headers["content-disposition"] == 'attachment; filename="contact.xml"'
    assert '<group display_name="All Contacts" />' in response.text
    assert '<contact display_name="Alice" office_number="100"' in response.text


def test_web_ui_is_english_and_exposes_csv_import_and_export_controls(client):
    response = client.get("/")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "Add New Contact" in response.text
    assert "Office Number" in response.text
    assert "Mobile Number" in response.text
    assert "Other Number" in response.text
    assert "Phone Connection" in response.text
    assert "192.168.131.165" in response.text
    assert 'href="/yealink/remote-phonebook.cfg"' in response.text
    assert "Import Contacts" in response.text
    assert "Export All Contacts" in response.text
    assert 'id="importForm"' in response.text
    assert 'id="duplicateStrategy"' in response.text
    assert 'href="/api/contacts/export.csv"' in response.text
    assert 'id="maintenance-title"' in response.text
    assert 'id="maintenanceContactCount"' in response.text
    assert 'id="clearAllBtn"' in response.text
    assert 'href="/yealink/local-contacts.xml"' in response.text
    assert "Back up before updates" in response.text
    assert "requires an administrator login" in response.text
    assert "Telefonbuch" not in response.text
