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
print_msg "${BLUE}" "=== AgentStepper LLM Agent Debugger: UI Start Script ==="
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

print_msg "${YELLOW}" "Run 'docker stop ${UI_CONTAINER_NAME}' to stop the UI when done."
echo