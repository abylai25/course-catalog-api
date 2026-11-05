"""try_errors.py — smoke-test the five expected error responses.

Requires the API to be running on localhost:8000 and seed.sql to have been
loaded (so that aigerim@example.com and the enrollment for ai-integration/3
already exist).

Run:  python try_errors.py
Expected output:
    ok   email already taken     409  {"detail":"Student with this email already...
    ok   already enrolled        409  {"detail":"Student is already enrolled in t...
    ok   unknown course          404  {"detail":"Course not found"}
    ok   unknown student         404  {"detail":"Student not found"}
    ok   name too short          422  {"detail":[{"type":"string_too_short",...
    5 of 5 as expected
"""

import httpx

BASE = "http://localhost:8000"

# Each tuple: (description, path, request body, expected HTTP status)
CASES: list[tuple[str, str, dict, int]] = [
    (
        "email already taken",
        "/students",
        {"name": "Aigerim Two", "email": "aigerim@example.com"},
        409,
    ),
    (
        "already enrolled",
        "/enrollments",
        {"courseId": "ai-integration", "studentId": 3},
        409,
    ),
    (
        "unknown course",
        "/enrollments",
        {"courseId": "nope", "studentId": 3},
        404,
    ),
    (
        "unknown student",
        "/enrollments",
        {"courseId": "web-security", "studentId": 999},
        404,
    ),
    (
        "name too short",
        "/students",
        {"name": "N", "email": "n@example.com"},
        422,
    ),
]

failed = 0
with httpx.Client(base_url=BASE, timeout=5) as client:
    for title, path, body, expected in CASES:
        response = client.post(path, json=body)
        ok = response.status_code == expected
        failed += not ok
        mark = "ok  " if ok else "FAIL"
        print(f"{mark} {title:<22} {response.status_code}  {response.text[:60]}")

print(f"\n{len(CASES) - failed} of {len(CASES)} as expected")
raise SystemExit(bool(failed))
