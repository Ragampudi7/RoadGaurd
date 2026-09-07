"""Exercise GET /reports/{id}/pdf against a real Postgres and a real photograph."""
import hashlib
import io
import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/roadguard")
os.environ.setdefault("JWT_SECRET", "regen-test-secret-thirty-two-bytes-plus")
os.environ.setdefault("ALLOW_PRETRAINED_FALLBACK", "false")

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {extra}")


IMG_PATH = "/home/claude/training/datasets/pothole/test/images/11_jpg.rf.7ef3d543d83c0f883b9145bb22c860a5.jpg"
photo = open(IMG_PATH, "rb").read()
digest = hashlib.sha256(photo).hexdigest()
w, h = Image.open(io.BytesIO(photo)).size

import base64

with TestClient(app) as c:
    email = f"regen+{uuid.uuid4().hex[:8]}@example.com"
    tok = c.post("/auth/signup", json={"name": "Regen", "email": email,
                                       "password": "regen-password-123"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    payload = {
        "title": "Regeneration test", "latitude": 17.4948, "longitude": 78.3996,
        "road_health_score": 80.84, "road_condition": "Fair", "defect_percentage": 19.16,
        "total_defects": 2, "defect_counts": {"pothole": 2},
        "risk_index": 61.4, "risk_level": "High", "priority_tier": "Priority-2",
        "response_window": "Remediate within 7 days",
        "risk_components": [{"name": "Extent", "value": 19.16, "unit": "%", "value_display": "19.16% of the frame damaged", "full_scale": 40.0, "score": 47.9, "weight": 0.4}],
        "risk_detail": {
            "risk_index": 61.4, "risk_level": "High", "risk_colour": "#E8833A",
            "priority_tier": "Priority-2", "response_window": "Remediate within 7 days",
            "components": [{"name": "Extent", "value": 19.16, "unit": "%", "value_display": "19.16% of the frame damaged", "full_scale": 40.0, "score": 47.9, "weight": 0.4}],
            "hazard_factor": 0.9, "confidence_factor": 0.82,
            "max_severity": "Critical", "dominant_defect": "pothole",
            "summary": "High risk - schedule remediation within a week.",
        },
        "detections": [
            {"id": 1, "class_id": 0, "class_name": "pothole", "confidence": 0.84,
             "bbox": [40, 60, 220, 190], "area": 23400, "area_percentage": 5.71,
             "severity": "High", "severity_rank": 2, "severity_colour": "#E8833A",
             "recommended_action": "Patch within the week."},
            {"id": 2, "class_id": 0, "class_name": "pothole", "confidence": 0.71,
             "bbox": [300, 320, 480, 500], "area": 32400, "area_percentage": 7.91,
             "severity": "Critical", "severity_rank": 3, "severity_colour": "#D1495B",
             "recommended_action": "Barricade and repair."},
        ],
        "model_name": "best.pt", "model_version": "yolo11n-935e809b",
        "inference_image_size": 640,
        "image_sha256": digest, "image_width": w, "image_height": h,
        "image_base64": base64.b64encode(photo).decode(), "image_mime": "image/jpeg",
        "complaint_description": "Two potholes on the carriageway.",
        "addressed_to": "Greater Hyderabad Municipal Corporation (GHMC)",
    }

    r = c.post("/reports", json=payload, headers=H)
    check("report filed with its photograph", r.status_code == 201, r.text[:200])
    rid = r.json()["id"]

    r = c.get(f"/reports/{rid}/pdf", headers=H)
    check("pdf 200", r.status_code == 200, r.text[:300])
    body = r.content
    check("is a real PDF", body[:5] == b"%PDF-", body[:20])
    check("has some size", len(body) > 40_000, f"{len(body)} bytes")
    check("offered as a download named by the reference",
          "road_health_report_RHA-" in r.headers.get("content-disposition", ""),
          r.headers.get("content-disposition"))
    check("not cached", r.headers.get("cache-control") == "no-store")

    open("/home/claude/regen.pdf", "wb").write(body)

    # The document must say it is a rebuild, and name the weights it was filed
    # under rather than whatever this process happens to have loaded.
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(body)).pages)
    check("marked as a regenerated copy", "REGENERATED COPY" in text.upper(), text[:200])
    check("names the weights it was filed under", "yolo11n-935e809b" in text)
    check("shows the filed score, not a recomputed one", "80.84" in text or "80.8" in text)
    check("carries the reference", r.json if False else "RHA-" in text)
    check("addressed to the municipal body", "GHMC" in text or "Hyderabad" in text)

    # Another user must not be able to pull someone else's evidence.
    other = c.post("/auth/signup", json={"name": "Mallory",
                                         "email": f"m{uuid.uuid4().hex[:6]}@x.com",
                                         "password": "another-password-xyz"}).json()
    H2 = {"Authorization": f"Bearer {other['access_token']}"}
    check("another user gets 404, not the PDF",
          c.get(f"/reports/{rid}/pdf", headers=H2).status_code == 404)
    check("no token gets 401", c.get(f"/reports/{rid}/pdf").status_code == 401)

    # A report filed without its photograph cannot be rebuilt, and says so.
    no_photo = dict(payload)
    no_photo.pop("image_base64")
    rid2 = c.post("/reports", json=no_photo, headers=H).json()["id"]
    r = c.get(f"/reports/{rid2}/pdf", headers=H)
    check("no photograph -> a clear refusal, not a 500",
          r.status_code == 409 and "photograph" in r.text.lower(),
          f"{r.status_code} {r.text[:160]}")

    c.delete(f"/reports/{rid}", headers=H)
    c.delete(f"/reports/{rid2}", headers=H)

print(f"\n{ok} passed, {fail} failed")
raise SystemExit(1 if fail else 0)
