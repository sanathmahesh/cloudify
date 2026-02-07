#!/bin/bash

# Cloudify Quick Start Script
# This script helps you get started with Cloudify quickly

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  CLOUDIFY QUICK START                     ║"
echo "║        Automated Cloud Migration to Google Cloud         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠ Not running in virtual environment${NC}"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
    echo ""
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
    echo ""
else
    echo -e "${GREEN}✓ Running in virtual environment${NC}"
    echo ""
fi

# Install dependencies
echo -e "${CYAN}Installing dependencies...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Creating .env from template..."
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo ""
    echo -e "${YELLOW}⚠ Please edit .env and add your API keys:${NC}"
    echo "  - ANTHROPIC_API_KEY"
    echo "  - DEDALUS_API_KEY (optional)"
    echo ""
    read -p "Press Enter to continue after editing .env..."
else
    echo -e "${GREEN}✓ .env file found${NC}"
    echo ""
fi

# Check for configuration file
if [ ! -f migration_config.yaml ]; then
    echo -e "${YELLOW}⚠ migration_config.yaml not found${NC}"
    echo "Initializing configuration..."
    python migration_orchestrator.py init
    echo -e "${GREEN}✓ Configuration initialized${NC}"
    echo ""
    echo -e "${YELLOW}⚠ Please edit migration_config.yaml with your settings${NC}"
    echo ""
    read -p "Press Enter to continue after editing migration_config.yaml..."
else
    echo -e "${GREEN}✓ migration_config.yaml found${NC}"
    echo ""
fi

# Check prerequisites
echo -e "${CYAN}Checking prerequisites...${NC}"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}✗ gcloud CLI not found${NC}"
    echo "  Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
else
    echo -e "${GREEN}✓ gcloud CLI found${NC}"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "  Install from: https://docs.docker.com/get-docker/"
    exit 1
else
    echo -e "${GREEN}✓ Docker found${NC}"
fi

# Check Firebase (optional)
if ! command -v firebase &> /dev/null; then
    echo -e "${YELLOW}⚠ Firebase CLI not found (optional)${NC}"
    echo "  Install with: npm install -g firebase-tools"
else
    echo -e "${GREEN}✓ Firebase CLI found${NC}"
fi

echo ""

# Authenticate with GCP
echo -e "${CYAN}Checking GCP authentication...${NC}"
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo -e "${GREEN}✓ Already authenticated with GCP${NC}"
else
    echo -e "${YELLOW}⚠ Not authenticated with GCP${NC}"
    echo "Initiating GCP login..."
    gcloud auth login
    gcloud auth application-default login
    echo -e "${GREEN}✓ GCP authentication complete${NC}"
fi

echo ""

# Run migration
echo -e "${CYAN}Ready to run migration!${NC}"
echo ""
echo "Usage:"
echo "  1. Dry run (preview only):"
echo "     ${GREEN}python migration_orchestrator.py migrate --dry-run${NC}"
echo ""
echo "  2. Interactive mode:"
echo "     ${GREEN}python migration_orchestrator.py migrate --mode interactive${NC}"
echo ""
echo "  3. Automated mode:"
echo "     ${GREEN}python migration_orchestrator.py migrate --mode automated${NC}"
echo ""

read -p "Run migration now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${CYAN}Starting migration...${NC}"
    python migration_orchestrator.py migrate
else
    echo ""
    echo "Migration cancelled. Run manually when ready:"
    echo "  ${GREEN}python migration_orchestrator.py migrate${NC}"
fi

echo ""
echo -e "${GREEN}✓ Quick start complete!${NC}"
