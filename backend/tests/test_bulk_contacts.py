import csv
import io


def create_contact(client, name, phone1=None, phone2=None, phone3=None):
    response = client.post(
        "/api/contacts",
        json={
            "name": name,
            "phone1": phone1,
            "phone2": phone2,
            "phone3": phone3,
        },
    )
    assert response.status_code == 201
    return response.json()


def parse_csv(response):
    decoded = response.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(decoded)))


def test_export_returns_all_contacts_as_round_trip_csv(client):
    create_contact(client, "Müller, Anna", "+49 30 123", "100")
    create_contact(client, "Bob", "200", phone3="202")

    response = client.get("/api/contacts/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert parse_csv(response) == [
        {
            "name": "Müller, Anna",
            "phone1": "+49 30 123",
            "phone2": "100",
            "phone3": "",
        },
        {"name": "Bob", "phone1": "200", "phone2": "", "phone3": "202"},
    ]


def test_import_creates_contacts_and_returns_a_summary(client):
    csv_content = (
        "name,phone1,phone2,phone3\r\n"
        '"Müller, Anna",+49 30 123,100,\r\n'
        "Bob,200,,202\r\n"
    )

    response = client.post(
        "/api/contacts/import",
        files={"file": ("contacts.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_rows": 2,
        "created": 2,
        "updated": 0,
        "skipped": 0,
        "error_count": 0,
        "errors": [],
    }
    assert client.get("/api/contacts").json() == [
        {
            "id": 1,
            "name": "Müller, Anna",
            "phone1": "+49 30 123",
            "phone2": "100",
            "phone3": None,
        },
        {
            "id": 2,
            "name": "Bob",
            "phone1": "200",
            "phone2": None,
            "phone3": "202",
        },
    ]


def test_import_reports_validation_errors_by_csv_row_and_keeps_valid_rows(client):
    too_long_phone = "1" * 51
    csv_content = (
        "name,phone1\n"
        ",100\n"
        f"Invalid phone,{too_long_phone}\n"
        "Valid contact,300\n"
    )

    response = client.post(
        "/api/contacts/import",
        files={"file": ("contacts.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["total_rows"] == 3
    assert result["created"] == 1
    assert result["error_count"] == 2
    assert [error["row"] for error in result["errors"]] == [2, 3]
    assert "name" in result["errors"][0]["message"]
    assert "phone1" in result["errors"][1]["message"]
    assert [contact["name"] for contact in client.get("/api/contacts").json()] == [
        "Valid contact"
    ]


def test_import_skips_duplicate_names_case_insensitively_by_default(client):
    create_contact(client, "Alice", "100")

    response = client.post(
        "/api/contacts/import",
        files={"file": ("contacts.csv", "name,phone1\n alice ,999\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["skipped"] == 1
    contacts = client.get("/api/contacts").json()
    assert len(contacts) == 1
    assert contacts[0]["phone1"] == "100"


def test_import_can_update_duplicate_names(client):
    original = create_contact(client, "Alice", "100", "101")

    response = client.post(
        "/api/contacts/import?duplicate_strategy=update",
        files={"file": ("contacts.csv", "name,phone1,phone3\nALICE,999,303\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1
    updated = client.get(f"/api/contacts/{original['id']}").json()
    assert updated == {
        "id": original["id"],
        "name": "ALICE",
        "phone1": "999",
        "phone2": "101",
        "phone3": "303",
    }


def test_import_can_report_duplicate_names_as_row_errors(client):
    create_contact(client, "Alice", "100")

    response = client.post(
        "/api/contacts/import?duplicate_strategy=error",
        files={"file": ("contacts.csv", "name,phone1\nAlice,999\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["error_count"] == 1
    assert response.json()["errors"] == [
        {"row": 2, "name": "Alice", "message": "Duplicate contact name"}
    ]


def test_import_rejects_a_csv_without_the_required_name_header(client):
    response = client.post(
        "/api/contacts/import",
        files={"file": ("contacts.csv", "phone1,phone2\n100,101\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "CSV must contain a 'name' column"}
