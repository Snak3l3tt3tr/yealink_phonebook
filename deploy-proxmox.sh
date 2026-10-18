#!/bin/bash
#
# Proxmox LXC Deployment Script for Phonebook Application
# Run this script on your Proxmox host to create and configure the LXC container
#
# Usage: ./deploy-proxmox.sh [hostname]
# Example: ./deploy-proxmox.sh phonebook
# If no hostname is provided, "phonebook" will be used
#
# This script leverages the community-scripts/ProxmoxVE project for storage
# and template detection: https://github.com/community-scripts/ProxmoxVE

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CT_HOSTNAME="${1:-phonebook}"              # Use CT_HOSTNAME to avoid conflicts with build.func
GITHUB_REPO="https://github.com/Snak3l3tt3tr/yealink_phonebook.git"
MEMORY=2048
SWAP=512
DISK_SIZE=8
CORES=2
NETWORK_BRIDGE="vmbr0"
APP_PORT=8000

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Proxmox LXC Deployment Script${NC}"
echo -e "${GREEN}Phonebook Application${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    echo -e "${RED}Error: This script must be run on a Proxmox host${NC}"
    exit 1
fi

# Download community-scripts helper functions
echo -e "${BLUE}Loading Proxmox helper functions...${NC}"
TEMP_BUILD_FUNC=$(mktemp)
trap "rm -f $TEMP_BUILD_FUNC" EXIT

if ! curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func -o "$TEMP_BUILD_FUNC"; then
    echo -e "${RED}Error: Failed to download helper functions${NC}"
    exit 1
fi

# Source the community-scripts build functions
source "$TEMP_BUILD_FUNC"

# Function to find next available container ID (cluster-wide)
find_next_ctid() {
    local start_id=100
    local max_id=999

    # Get list of all existing container IDs from all nodes in the cluster
    local existing_ids=$(pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | grep -oP '"vmid":\s*\K\d+' | sort -n || pct list | awk 'NR>1 {print $1}' | sort -n)

    for ((id=start_id; id<=max_id; id++)); do
        # Check if ID exists in the list
        if ! echo "$existing_ids" | grep -q "^${id}$"; then
            echo $id
            return
        fi
    done

    echo -e "${RED}Error: No available container IDs found between $start_id and $max_id${NC}" >&2
    exit 1
}

# Function to find available storage for containers (using community-scripts approach)
find_container_storage() {
    local storage=$(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 {print $1; exit}')

    if [ -z "$storage" ]; then
        echo -e "${RED}Error: No storage found that supports containers (rootdir content)${NC}" >&2
        echo -e "${YELLOW}Available storage:${NC}" >&2
        pvesm status >&2
        echo ""
        echo -e "${YELLOW}To enable container storage, you need to:${NC}" >&2
        echo -e "  1. Go to Proxmox UI: Datacenter → Storage → Add" >&2
        echo -e "  2. Or enable 'Container' content type on existing storage" >&2
        echo -e "  3. Common options: Directory, ZFS, LVM-Thin" >&2
        exit 1
    fi

    echo "$storage"
}

# Function to find Debian template (using community-scripts approach)
find_debian_template() {
    local template_storage=$(pvesm status -content vztmpl 2>/dev/null | awk 'NR>1 {print $1; exit}')

    if [ -z "$template_storage" ]; then
        template_storage="local"
    fi

    # Look for Debian template - the filename is in the first column
    local template=$(pveam list "$template_storage" 2>/dev/null | grep -i "debian.*standard" | head -1 | awk '{print $1}')

    if [ -z "$template" ]; then
        echo -e "${RED}Error: No Debian template found${NC}" >&2
        echo -e "${YELLOW}Available templates:${NC}" >&2
        pveam list "$template_storage" 2>/dev/null >&2
        echo ""
        echo -e "${YELLOW}To download Debian 12 template, run:${NC}" >&2
        echo -e "  pveam update" >&2
        echo -e "  pveam download ${template_storage} debian-12-standard_12.12-1_amd64.tar.zst" >&2
        exit 1
    fi

    # Template is already in format "storage:vztmpl/filename.tar.zst" from pveam list
    # Just need to ensure it has the storage prefix
    if [[ "$template" == *":"* ]]; then
        echo "$template"
    else
        echo "${template_storage}:vztmpl/${template}"
    fi
}

# Auto-detect configuration
CTID=$(find_next_ctid)
STORAGE=$(find_container_storage)
TEMPLATE=$(find_debian_template)

echo -e "${GREEN}Configuration:${NC}"
echo -e "  Container ID: ${BLUE}${CTID}${NC}"
echo -e "  Hostname: ${BLUE}${CT_HOSTNAME}${NC}"
echo -e "  Storage: ${BLUE}${STORAGE}${NC}"
echo -e "  Template: ${BLUE}${TEMPLATE}${NC}"
echo -e "  Memory: ${BLUE}${MEMORY}MB${NC}"
echo -e "  Disk: ${BLUE}${DISK_SIZE}GB${NC}"
echo -e "  Cores: ${BLUE}${CORES}${NC}"
echo ""

# Debug: Show the exact pct create command that will be run
echo -e "${BLUE}Running: pct create ${CTID} ${TEMPLATE} --hostname ${CT_HOSTNAME} ...${NC}"
echo ""

echo -e "${GREEN}Creating LXC container...${NC}"
pct create $CTID "$TEMPLATE" \
    --hostname "$CT_HOSTNAME" \
    --memory $MEMORY \
    --swap $SWAP \
    --cores $CORES \
    --rootfs $STORAGE:$DISK_SIZE \
    --net0 name=eth0,bridge=$NETWORK_BRIDGE,ip=dhcp \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1 \
    --ssh-public-keys /root/.ssh/authorized_keys 2>/dev/null || \
pct create $CTID "$TEMPLATE" \
    --hostname "$CT_HOSTNAME" \
    --memory $MEMORY \
    --swap $SWAP \
    --cores $CORES \
    --rootfs $STORAGE:$DISK_SIZE \
    --net0 name=eth0,bridge=$NETWORK_BRIDGE,ip=dhcp \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1

echo -e "${GREEN}Starting container...${NC}"
pct start $CTID

# Wait for container to be ready
echo -e "${BLUE}Waiting for container to boot...${NC}"
sleep 5

echo -e "${GREEN}Updating system packages...${NC}"
pct exec $CTID -- bash -c "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y"

echo -e "${GREEN}Installing required packages...${NC}"
pct exec $CTID -- bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    sqlite3 \
    sudo"

echo -e "${GREEN}Setting up root password for console access...${NC}"
pct exec $CTID -- bash -c "echo 'root:phonebook' | chpasswd"
echo -e "${YELLOW}Root password set to: phonebook (change this after login!)${NC}"

echo -e "${GREEN}Creating application user...${NC}"
pct exec $CTID -- bash -c "useradd -m -s /bin/bash phonebook || true"

echo -e "${GREEN}Creating application directory...${NC}"
pct exec $CTID -- bash -c "mkdir -p /opt/phonebook /opt/phonebook/data && chown -R phonebook:phonebook /opt/phonebook"

echo -e "${GREEN}Cloning application from GitHub...${NC}"
pct exec $CTID -- bash -c "cd /opt/phonebook && sudo -u phonebook git clone $GITHUB_REPO app"

echo -e "${GREEN}Setting up Python virtual environment...${NC}"
pct exec $CTID -- bash -c "cd /opt/phonebook/app && sudo -u phonebook python3 -m venv venv"

echo -e "${GREEN}Installing Python dependencies...${NC}"
pct exec $CTID -- bash -c "cd /opt/phonebook/app && sudo -u phonebook venv/bin/pip install --upgrade pip && sudo -u phonebook venv/bin/pip install -r backend/requirements.txt"

echo -e "${GREEN}Creating systemd service...${NC}"
pct exec $CTID -- bash -c 'cat > /etc/systemd/system/phonebook.service << EOF
[Unit]
Description=Phonebook Application
After=network.target

[Service]
Type=simple
User=phonebook
Group=phonebook
WorkingDirectory=/opt/phonebook/app/backend
Environment="DATABASE_URL=sqlite:////opt/phonebook/data/phonebook.db"
Environment="PYTHONPATH=/opt/phonebook/app/backend"
ExecStart=/opt/phonebook/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

echo -e "${GREEN}Creating update script...${NC}"
pct exec $CTID -- bash -c 'cat > /usr/local/bin/update << "EOF"
#!/bin/bash
#
# Update script for Phonebook application
# Pulls latest code from GitHub and restarts the service
#

set -e

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Phonebook Application Update${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

APP_DIR="/opt/phonebook/app"
BACKUP_DIR="/opt/phonebook/backups"
BACKUP_NAME="phonebook-$(date +%Y%m%d-%H%M%S).db"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Backup database
echo -e "${GREEN}Backing up database...${NC}"
mkdir -p "$BACKUP_DIR"
if [ -f "/opt/phonebook/data/phonebook.db" ]; then
    cp "/opt/phonebook/data/phonebook.db" "$BACKUP_DIR/$BACKUP_NAME"
    echo -e "${GREEN}Database backed up to: $BACKUP_DIR/$BACKUP_NAME${NC}"

    # Keep only last 10 backups
    cd "$BACKUP_DIR"
    ls -t phonebook-*.db | tail -n +11 | xargs -r rm
fi

# Stop service
echo -e "${GREEN}Stopping phonebook service...${NC}"
systemctl stop phonebook

# Pull latest code
echo -e "${GREEN}Pulling latest code from GitHub...${NC}"
cd "$APP_DIR"
sudo -u phonebook git fetch --all
sudo -u phonebook git reset --hard origin/main || sudo -u phonebook git reset --hard origin/master || sudo -u phonebook git reset --hard origin/develop

# Update dependencies
echo -e "${GREEN}Updating Python dependencies...${NC}"
sudo -u phonebook venv/bin/pip install --upgrade pip
sudo -u phonebook venv/bin/pip install -r backend/requirements.txt

# Start service
echo -e "${GREEN}Starting phonebook service...${NC}"
systemctl start phonebook

# Check status
sleep 2
if systemctl is-active --quiet phonebook; then
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Update completed successfully!${NC}"
    echo -e "${GREEN}======================================${NC}"
    systemctl status phonebook --no-pager
else
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}Error: Service failed to start${NC}"
    echo -e "${RED}======================================${NC}"
    echo -e "${YELLOW}Restoring database backup...${NC}"
    cp "$BACKUP_DIR/$BACKUP_NAME" "/opt/phonebook/data/phonebook.db"
    systemctl start phonebook
    exit 1
fi
EOF'

pct exec $CTID -- chmod +x /usr/local/bin/update

echo -e "${GREEN}Enabling and starting phonebook service...${NC}"
pct exec $CTID -- systemctl daemon-reload
pct exec $CTID -- systemctl enable phonebook
pct exec $CTID -- systemctl start phonebook

# Wait for service to start
sleep 5

# Get container IP
CONTAINER_IP=$(pct exec $CTID -- hostname -I | awk '{print $1}')

# Verify service is running
echo -e "${BLUE}Verifying deployment...${NC}"
if pct exec $CTID -- systemctl is-active --quiet phonebook; then
    echo -e "${GREEN}✓ Service is running${NC}"

    # Test if API is responding
    if pct exec $CTID -- curl -s http://localhost:8000/api | grep -q "ok"; then
        echo -e "${GREEN}✓ API is responding${NC}"
    else
        echo -e "${YELLOW}⚠ API test failed, but service is running${NC}"
    fi
else
    echo -e "${RED}✗ Service is not running!${NC}"
    echo -e "${YELLOW}Checking logs:${NC}"
    pct exec $CTID -- journalctl -u phonebook -n 20 --no-pager
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "Container ID: ${BLUE}$CTID${NC}"
echo -e "Hostname: ${BLUE}$CT_HOSTNAME${NC}"
echo -e "IP Address: ${BLUE}$CONTAINER_IP${NC}"
echo -e "Root Password: ${YELLOW}phonebook${NC} (please change!)"
echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo -e "  Web Frontend: ${BLUE}http://$CONTAINER_IP:$APP_PORT/${NC}"
echo -e "  API Docs: ${BLUE}http://$CONTAINER_IP:$APP_PORT/docs${NC}"
echo -e "  Yealink XML: ${BLUE}http://$CONTAINER_IP:$APP_PORT/yealink/phonebook.xml${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "  Update application: ${BLUE}pct exec $CTID -- update${NC}"
echo -e "  Check status: ${BLUE}pct exec $CTID -- systemctl status phonebook${NC}"
echo -e "  View logs: ${BLUE}pct exec $CTID -- journalctl -u phonebook -f${NC}"
echo -e "  Enter container: ${BLUE}pct enter $CTID${NC}"
echo ""
echo -e "${YELLOW}Troubleshooting:${NC}"
echo -e "  If frontend not accessible, check logs:"
echo -e "    ${BLUE}pct exec $CTID -- journalctl -u phonebook -n 50${NC}"
echo -e "  Check if service is running:"
echo -e "    ${BLUE}pct exec $CTID -- systemctl status phonebook${NC}"
echo -e "  Test API directly:"
echo -e "    ${BLUE}curl http://$CONTAINER_IP:$APP_PORT/api${NC}"
echo ""
echo -e "${GREEN}Configuration sourced from community-scripts/ProxmoxVE${NC}"
echo ""
