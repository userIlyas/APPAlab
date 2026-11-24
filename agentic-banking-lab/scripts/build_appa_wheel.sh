#!/usr/bin/env bash
# Build the OpenAPPA Python wheel (appa_agent_python) from a local OpenAPPA
# checkout inside an isolated Rust container, and vendor it under ./vendor.
#
# Usage:
#   scripts/build_appa_wheel.sh [path/to/OpenAPPA]
#
# Defaults to ../OpenAPPA (sibling checkout).  Never clones or downloads
# sources; it only builds what already exists locally.  No secrets involved.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENAPPA="${1:-${HERE}/../OpenAPPA}"
VENDOR="${HERE}/vendor"
RUST_IMAGE="${APPA_BUILD_RUST_IMAGE:-rust:1.96-bookworm}"

if [[ ! -f "${OPENAPPA}/appa-agent-python/Cargo.toml" ]]; then
  echo "error: OpenAPPA checkout not found at ${OPENAPPA}" >&2
  exit 2
fi

mkdir -p "${VENDOR}" /tmp/appa-build /tmp/appa-dist
rm -rf /tmp/appa-build/* /tmp/appa-dist/*

# Copy without .git and without a possibly stale target dir.
tar -C "$(dirname "${OPENAPPA}")" \
    --exclude='.git' --exclude='target' --exclude='vendor' \
    -cf - "$(basename "${OPENAPPA}")" | tar -C /tmp/appa-build -xf -

docker run --rm \
  -e CARGO_TARGET_DIR=/build/target \
  -e CARGO_HOME=/build/cargo \
  -v /tmp/appa-build/OpenAPPA:/src:rw \
  -v /tmp/appa-dist:/dist \
  -w /src/appa-agent-python \
  "${RUST_IMAGE}" \
  bash -c 'set -euo pipefail; \
    apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip >/dev/null 2>&1; \
    python3 -m venv /build/venv; \
    /build/venv/bin/pip install --no-cache-dir --quiet "maturin>=1.9,<2"; \
    /build/venv/bin/maturin build --release --out /dist;'

cp /tmp/appa-dist/appa_agent_python-*.whl "${VENDOR}/"
echo "Built and vendored:"
ls -la "${VENDOR}"
