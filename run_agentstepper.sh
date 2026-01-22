#!/bin/bash
#set -euo pipefail

# =============================
# CLI Colors & Helpers (style)
# =============================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# =============================
# Config (override via env vars)
# =============================
VENV_DIR="${VENV_DIR:-.venv}"

# Docker image & container settings
UI_DIR="${UI_DIR:-AgentStepper UI}"                         # path to the UI folder (spaces ok)
UI_DOCKERFILE="${UI_DOCKERFILE:-${UI_DIR}/Dockerfile}"      # path to the Dockerfile
UI_IMAGE_TAG="${UI_IMAGE_TAG:-agentstepper-ui:latest}"      # docker image tag
UI_CONTAINER_NAME="${UI_CONTAINER_NAME:-agentstepper-ui}"   # docker container name
UI_CONTAINER_PORT="${UI_CONTAINER_PORT:-80}"                # container port (Nginx default)
UI_HOST_PORT="${UI_HOST_PORT:-3000}"                        # host port to expose
UI_HOST_BIND="${UI_HOST_BIND:-0.0.0.0}"                     # bind on all interfaces by default

# =============================
# Welcome
# =============================
clear
print_msg "${BLUE}" "=== AgentStepper LLM Agent Debugger: Core & UI Start Script ==="
echo

# =============================
# Check prerequisites: python3 + pip
# =============================
if ! command -v python3 >/dev/null 2>&1; then
    print_msg "${RED}" "Error: python3 is not installed or not on PATH."
    exit 1
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
    print_msg "${RED}" "Error: pip for python3 is not available. Please install python3-pip."
    exit 1
fi
print_msg "${GREEN}" "Found python3 and pip."
echo

# =============================
# Virtualenv
# =============================
if [ ! -d "$VENV_DIR" ]; then
    print_msg "${YELLOW}" "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR" || { print_msg "${RED}" "Failed to create virtual environment"; exit 1; }
else
    print_msg "${GREEN}" "Virtual environment exists at ${VENV_DIR}."
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
print_msg "${GREEN}" "Virtual environment activated."
echo

# =============================
# Python deps (only if missing)
# =============================
need_install=false

if ! python3 -m pip show agentstepper-api >/dev/null 2>&1; then
    need_install=true
fi

if ! python3 -m pip show agentstepper-core >/dev/null 2>&1; then
    need_install=true
fi

if [ "$need_install" = true ]; then
    print_msg "${YELLOW}" "Missing packages detected. Upgrading pip and installing local deps..."
    python3 -m pip install --upgrade pip || { print_msg "${RED}" "Failed to upgrade pip"; exit 1; }

    # Editable installs for your local packages (adjust paths if needed)
    python3 -m pip install -e "AgentStepper API"  || { print_msg "${RED}" "Failed to install AgentStepper API"; exit 1; }
    python3 -m pip install -e "AgentStepper Core" || { print_msg "${RED}" "Failed to install AgentStepper Core"; exit 1; }
else
    print_msg "${GREEN}" "All required Python packages are already installed. Skipping pip upgrade & installs."
fi
echo

# =============================
# Docker: availability & UI
# =============================
print_msg "${BLUE}" "Checking Docker availability..."
if ! command -v docker >/dev/null 2>&1; then
    print_msg "${RED}" "Error: Docker is not installed or not on PATH."
    exit 1
fi
print_msg "${GREEN}" "Docker is available."
echo

# Start/reuse container intelligently:
# 1) If running -> leave it running
# 2) If exists (stopped) -> start it
# 3) Else -> build image (cached if unchanged) and create container
if docker ps --format '{{.Names}}' | grep -qx "${UI_CONTAINER_NAME}"; then
    print_msg "${GREEN}" "Container '${UI_CONTAINER_NAME}' is already running."
elif docker ps -a --format '{{.Names}}' | grep -qx "${UI_CONTAINER_NAME}"; then
    print_msg "${YELLOW}" "Starting existing container '${UI_CONTAINER_NAME}'..."
    docker start "${UI_CONTAINER_NAME}" >/dev/null
else
    print_msg "${YELLOW}" "Building Docker image '${UI_IMAGE_TAG}' from '${UI_DOCKERFILE}'..."
    docker build -t "${UI_IMAGE_TAG}" -f "${UI_DOCKERFILE}" "${UI_DIR}"

    print_msg "${YELLOW}" "Creating and starting container '${UI_CONTAINER_NAME}' on ${UI_HOST_BIND}:${UI_HOST_PORT} -> ${UI_CONTAINER_PORT}..."
    docker run -d --name "${UI_CONTAINER_NAME}" \
        -p "${UI_HOST_BIND}:${UI_HOST_PORT}:${UI_CONTAINER_PORT}" \
        "${UI_IMAGE_TAG}" >/dev/null
fi

print_msg "${GREEN}" "UI container details:"
echo "  Name : ${UI_CONTAINER_NAME}"
echo "  Image: ${UI_IMAGE_TAG}"
echo "  URLs :"
echo "    - http://localhost:${UI_HOST_PORT}"
echo

# =============================
# Trap for cleanup on signals
# =============================
cleanup() {
    trap - EXIT INT TERM
    if docker ps --format '{{.Names}}' | grep -qx "${UI_CONTAINER_NAME}"; then
        print_msg "${YELLOW}" "Stopping Docker container '${UI_CONTAINER_NAME}'..."
        docker stop "${UI_CONTAINER_NAME}" >/dev/null 2>&1 || true
        print_msg "${GREEN}" "Container '${UI_CONTAINER_NAME}' stopped."
    fi
    exit 1
}
trap cleanup EXIT INT TERM

# =============================
# OpenAI API Key check/prompt
# =============================
if [ -n "$OPENAI_API_KEY" ]; then
    print_msg "${GREEN}" "OpenAI API key already set in environment."
else
    while true; do
        print_msg "${YELLOW}" "Enter your OpenAI API key (input hidden):"
        read -s -r api_key
        # Validation: checks if key starts with sk- and is at least 20 chars, allowing dashes
        if [[ $api_key =~ ^sk-[a-zA-Z0-9\-]{20,} ]]; then
            print_msg "${GREEN}" "Valid OpenAI API key format."
            export OPENAI_API_KEY="$api_key"
            print_msg "${GREEN}" "OpenAI API key exported successfully."
            break
        else
            print_msg "${RED}" "Error: Invalid OpenAI API key format. It should start with 'sk-' and be at least 20 characters."
        fi
    done
fi
echo

# =============================
# Start AgentStepper Core
# =============================
print_msg "${BLUE}" "Starting AgentStepper Core..."
if python3 -m agentstepper --config "AgentStepper Core"/default.conf; then
    print_msg "${GREEN}" "AgentStepper Core exited."
else
    print_msg "${RED}" "AgentStepper Core terminated with an error."
    # Script will still run cleanup via trap
    exit 1
fi
