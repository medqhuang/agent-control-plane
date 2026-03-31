#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="remote-agent"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DEFAULT_WORKDIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
DEFAULT_VENV_DIR="${HOME}/.venvs/agent-control-plane"
DEFAULT_CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
DEFAULT_SYSTEMD_DIR="${DEFAULT_CONFIG_HOME}/systemd/user"
DEFAULT_ENV_DIR="${DEFAULT_CONFIG_HOME}/remote-agent"
DEFAULT_ENV_FILE="${DEFAULT_ENV_DIR}/remote-agent.env"
DEFAULT_SERVICE_FILE="${DEFAULT_SYSTEMD_DIR}/${SERVICE_NAME}.service"
DEFAULT_TEMPLATE_FILE="${DEFAULT_WORKDIR}/deploy/systemd/${SERVICE_NAME}.service.template"
DEFAULT_LOG_DIR="${HOME}/.local/state/remote-agent"
DEFAULT_LOG_FILE="${DEFAULT_LOG_DIR}/remote-agent.log"
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8711"
DEFAULT_LOG_LEVEL="info"

WORKDIR="${DEFAULT_WORKDIR}"
VENV_DIR="${DEFAULT_VENV_DIR}"
ENV_FILE="${DEFAULT_ENV_FILE}"
SERVICE_FILE="${DEFAULT_SERVICE_FILE}"
TEMPLATE_FILE="${DEFAULT_TEMPLATE_FILE}"
LOG_FILE="${DEFAULT_LOG_FILE}"
HOST="${DEFAULT_HOST}"
PORT="${DEFAULT_PORT}"
LOG_LEVEL="${DEFAULT_LOG_LEVEL}"
START_AFTER_INSTALL="false"

usage() {
  cat <<'EOF'
Usage: bash scripts/install-systemd-user.sh [options]

Options:
  --workdir PATH       Remote remote-agent workdir. Default: current repo copy
  --venv PATH          Virtualenv path. Default: ~/.venvs/agent-control-plane
  --host HOST          REMOTE_AGENT_HOST value. Default: 0.0.0.0
  --port PORT          REMOTE_AGENT_PORT value. Default: 8711
  --log-level LEVEL    REMOTE_AGENT_LOG_LEVEL value. Default: info
  --log-file PATH      Service log file path. Default: ~/.local/state/remote-agent/remote-agent.log
  --start              Start the service after install
  -h, --help           Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      WORKDIR="$2"
      shift 2
      ;;
    --venv)
      VENV_DIR="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --log-level)
      LOG_LEVEL="$2"
      shift 2
      ;;
    --log-file)
      LOG_FILE="$2"
      shift 2
      ;;
    --start)
      START_AFTER_INSTALL="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is required for user-service installation" >&2
  exit 1
fi

if ! systemctl --user is-system-running >/dev/null 2>&1; then
  echo "systemctl --user is not available for the current user session" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required on the remote host" >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE_FILE}" ]]; then
  echo "service template not found: ${TEMPLATE_FILE}" >&2
  exit 1
fi

WORKDIR="$(cd -- "${WORKDIR}" && pwd -P)"
mkdir -p "$(dirname -- "${ENV_FILE}")" "$(dirname -- "${SERVICE_FILE}")" "$(dirname -- "${VENV_DIR}")" "$(dirname -- "${LOG_FILE}")"

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

SERVICE_PYTHON="${VENV_DIR}/bin/python"
if [[ ! -x "${SERVICE_PYTHON}" ]]; then
  echo "virtualenv python not found: ${SERVICE_PYTHON}" >&2
  exit 1
fi

"${SERVICE_PYTHON}" -m pip install -e "${WORKDIR}"

cat > "${ENV_FILE}" <<EOF
REMOTE_AGENT_HOST=${HOST}
REMOTE_AGENT_PORT=${PORT}
REMOTE_AGENT_LOG_LEVEL=${LOG_LEVEL}
REMOTE_AGENT_LOG_FILE=${LOG_FILE}
EOF

escape_sed() {
  printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'
}

sed \
  -e "s/__REMOTE_AGENT_WORKDIR__/$(escape_sed "${WORKDIR}")/g" \
  -e "s/__REMOTE_AGENT_ENV_FILE__/$(escape_sed "${ENV_FILE}")/g" \
  -e "s/__REMOTE_AGENT_PYTHON_BIN__/$(escape_sed "${SERVICE_PYTHON}")/g" \
  "${TEMPLATE_FILE}" > "${SERVICE_FILE}"

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}.service" >/dev/null

if [[ "${START_AFTER_INSTALL}" == "true" ]]; then
  systemctl --user restart "${SERVICE_NAME}.service"
fi

LINGER_STATE="$(loginctl show-user "${USER}" -p Linger --value 2>/dev/null || true)"

echo "service_file=${SERVICE_FILE}"
echo "env_file=${ENV_FILE}"
echo "workdir=${WORKDIR}"
echo "python_bin=${SERVICE_PYTHON}"
echo "log_file=${LOG_FILE}"
echo "linger=${LINGER_STATE:-unknown}"

if [[ "${LINGER_STATE}" != "yes" ]]; then
  echo "warning=loginctl linger is not enabled; the user service may not survive logout" >&2
fi
