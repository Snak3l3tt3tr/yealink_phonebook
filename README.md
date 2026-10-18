# Phonebook

A lightweight web application for maintaining a phonebook with support for Yealink IP phones.

## Features

- 📝 Simple web interface for managing contacts
- 📞 Support for up to 3 phone numbers per contact
- 📱 XML export for Yealink IP phones
- 📥 CSV bulk import with validation, duplicate handling, and row-level errors
- 📤 CSV export of all contacts
- 🐳 Docker support for easy deployment
- 🔄 RESTful API
- 💾 SQLite database (no external database required)

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI - Modern, fast web framework
- SQLAlchemy - SQL toolkit and ORM
- SQLite - Lightweight database
- Uvicorn - ASGI server

**Frontend:**
- HTML5
- CSS3
- Vanilla JavaScript (no framework required)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/Snak3l3tt3tr/yealink_phonebook.git
cd yealink_phonebook
```

2. Start the application:
```bash
docker-compose up -d
```

3. Access the application:
- Web Interface: http://localhost:8681/
- API Documentation: http://localhost:8681/docs
- Yealink XML: http://localhost:8681/yealink/phonebook.xml

### Manual Setup

1. **Install Python dependencies:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Start the backend:**
```bash
python main.py
```

3. **Access the frontend:**
Open `frontend/index.html` in your browser, or serve it with a simple HTTP server:
```bash
cd frontend
python -m http.server 8080
```

Then access http://localhost:8080

## API Endpoints

### Contacts

- `GET /api/contacts` - List all contacts
- `GET /api/contacts/{id}` - Get a specific contact
- `POST /api/contacts` - Create a new contact
- `PUT /api/contacts/{id}` - Update a contact
- `DELETE /api/contacts/{id}` - Delete a contact
- `DELETE /api/contacts?confirm=DELETE%20ALL` - Delete every contact
- `POST /api/contacts/import` - Import a UTF-8 CSV file
- `GET /api/contacts/export.csv` - Download all contacts as CSV

## CSV Import and Export

Open the web interface and use **CSV Import and Export**. The CSV header uses
these field names:

```csv
name,phone1,phone2,phone3
Alice Smith,+974 5555 0100,100,
Bob Jones,200,,202
```

- `name` is required and may contain up to 255 characters.
- `phone1`, `phone2`, and `phone3` are optional and may contain up to 50
  characters each.
- Files must be UTF-8 encoded, use a `.csv` extension, and be no larger than
  2 MB.
- Only `name` is required in the header; omitted phone columns are left
  unchanged when an existing contact is updated.
- Empty phone cells clear those values when the corresponding column is
  present and the duplicate strategy is **update**.
- Blank rows are ignored. Valid rows are imported even when other rows have
  errors, and the web interface reports the original CSV row number for each
  problem.

Duplicate names are compared after trimming surrounding whitespace and without
regard to letter case. Choose one of these strategies in the web interface or
pass it as `duplicate_strategy` to the import endpoint:

| Strategy | Behavior |
|---|---|
| `skip` (default) | Keep the existing contact and count the row as skipped |
| `update` | Update the existing contact from columns present in the CSV |
| `error` | Keep the existing contact and report a row-level duplicate error |

The export contains `name,phone1,phone2,phone3` and can be imported again.
Database IDs are intentionally excluded.

## Maintenance

The web interface includes a **Maintenance** section with the live contact
count, CSV and Yealink XML downloads, Docker update and log commands, storage
guidance, and a **Delete All Contacts** action. The bulk-delete action requires
typing `DELETE ALL`; it cannot be undone, so download a CSV backup first.

Docker stores the SQLite database in the named `phonebook-data` volume. A
container rebuild keeps this volume, but deleting the volume erases the stored
contacts. The application has no built-in sign-in protection, so restrict
access with a firewall, VPN, or authenticated reverse proxy.

### Yealink Integration

- `GET /yealink/phonebook.xml` - Download the XML phonebook for Yealink IP phones

The XML matches the Yealink local-contact export structure. The existing
database fields map as follows: `phone1` is the office number, `phone2` is the
mobile number, and `phone3` is the other number. No database migration is
required.

Browsers download this endpoint as `contact.xml` because Yealink's local-contact
format has two top-level sections and cannot be rendered as strict XML. The file
body remains in the phone-compatible format.

## Yealink IP Phone Setup

1. Access your Yealink phone's web interface
2. Navigate to Directory → Remote Phone Book
3. For Docker, set the Remote URL to: `http://your-server:8681/yealink/phonebook.xml`
4. Save and the phonebook will sync automatically

## Development

### Project Structure

```
yealink_phonebook/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # Database configuration
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── index.html        # Main HTML page
│   ├── style.css         # Styles
│   └── app.js           # JavaScript application
├── .github/
│   └── workflows/       # CI/CD workflows
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests
```

## Windows Docker Deployment and Update

To deploy and open TCP port `8681` on every Windows Firewall profile, start
PowerShell as Administrator and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Deploy-Public.ps1
```

The script starts the Docker Compose service, creates an inbound firewall rule
for any remote address, and verifies `http://127.0.0.1:8681/api`. If the PC is
behind a router, also forward public TCP port `8681` to the PC's LAN address on
port `8681`. An ISP CGNAT connection requires a tunnel or a public server.

Run these commands in PowerShell from the folder where you want the project:

```powershell
git clone https://github.com/Snak3l3tt3tr/yealink_phonebook.git
Set-Location .\yealink_phonebook
docker compose up -d --build
docker compose ps
```

Open `http://localhost:8681/`. The Compose configuration deliberately uses the
same deployment identity as the existing Windows installation:

| Setting | Value |
|---|---|
| Compose project | `yealinkphonebook` |
| Service | `phonebook` |
| Image | `yealinkphonebook-phonebook` |
| Generated container | `yealinkphonebook-phonebook-1` |
| Port mapping | `8681:8000` |

The named Docker volume `phonebook-data` stores
the SQLite database independently of the container, so rebuilding the image
does not delete contacts.

Before updating an existing installation, make a consistent backup while the
application is stopped:

```powershell
Set-Location C:\path\to\yealink_phonebook
docker compose stop phonebook
$container = docker compose ps -a -q phonebook
docker cp "${container}:/data/phonebook.db" ".\phonebook-backup.db"
docker compose start phonebook
```

Then pull and rebuild:

```powershell
git pull
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8681/api
```

If the health request returns `status: ok`, open the web interface and import a
small CSV first. The feature does not require a database migration.

To restore the backup, stop the application before copying it back:

```powershell
docker compose stop phonebook
$container = docker compose ps -a -q phonebook
docker cp ".\phonebook-backup.db" "${container}:/data/phonebook.db"
docker compose start phonebook
```

### Database

The SQLite database is created automatically on first run. By default, it's stored as `phonebook.db` in the backend directory.

To use a different location, set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL=sqlite:////path/to/your/database.db
```

## Deployment to Proxmox LXC

### Automated Deployment (Recommended)

We provide an automated deployment script that creates and configures an LXC container with everything set up.

**Prerequisites:**

- Proxmox VE host
- Debian 12 LXC template downloaded
- Network configured (DHCP or static IP)

**Steps:**

1. **Run this one-liner on your Proxmox host:**

```bash
# Quick deployment with auto-detected container ID and default hostname "phonebook"
curl -fsSL https://raw.githubusercontent.com/Snak3l3tt3tr/yealink_phonebook/main/deploy-proxmox.sh | bash

# With custom hostname:
curl -fsSL https://raw.githubusercontent.com/Snak3l3tt3tr/yealink_phonebook/main/deploy-proxmox.sh | bash -s -- myphonebook
```

The script automatically finds the next available container ID (starting from 100).

**Note:** Make sure to:

- Update the branch name if you're not using `main` (could be `master` or `develop`)
- Update the `GITHUB_REPO` variable in [deploy-proxmox.sh](deploy-proxmox.sh) before committing to GitHub

The script will:

- Auto-detect the next available container ID (100-999)
- Create a new LXC container with Debian 12
- Install Python 3, git, and dependencies
- Clone your application from GitHub
- Set up a Python virtual environment
- Create a systemd service for auto-start
- Install an `update` command for easy updates
- Start the application automatically

4. **Access your application:**

```bash
# The script will display the container IP, for example:
# Application URL: http://192.168.1.100:8000
```

### Updating the Application

Inside the LXC container, we provide an `update` script that pulls the latest code and restarts the service:

**From the Proxmox host:**
```bash
# Replace CTID with your actual container ID
pct exec CTID -- update
```

**Or enter the container and run:**
```bash
# Replace CTID with your actual container ID
pct enter CTID
update
```

The update script will:

- Backup the current database
- Pull the latest code from GitHub (main/master branch)
- Update Python dependencies
- Restart the service
- Automatically rollback if the update fails

### Managing the Service

**Check service status:**
```bash
pct exec CTID -- systemctl status phonebook
```

**View logs:**
```bash
pct exec CTID -- journalctl -u phonebook -f
```

**Restart service:**
```bash
pct exec CTID -- systemctl restart phonebook
```

**Database backups location:**
```bash
# Backups are stored in: /opt/phonebook/backups/
pct exec CTID -- ls -lh /opt/phonebook/backups/
```

### Manual Deployment Options

If you prefer manual deployment or need a different setup:

#### Option 1: Docker in LXC

1. Create a new LXC container (Ubuntu 22.04 recommended)
2. Make it privileged or enable nesting: `Features → Nesting`
3. Install Docker in the container:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

4. Clone and run the application:
```bash
git clone https://github.com/Snak3l3tt3tr/yealink_phonebook.git
cd yealink_phonebook
docker-compose up -d
```

#### Option 2: Direct Installation

1. Create a new LXC container (Ubuntu 22.04)
2. Install Python:
```bash
apt update
apt install python3.11 python3-pip -y
```

3. Clone and setup:
```bash
git clone https://github.com/Snak3l3tt3tr/yealink_phonebook.git
cd yealink_phonebook/backend
pip install -r requirements.txt
```

4. Create a systemd service (`/etc/systemd/system/phonebook.service`):
```ini
[Unit]
Description=Phonebook API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/yealink_phonebook/backend
Environment="DATABASE_URL=sqlite:////var/lib/phonebook/phonebook.db"
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

5. Enable and start:
```bash
systemctl enable phonebook
systemctl start phonebook
```

## Environment Variables

- `DATABASE_URL` - Database connection string (default: `sqlite:///./phonebook.db`)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this project for any purpose.

## Support

For issues and questions, please use the GitHub issue tracker.
