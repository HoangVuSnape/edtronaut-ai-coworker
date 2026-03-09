#!/usr/bin/env python3
"""
Generate Python gRPC stubs from .proto files.

Usage:
    python scripts/generate_protos.py

Output goes to src/coworker_api/generated/
"""

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROTO_DIR = BACKEND_DIR / "protos"
OUTPUT_DIR = BACKEND_DIR / "src" / "coworker_api" / "generated"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create __init__.py if missing
    init_file = OUTPUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Generated gRPC/Protobuf stubs."""\n')

    proto_files = list(PROTO_DIR.glob("*.proto"))
    if not proto_files:
        print("No .proto files found in", PROTO_DIR)
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={PROTO_DIR}",
        f"--python_out={OUTPUT_DIR}",
        f"--grpc_python_out={OUTPUT_DIR}",
        f"--pyi_out={OUTPUT_DIR}",
    ] + [str(f) for f in proto_files]

    print(f"Compiling {len(proto_files)} proto file(s)...")
    print(f"  Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR:", result.stderr)
        sys.exit(result.returncode)

    # Fix imports in generated files (grpc_tools generates absolute imports
    # like `import coworker_pb2`, but we need relative `from . import ...`)
    for py_file in OUTPUT_DIR.glob("*_grpc.py"):
        content = py_file.read_text()
        for proto_file in proto_files:
            stem = proto_file.stem
            old_import = f"import {stem}_pb2"
            new_import = f"from . import {stem}_pb2"
            if old_import in content and new_import not in content:
                content = content.replace(old_import, new_import)
        py_file.write_text(content)

    print(f"Generated stubs in {OUTPUT_DIR}:")
    for f in sorted(OUTPUT_DIR.glob("*.py*")):
        print(f"  {f.name}")
    print("Done!")


if __name__ == "__main__":
    main()
