#!/bin/bash

# Configuration
REPO_URL="https://github.com/SEU_USUARIO/infra_install.git"
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

git clone "$REPO_URL" "$INSTALL_DIR"
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to clone repository. Please check the URL.${NC}"
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
