"""Classify functional accelerator failures without rejecting expected taint."""
import re, sys
from pathlib import Path

def classify(log, secure_boot, version):
    warnings, failures = [], []
    for line in log.splitlines():
        if re.search(r"amdxdna.*module verification failed: signature and/or required key missing", line, re.I):
            if "SecureBoot disabled" in secure_boot and "2.21.260102.53.release" in version:
                warnings.append(line)
            else:
                failures.append(line)
        elif re.search(r"amdxdna.*(ERROR|timeout|fault|failed)|amdgpu.*(GPU reset|VM.*fault|ring.*timeout)", line, re.I):
            failures.append(line)
    return warnings, failures

if __name__ == "__main__":
    warnings, failures = classify(*(Path(p).read_text() for p in sys.argv[1:]))
    for line in warnings:
        print("WARNING (Secure Boot disabled; exact DKMS loaded):", line)
    for line in failures:
        print("FUNCTIONAL FAILURE:", line)
    if not failures:
        print("PASS: no functional accelerator kernel failure")
    sys.exit(bool(failures))
