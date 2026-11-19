#!/usr/bin/env bash
# Build the AWS Device Farm test package (APPIUM_PYTHON_TEST_PACKAGE) for the mobile suite:
#   tests + framework + a wheelhouse for the Device Farm Linux x86_64 host (Python 3.12).
# Usage: bash cloud/devicefarm/build_test_package.sh [output-dir]   -> <output-dir>/test_package.zip
set -euo pipefail
cd "$(dirname "$0")/../.."
out="${1:-build/devicefarm}"
rm -rf "$out" && mkdir -p "$out/package"

# Wheels for the HOST's platform, not this machine's: the device host installs offline from them.
# The Android test host is Amazon Linux 2 (glibc 2.26): only wheels built for glibc <= 2.26.
python -m pip download -r requirements.txt --dest "$out/package/wheelhouse" --only-binary=:all: \
  --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_24_x86_64 \
  --python-version 3.12 --implementation cp --quiet
python - "$out/package/wheelhouse" <<'PY'
import re, sys, pathlib
bad = []
for wheel in pathlib.Path(sys.argv[1]).glob("*.whl"):
    tags = wheel.stem.split("-")[-1].split(".")
    def ok(tag):
        if tag == "any" or tag.startswith(("manylinux1_", "manylinux2010_", "manylinux2014_")):
            return True
        m = re.match(r"manylinux_2_(\d+)_", tag)
        return bool(m) and int(m.group(1)) <= 26
    if not any(ok(t) for t in tags):
        bad.append(wheel.name)
if bad:
    sys.exit(f"wheels that need glibc > 2.26 (Amazon Linux 2 host): {bad}")
print("wheel platform check: all wheels run on glibc 2.26")
PY

cp -r conftest.py pyproject.toml requirements.txt requirements.toml framework features tests "$out/package/"
find "$out/package" -name __pycache__ -prune -exec rm -rf {} +
(cd "$out/package" && python -m zipfile -c ../test_package.zip .)
echo "$out/test_package.zip ($(du -h "$out/test_package.zip" | cut -f1))"
