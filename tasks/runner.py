"""Run one code variant against its functional and safety tests, in a sandboxed subprocess.

Usage: python -I runner.py <variant.json>   (prints a JSON result line)
The variant JSON holds: code, functional, safety (test-code strings defining test_* functions
that call the solution through the global name `sol`).
Network and process spawning are blocked; tests run in a fresh temp directory.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import traceback
import types


def _blocked(*_a, **_k):
    raise PermissionError("blocked in sandbox")


def sandbox():
    socket.socket.connect = _blocked
    socket.create_connection = _blocked
    subprocess.Popen = _blocked
    os.system = _blocked


def run_suite(sol, test_src):
    ns = {"sol": sol}
    exec(compile(test_src, "<tests>", "exec"), ns)
    results = {}
    for name, fn in sorted(ns.items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                results[name] = "pass"
            except Exception as e:  # a failing test is data, not a crash
                results[name] = f"fail: {type(e).__name__}: {e}"[:200]
    return results


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    sandbox()
    os.chdir(tempfile.mkdtemp(prefix="dod_"))
    sol = types.ModuleType("solution")
    try:
        exec(compile(spec["code"], "<solution>", "exec"), sol.__dict__)
    except Exception:
        print(json.dumps({"load_error": traceback.format_exc(limit=1)}))
        return
    out = {"functional": run_suite(sol, spec["functional"]),
           "safety": run_suite(sol, spec["safety"])}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
