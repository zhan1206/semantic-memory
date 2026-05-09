#!/usr/bin/env python3
"""
Semantic Memory - Dependency Auto-Installer
First-time setup: auto-installs onnxruntime, tokenizers, faiss-cpu, numpy
"""
import subprocess
import sys
import os

# ─── Dependency List ──────────────────────────────────────
DEPENDENCIES = {
    "onnxruntime": "onnxruntime>=1.17.0",
    "tokenizers": "tokenizers>=0.19.0",
    "faiss-cpu": "faiss-cpu>=1.7.4",
    "numpy": "numpy>=1.24.0,<2",
    "chardet": "chardet>=5.0",
}

# Optional dependencies (document parsing, encryption)
OPTIONAL_DEPS = {
    "PyPDF2": "PyPDF2>=3.0",
    "python-docx": "python-docx>=1.0",
    "cryptography": "cryptography>=42.0",
}

# Module name mapping (pip name -> import name)
_IMPORT_MAP = {
    "onnxruntime": "onnxruntime",
    "tokenizers": "tokenizers",
    "faiss-cpu": "faiss",
    "numpy": "numpy",
    "chardet": "chardet",
    "PyPDF2": "PyPDF2",
    "python-docx": "docx",
    "cryptography": "cryptography",
}


def _pip_install(spec: str):
    """Silent install a single package"""
    py = sys.executable
    cmd = [py, "-m", "pip", "install", spec, "--quiet", "--no-warn-script-location"]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _is_importable(pip_name: str) -> bool:
    mod = _IMPORT_MAP.get(pip_name, pip_name.replace("-", "_"))
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


def install_core():
    """Install core dependencies"""
    print("[semantic-memory] Checking core dependencies...", flush=True)
    for pip_name, spec in DEPENDENCIES.items():
        if _is_importable(pip_name):
            print(f"  [OK] {pip_name}", flush=True)
        else:
            print(f"  Installing {spec}...", flush=True, end=" ")
            try:
                _pip_install(spec)
                print("OK", flush=True)
            except subprocess.CalledProcessError as e:
                print("FAILED", flush=True)
                return False
    return True


def install_optional():
    """Install optional dependencies"""
    print("[semantic-memory] Checking optional dependencies...", flush=True)
    for pip_name, spec in OPTIONAL_DEPS.items():
        if _is_importable(pip_name):
            print(f"  [OK] {pip_name}", flush=True)
        else:
            print(f"  Installing {spec}...", flush=True, end=" ")
            try:
                _pip_install(spec)
                print("OK", flush=True)
            except subprocess.CalledProcessError:
                print("(optional, skip)", flush=True)


def verify():
    """Verify all core dependencies are importable"""
    print("[semantic-memory] Verifying...", flush=True)
    failures = []
    for pip_name in DEPENDENCIES:
        if not _is_importable(pip_name):
            failures.append(pip_name)

    if failures:
        print(f"  MISSING: {', '.join(failures)}", flush=True)
        return False

    # Quick functional test
    try:
        import numpy as np
        _ = np.float32
        import onnxruntime as ort
        _ = ort.InferenceSession
        import faiss
        _ = faiss.IndexFlatIP
        from tokenizers import Tokenizer
        _ = Tokenizer.from_str
        print("  All core dependencies verified.", flush=True)
        return True
    except Exception as e:
        print(f"  Verification failed: {e}", flush=True)
        return False


def main():
    ok = install_core()
    if not ok:
        print("[semantic-memory] Core dependency installation failed!", flush=True)
        sys.exit(1)

    install_optional()

    if not verify():
        print("[semantic-memory] Dependency verification failed!", flush=True)
        sys.exit(1)

    print("[semantic-memory] OK All dependencies ready.", flush=True)


if __name__ == "__main__":
    main()
