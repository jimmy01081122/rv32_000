#!/usr/bin/env bash
# Development preflight. --signoff additionally requires the ACT4 generator.
set -euo pipefail
project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
sim_image=${SIM_IMAGE:-rv32ooo-sim:g1}
syn_image=${SYN_IMAGE:-rv32ooo-syn:g1}
act_image=${ACT_IMAGE:-$sim_image}
failures=0

if ! command -v docker >/dev/null || ! docker info >/dev/null 2>&1; then
  echo 'ERROR: Docker daemon is unavailable.' >&2
  exit 1
fi
docker version --format 'Docker server: {{.Server.Version}}'

check_image() {
  local image=$1
  shift
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "ERROR: Missing image $image; run make docker-build." >&2
    failures=$((failures + 1))
    return
  fi
  if ! docker run --rm --pull=never --user "$(id -u):$(id -g)" \
    --entrypoint /bin/bash "$image" -euc "$*"; then
    echo "ERROR: Required tools unavailable in $image." >&2
    failures=$((failures + 1))
  fi
}

check_image "$sim_image" 'verilator --version; riscv32-unknown-elf-gcc --version; spike -h; python3 --version'
check_image "$syn_image" 'sv2v --numeric-version; yosys -V; python3 --version'

for dependency in software/embench/embench-iot verification/act4/riscv-arch-test; do
  expected=$(git ls-files --stage "$dependency" | awk '{print $2}')
  if [ ! -e "$dependency/.git" ]; then
    echo "ERROR: $dependency is missing; run make deps-init." >&2
    failures=$((failures + 1))
  elif [ "$(git -C "$dependency" rev-parse HEAD)" != "$expected" ]; then
    echo "ERROR: $dependency differs from tracked commit $expected." >&2
    failures=$((failures + 1))
  else
    echo "Dependency: $dependency @ $expected"
  fi
done

if [ "${1:-}" = --signoff ]; then
  check_image "$act_image" 'sail_riscv_sim --version; if ! command -v mise; then command -v uv; command -v bundle; fi'
else
  echo 'ACT4 fresh generation and ASAP7 physical implementation require additional tooling; see docs/SESSION_HANDOFF.md.'
fi

if [ "$failures" -gt 0 ]; then
  echo "Environment check failed: $failures problem(s)." >&2
  exit 1
fi
echo 'Environment check passed.'
