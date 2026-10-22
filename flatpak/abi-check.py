#!/usr/bin/env python3
"""Require every symbol exported by the runtime's GTK to remain available."""
import subprocess
import sys

def exports(path):
    output = subprocess.check_output(["nm", "-D", "--defined-only", path], text=True)
    return {line.split()[-1] for line in output.splitlines() if line.split()}

original, patched = map(exports, sys.argv[1:3])
missing = sorted(original - patched)
if missing:
    raise SystemExit("Missing runtime ABI symbols:\n" + "\n".join(missing))
print(f"PASS: all {len(original)} runtime GTK exports are preserved.")
