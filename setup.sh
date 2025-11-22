#!/bin/bash

# Configuration
REPO_URL="https://github.com/lucasvnd/infra.git"
INSTALL_DIR="/opt/infra_installer"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}   Infrastructure Installer Bootstrap    ${NC}"
echo -e "${BLUE}=========================================${NC}"

# 1. Check Root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (sudo su)${NC}"
  exit 1
fi

# 2. Check for GitHub Token (for private repos)
if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "${RED}ERROR: GITHUB_TOKEN environment variable is required for private repository access${NC}"
  echo -e "${BLUE}Usage: GITHUB_TOKEN=your_token curl -sL ... | sudo -E bash${NC}"
  exit 1
fi

# 2. Install Dependencies
echo -e "\n${BLUE}➜ Installing dependencies...${NC}"
apt-get update -qq
apt-get install -y git python3 -qq
echo -e "${GREEN}✔ Dependencies installed${NC}"

# 3. Clone Repository
echo -e "\n${BLUE}➜ Fetching installation files...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo "Cleaning up previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# Clone using token authentication for private repo
REPO_WITH_TOKEN="https://${GITHUB_TOKEN}@github.com/lucasvnd/infra.git"
git clone "$REPO_WITH_TOKEN" "$INSTALL_DIR"
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to clone repository. Please check the token and URL.${NC}"
    exit 1
fi
echo -e "${GREEN}✔ Files downloaded${NC}"

# 4. Run Installer
echo -e "\n${BLUE}➜ Starting Python Installer...${NC}"
cd "$INSTALL_DIR"
python3 install.py

# 5. Cleanup
echo -e "\n${BLUE}➜ Cleaning up...${NC}"
cd /
rm -rf "$INSTALL_DIR"
echo -e "${GREEN}✔ Installation finished and temporary files removed.${NC}"
