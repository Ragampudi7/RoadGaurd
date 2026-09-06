"""End-to-end exercise of auth + persistence against a real Postgres."""
import os, uuid, json

os.environ["DATABASE_URL"] = "postgresql://postgres@127.0.0.1:5433/roadguard"
os.environ["JWT_SECRET"] = "test-secret-not-production"
os.environ["ALLOW_PRETRAINED_FALLBACK"] = "false"

from fastapi.testclient import TestClient
from app.main import app

ok = fail = 0
def check(label, cond, extra=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else:    fail += 1; print(f"  FAIL  {label} {extra}")

with TestClient(app) as c:
    email = f"siva+{uuid.uuid4().hex[:6]}@example.com"

    # ---- signup ----------------------------------------------------------
    r = c.post("/auth/signup", json={"name": "Siva", "email": email,
                                     "password": "correct-horse-battery", "city": "Hyderabad"})
    check("signup 201", r.status_code == 201, r.text[:160])
    tok = r.json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    check("token returned", bool(tok))
    check("password not echoed", "password" not in r.text.lower())

    # ---- duplicate email -------------------------------------------------
    r = c.post("/auth/signup", json={"name": "Other", "email": email.upper(),
                                     "password": "another-password-xyz"})
    check("duplicate email 409 (case-insensitive)", r.status_code == 409, r.text[:120])

    # ---- login -----------------------------------------------------------
    r = c.post("/auth/login", json={"email": email, "password": "correct-horse-battery"})
    check("login 200", r.status_code == 200, r.text[:120])
    r = c.post("/auth/login", json={"email": email, "password": "wrong"})
    check("bad password 401", r.status_code == 401)
    wrong_user = c.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    check("unknown email gives the SAME message as bad password",
          wrong_user.json()["error"]["message"] == r.json()["error"]["message"])

    # ---- auth guard ------------------------------------------------------
    check("no token 401", c.get("/auth/me").status_code == 401)
    check("garbage token 401", c.get("/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401)
    check("me 200", c.get("/auth/me", headers=H).status_code == 200)

    # ---- create reports --------------------------------------------------
    def payload(score, cond, risk, level, tier, lat, lon):
        return {"title": f"Test {cond}", "latitude": lat, "longitude": lon,
                "road_health_score": score, "road_condition": cond,
                "defect_percentage": 100 - score, "total_defects": 3,
                "defect_counts": {"pothole": 3},
                "risk_index": risk, "risk_level": level, "priority_tier": tier,
                "response_window": "Remediate within 7 days",
                "risk_components": [{"name": "Extent", "value": 48, "weight": 0.5}],
                "detections": [{"id": 1, "class_name": "pothole", "confidence": 0.84,
                                "severity": "Critical", "area_percentage": 11.9}],
                "model_name": "best.pt", "model_version": "yolo11n-640-e100",
                "inference_image_size": 640, "image_sha256": "a"*64,
                "image_width": 640, "image_height": 640,
                "complaint_description": "Defects detected.",
                "addressed_to": "GHMC"}

    r = c.post("/reports", json=payload(80.8, "Fair", 61.4, "High", "Priority-2", 17.49, 78.39), headers=H)
    check("create report 201", r.status_code == 201, r.text[:200])
    rid = r.json()["id"]
    check("defaults to Draft", r.json()["status"] == "Draft")
    check("reference generated", r.json()["reference"].startswith("RHA-"))
    check("detections round-tripped", len(r.json()["detections"]) == 1)
    check("model version stored", r.json()["model_version"] == "yolo11n-640-e100")

    c.post("/reports", json={**payload(38.7, "Dangerous", 88.4, "Critical", "Priority-1", 17.44, 78.39),
                             "submit": True}, headers=H)
    c.post("/reports", json=payload(91.2, "Good", 12.4, "Low", "Routine", 17.42, 78.41), headers=H)

    # ---- list / filter / bbox -------------------------------------------
    r = c.get("/reports", headers=H)
    check("list 200 with 3", r.status_code == 200 and r.json()["total"] == 3, r.text[:160])
    check("newest first", r.json()["items"][0]["road_condition"] == "Good")
    r = c.get("/reports?status=Submitted", headers=H)
    check("status filter", r.json()["total"] == 1, r.text[:120])
    r = c.get("/reports?min_lat=17.40&max_lat=17.43&min_lon=78.40&max_lon=78.42", headers=H)
    check("bbox filter", r.json()["total"] == 1, r.text[:160])

    # ---- stats -----------------------------------------------------------
    r = c.get("/reports/stats", headers=H)
    s = r.json()
    check("stats 200", r.status_code == 200, r.text[:160])
    check("stats total 3", s["total"] == 3)
    check("stats buckets", s["by_condition"].get("Good") == 1 and s["by_risk_level"].get("Critical") == 1, json.dumps(s)[:200])
    check("stats worst = highest risk", s["worst"]["risk_level"] == "Critical")

    # ---- status transitions ---------------------------------------------
    r = c.patch(f"/reports/{rid}/status", json={"status": "Submitted"}, headers=H)
    check("citizen may submit own draft", r.status_code == 200, r.text[:160])
    r = c.patch(f"/reports/{rid}/status", json={"status": "Resolved"}, headers=H)
    check("citizen may NOT self-resolve (403)", r.status_code == 403, r.text[:160])

    # ---- isolation between users ----------------------------------------
    other = c.post("/auth/signup", json={"name": "Mallory", "email": f"m{uuid.uuid4().hex[:6]}@x.com",
                                         "password": "another-password-xyz"}).json()
    H2 = {"Authorization": f"Bearer {other['access_token']}"}
    check("other user sees no reports", c.get("/reports", headers=H2).json()["total"] == 0)
    check("other user cannot read by id (404)", c.get(f"/reports/{rid}", headers=H2).status_code == 404)
    check("other user cannot change status", c.patch(f"/reports/{rid}/status",
          json={"status": "Resolved"}, headers=H2).status_code == 404)

    # ---- delete ----------------------------------------------------------
    check("delete own report 204", c.delete(f"/reports/{rid}", headers=H).status_code == 204)
    check("gone afterwards", c.get(f"/reports/{rid}", headers=H).status_code == 404)

print(f"\n{ok} passed, {fail} failed")
raise SystemExit(1 if fail else 0)
