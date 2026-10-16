#!/bin/sh
set -eu

if [ "$(uname -m)" != "arm64" ]; then
    echo "This MLX setup requires native Apple silicon (arm64)." >&2
    exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install cmake==4.4.4 pybind11==3.1.0
mkdir -p work/bin
cat > work/bin/nproc <<'NPROC'
#!/bin/sh
sysctl -n hw.logicalcpu
NPROC
chmod +x work/bin/nproc
PATH="$PWD/.venv/bin:$PWD/work/bin:$PATH" ARCHFLAGS="-arch arm64" CMAKE_POLICY_VERSION_MINIMUM=3.5 \
    .venv/bin/python -m pip install --no-build-isolation sentencepiece==0.2.2
.venv/bin/python -m pip install -r requirements.txt
