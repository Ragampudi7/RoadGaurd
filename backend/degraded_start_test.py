"""
An unreachable database must not take the whole API down.

Needs no database - that is the point. It configures a DATABASE_URL whose
hostname cannot resolve and asserts the service still starts, still serves
the model, and is honest about what is missing.

This exists because the opposite happened: a DNS failure on the Aiven host
raised out of the lifespan and uvicorn exited with "Application startup
failed", taking detection down with it. Detection needs no database at all.

    python3 degraded_start_test.py
"""

import os

# A .invalid TLD is reserved by RFC 2606 and can never resolve, anywhere.
os.environ["DATABASE_URL"] = "postgresql://u:p@unreachable.invalid:5432/x"
os.environ["JWT_SECRET"] = "degraded-start-secret-thirty-two-bytes"
os.environ.setdefault("ALLOW_PRETRAINED_FALLBACK", "false")

from fastapi.testclient import TestClient   # noqa: E402
from app.main import app                    # noqa: E402

ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {extra}")


with TestClient(app) as c:
    check("the app starts at all", True)

    r = c.get("/health")
    body = r.json()
    check("health answers 200", r.status_code == 200, r.text[:120])
    check("persistence is reported as unavailable",
          body["persistence"] == "unavailable", body["persistence"])
    check("the model is still loaded", body["model_loaded"] is True)
    check("status is not falsely 'ok' about the model", body["status"] == "ok")

    # The half that needs no database must be untouched.
    check("root still serves", c.get("/").status_code == 200)

    # The half that does need one must refuse cleanly, not explode.
    r = c.post("/auth/signup", json={"name": "A", "email": "a@example.com",
                                     "password": "abcdefgh1234"})
    check("signup answers 503, not a 500", r.status_code == 503, r.text[:140])
    check("and says the database is the reason",
          "database" in r.text.lower(), r.text[:140])

    r = c.get("/reports", headers={"Authorization": "Bearer nonsense"})
    check("reports refuses without crashing", r.status_code in (401, 503), r.text[:120])

print(f"\n{ok} passed, {fail} failed")
raise SystemExit(1 if fail else 0)
