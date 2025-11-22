#!/bin/bash
# Infrastructure Installer Bootstrap
# One-liner for private repository installation

REPO_OWNER="lucasvnd"
REPO_NAME="infra"
INSTALL_DIR="/opt/infra_installer"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}   Infrastructure Installer Bootstrap    ${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (sudo su)${NC}"
  exit 1
fi

# Request token
echo -e "\n${YELLOW}This installer requires a GitHub Personal Access Token.${NC}"
echo -e "${BLUE}Create one at: https://github.com/settings/tokens${NC}"
echo -e "${BLUE}Required permission: 'repo' (Full control of private repositories)${NC}\n"
read -p "Enter your GitHub Token: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "${RED}Token is required!${NC}"
  exit 1
fi

# Install dependencies
echo -e "\n${BLUE}➜ Installing dependencies...${NC}"
apt-get update -qq
apt-get install -y git python3 -qq
echo -e "${GREEN}✔ Dependencies installed${NC}"

# Clone repository
echo -e "\n${BLUE}➜ Fetching installation files...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo "Cleaning up previous installation..."
    rm -rf "$INSTALL_DIR"
fi

REPO_URL="https://${GITHUB_TOKEN}@github.com/${REPO_OWNER}/${REPO_NAME}.git"
git clone -q "$REPO_URL" "$INSTALL_DIR" 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to clone repository.${NC}"
    echo -e "${RED}Please verify:${NC}"
    echo -e "${RED}  1. Your token has 'repo' permission${NC}"
    echo -e "${RED}  2. You have access to ${REPO_OWNER}/${REPO_NAME}${NC}"
    exit 1
fi
echo -e "${GREEN}✔ Files downloaded${NC}"

# Run installer
echo -e "\n${BLUE}➜ Starting Python Installer...${NC}"
cd "$INSTALL_DIR"
python3 install.py

# Cleanup
echo -e "\n${BLUE}➜ Cleaning up...${NC}"
cd /
rm -rf "$INSTALL_DIR"
echo -e "${GREEN}✔ Installation finished and temporary files removed.${NC}"

