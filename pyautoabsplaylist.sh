#!/bin/bash

# Default values
VENV_NAME="myvenv"
SCRIPT="main.py"
LOG_FILE="${HOME}/.local/share/pyautoabsplaylist/logs/playlist_auto.log"
CONFIG_FILE="${PWD}/config.yaml"  # Default to the current directory's config.yaml
SHOW_LOG=0
CLOSE_VENV=0
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")" # the directory where the script was symlinked from (the repo directory)

mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"

# Help message
show_help() {
    cat <<EOF

Usage: $(basename "$0") [--config <path/to/config.yaml>] [--venv <name>] [--log] [--close-venv]

Options:
  --config <path>    Path to a config file. If omitted, uses \`config.yaml\` in the current directory.
  --venv <name>      Name for the virtual environment. If omitted, defaults to "myvenv".
  --log              Show and follow the log file at ${LOG_FILE}
  --close-venv       Manually deactivate the virtual environment.
  --help             Show this help message and exit.

Behavior:
  - Create and activate a Python virtual environment in (${HOME}/mytools/<venv name>).
  - Install/update dependencies from ${SCRIPT_DIR}/requirements.txt .
  - Run a python script to create/update playlist(s) in Audiobookshelf
    based on configurations in \`config.yaml\`.
  - Deactivate the Python virtual environment.

EOF
}

# Function to deactivate the virtual environment if active
close_venv() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "Deactivating virtual environment..."
        echo "$(date '+%Y-%m-%d %H:%M:%S') Deactivating virtual environment at ${VENV_DIR}..." >> "${LOG_FILE}"
        deactivate
    else
        echo "No active virtual environment to deactivate."
    fi
}

# Parse arguments
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --log)
            SHOW_LOG=1
            shift
            ;;
        --venv)
            VENV_NAME="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --close-venv)
            CLOSE_VENV=1
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Deactivate the virtual environment if --close-venv is set
if [ "${CLOSE_VENV}" -eq 1 ]; then
    close_venv
    exit 0
fi

# Ensure the app repo directory contains the necessary files
if [ ! -f "${SCRIPT_DIR}/requirements.txt" ]; then
    echo "Error: requirements.txt not found in the repo directory (${SCRIPT_DIR})."
    echo "$(date '+%Y-%m-%d %H:%M:%S') Error: requirements.txt not found in the repo directory (${SCRIPT_DIR})." >> "${LOG_FILE}"
    exit 1
fi

# Create venv if needed
VENV_DIR="${HOME}/mytools/${VENV_NAME}"
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    echo "$(date '+%Y-%m-%d %H:%M:%S') Creating virtual environment at ${VENV_DIR}..." >> "${LOG_FILE}"
    python3 -m venv "${VENV_DIR}"
else
    echo "Virtual environment already exists at ${VENV_DIR}..."
    echo "$(date '+%Y-%m-%d %H:%M:%S') Virtual environment already exists at ${VENV_DIR}..." >> "${LOG_FILE}"
fi

# Launch log watcher if requested
if [ "${SHOW_LOG}" -eq 1 ]; then
    echo "Tailing log: ${LOG_FILE}"
    echo "(<ctrl>-c to exit)"
    echo
    sleep 1.5
    tail -n 30 -f "${LOG_FILE}"
    exit 0
fi

# Always ensure dependencies are installed
echo "Installing/upgrading dependencies..."
echo "$(date '+%Y-%m-%d %H:%M:%S') Installing/upgrading dependencies..." >> "${LOG_FILE}"
"${VENV_DIR}/bin/pip" install --upgrade -r "${SCRIPT_DIR}/requirements.txt" >> "${LOG_FILE}" 2>&1

# Activate the virtual environment
echo "Activating virtual environment at ${VENV_DIR}..."
echo "$(date '+%Y-%m-%d %H:%M:%S') Activating virtual environment at ${VENV_DIR}..." >> "${LOG_FILE}"
source "${VENV_DIR}/bin/activate"

# Run the Python script from the repo directory with remaining args
python "${SCRIPT_DIR}/${SCRIPT}" "${ARGS[@]}" --config "${CONFIG_FILE}"

echo "Deactivating virtual environment at ${VENV_DIR}..."
echo "$(date '+%Y-%m-%d %H:%M:%S') Deactivating virtual environment at ${VENV_DIR}..." >> "${LOG_FILE}"
close_venv
