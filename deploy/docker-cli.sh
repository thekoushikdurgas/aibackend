# shellcheck shell=bash
# Resolve docker / docker compose when the deploy user cannot access docker.sock yet.
# Source from deploy/*.sh:  source "$(dirname "${BASH_SOURCE[0]}")/docker-cli.sh"
#
# Sets DOCKER_CMD (array) and provides dc() for "docker compose …".
# Environment:
#   DEPLOY_USE_SUDO_DOCKER=1  force sudo docker
#   DEPLOY_USE_SUDO_DOCKER=0  never use sudo (fail with instructions)

setup_docker_cli() {
  local prefix="${1:-[docker]}"
  DOCKER_CMD=(docker)

  if "${DOCKER_CMD[@]}" info >/dev/null 2>&1; then
    return 0
  fi

  if [[ "${DEPLOY_USE_SUDO_DOCKER:-}" == "1" ]]; then
    if sudo docker info >/dev/null 2>&1; then
      echo "${prefix} Using sudo docker (DEPLOY_USE_SUDO_DOCKER=1)."
      DOCKER_CMD=(sudo docker)
      return 0
    fi
  fi

  if [[ "${DEPLOY_USE_SUDO_DOCKER:-}" == "0" ]]; then
    _docker_permission_help "$prefix"
    return 1
  fi

  # Auto-fallback after ec2-bootstrap (usermod -aG docker needs new login).
  if sudo docker info >/dev/null 2>&1; then
    echo "${prefix} WARNING: permission denied on docker.sock — using sudo for this run."
    echo "${prefix} Permanent fix: exit SSH and reconnect, or run: newgrp docker"
    DOCKER_CMD=(sudo docker)
    return 0
  fi

  _docker_permission_help "$prefix"
  return 1
}

_docker_permission_help() {
  local prefix="${1:-[docker]}"
  echo "${prefix} ERROR: cannot access Docker (permission denied on /var/run/docker.sock)."
  if id -nG 2>/dev/null | grep -qw docker || groups 2>/dev/null | grep -qw docker; then
    echo "${prefix} You are in group 'docker' but this shell was started before usermod."
    echo "${prefix} Run:  newgrp docker"
    echo "${prefix} Or:   exit SSH, reconnect, then: bash deploy/remote-deploy.sh"
  else
    echo "${prefix} Run:  sudo usermod -aG docker \"\$USER\" && newgrp docker"
  fi
  echo "${prefix} Or:   DEPLOY_USE_SUDO_DOCKER=1 bash deploy/remote-deploy.sh"
}

dc() {
  "${DOCKER_CMD[@]}" compose "$@"
}
