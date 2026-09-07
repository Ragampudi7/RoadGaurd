"""
The municipal official's half of the grievance loop, against a real Postgres.

The role is granted by the deployment's allow-list, never by the request, so
these tests set OFFICIAL_EMAILS before the app is imported and then check that
an ordinary signup cannot reach the same powers by asking.
"""
import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/roadguard")
os.environ.setdefault("JWT_SECRET", "official-test-secret-thirty-two-bytes")
os.environ.setdefault("ALLOW_PRETRAINED_FALLBACK", "false")

OFFICIAL = f"engineer{uuid.uuid4().hex[:6]}@ghmc.gov.in"
os.environ["OFFICIAL_EMAILS"] = "@ghmc.gov.in, named.person@example.com"

from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                            # noqa: E402

ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {extra}")


def payload(**kw):
    base = {
        "title": "Queue test", "latitude": 17.4948, "longitude": 78.3996,
        "road_health_score": 62.0, "road_condition": "Poor", "defect_percentage": 38.0,
        "total_defects": 3, "defect_counts": {"pothole": 3},
        "risk_index": 74.0, "risk_level": "High", "priority_tier": "Priority-2",
        "model_name": "best.pt", "model_version": "yolo11n-935e809b",
    }
    base.update(kw)
    return base


with TestClient(app) as c:
    # -- who gets to be an official ----------------------------------------
    print("\n1. Granting the role")
    citizen_email = f"citizen{uuid.uuid4().hex[:6]}@example.com"
    r = c.post("/auth/signup", json={"name": "Citizen", "email": citizen_email,
                                     "password": "citizen-password-1"})
    check("ordinary signup is a citizen", r.json()["user"]["role"] == "citizen", r.text[:160])
    CIT = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Asking for the role must not grant it.
    sneaky = f"sneaky{uuid.uuid4().hex[:6]}@example.com"
    r = c.post("/auth/signup", json={"name": "Sneaky", "email": sneaky,
                                     "password": "sneaky-password-1", "role": "official"})
    check("asking for 'official' in the signup body does not grant it",
          r.json()["user"]["role"] == "citizen", r.text[:200])

    r = c.post("/auth/signup", json={"name": "Engineer", "email": OFFICIAL,
                                     "password": "official-password-1"})
    check("an allow-listed domain signs up as an official",
          r.json()["user"]["role"] == "official", r.text[:200])
    OFF = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = c.post("/auth/signup", json={"name": "Named", "email": "named.person@example.com",
                                     "password": "named-password-1"})
    if r.status_code == 409:            # left over from a previous run
        r = c.post("/auth/login", json={"email": "named.person@example.com",
                                        "password": "named-password-1"})
    check("an allow-listed single address works too",
          r.json()["user"]["role"] == "official", r.text[:200])

    # -- the citizen files -------------------------------------------------
    print("\n2. What the queue shows")
    draft = c.post("/reports", json=payload(title="Private draft"), headers=CIT).json()
    filed = c.post("/reports", json=payload(title="Filed complaint", submit=True),
                   headers=CIT).json()
    check("citizen has a draft and a filed report",
          draft["status"] == "Draft" and filed["status"] == "Submitted")

    r = c.get("/reports?mine=false", headers=OFF)
    titles = [i["title"] for i in r.json()["items"]]
    check("the official sees the filed complaint", "Filed complaint" in titles, str(titles[:5]))
    check("the official does NOT see anybody's draft", "Private draft" not in titles,
          str(titles[:5]))

    r = c.get(f"/reports/{draft['id']}", headers=OFF)
    check("reading a draft by id is a 404, not a 403", r.status_code == 404, r.text[:120])
    r = c.get(f"/reports/{filed['id']}", headers=OFF)
    check("reading a filed report by id works", r.status_code == 200, r.text[:120])

    r = c.get("/reports", headers=OFF)
    check("without mine=false an official sees only their own",
          r.json()["total"] == 0, r.text[:160])

    # -- acting on it -------------------------------------------------------
    print("\n3. Acting on a complaint")
    r = c.patch(f"/reports/{filed['id']}/status", json={"status": "Acknowledged"}, headers=OFF)
    check("official may acknowledge", r.status_code == 200, r.text[:200])
    r = c.patch(f"/reports/{filed['id']}/status", json={"status": "Resolved"}, headers=OFF)
    check("official may resolve", r.status_code == 200, r.text[:200])
    r = c.patch(f"/reports/{filed['id']}/status", json={"status": "Acknowledged"}, headers=OFF)
    check("official may reopen a resolution that did not hold", r.status_code == 200)

    r = c.patch(f"/reports/{filed['id']}/status", json={"status": "Draft"}, headers=OFF)
    check("official may NOT un-file a citizen's complaint", r.status_code == 403, r.text[:200])

    r = c.patch(f"/reports/{draft['id']}/status", json={"status": "Acknowledged"}, headers=OFF)
    check("official cannot act on a draft at all (404)", r.status_code == 404, r.text[:160])

    r = c.delete(f"/reports/{filed['id']}", headers=OFF)
    check("official may not delete a citizen's report", r.status_code == 403, r.text[:160])

    # -- the citizen still cannot ------------------------------------------
    print("\n4. The citizen's limits are unchanged")
    r = c.patch(f"/reports/{filed['id']}/status", json={"status": "Resolved"}, headers=CIT)
    check("citizen still cannot self-resolve", r.status_code == 403, r.text[:160])
    r = c.get("/reports?mine=false", headers=CIT)
    check("mine=false does nothing for a citizen", r.json()["total"] == 2, r.text[:160])

    # -- evidence -----------------------------------------------------------
    print("\n5. Evidence")
    r = c.get(f"/reports/{filed['id']}/pdf", headers=OFF)
    check("official can pull the complaint document (409 here: no photo stored)",
          r.status_code in (200, 409), f"{r.status_code} {r.text[:120]}")
    r = c.get(f"/reports/{draft['id']}/pdf", headers=OFF)
    check("but not a draft's", r.status_code == 404, r.text[:120])

    c.delete(f"/reports/{filed['id']}", headers=CIT)
    c.delete(f"/reports/{draft['id']}", headers=CIT)

print(f"\n{ok} passed, {fail} failed")
raise SystemExit(1 if fail else 0)
