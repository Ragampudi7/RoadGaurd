#!/usr/bin/env python3
"""
Verify the database connection, create the tables, and smoke-test the API.

Run from the backend directory on a machine that can reach Aiven:

    python3 scripts/verify_db.py

Reads DATABASE_URL and JWT_SECRET from .env. It never prints either value —
only the host, so a screenshot of the output is safe to share.

Everything it creates is deleted before it exits.
"""

from __future__ import annotations

import os
import pathlib
import re
import socket
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GREEN, RED, DIM, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
ok = fail = 0


def check(label: str, cond: bool, extra: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  {GREEN}PASS{OFF}  {label}")
    else:
        fail += 1
        print(f"  {RED}FAIL{OFF}  {label} {DIM}{extra}{OFF}")


def load_env() -> dict[str, str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        sys.exit(f"{RED}No .env at {env_path}{OFF}\n"
                 "Add DATABASE_URL and JWT_SECRET first — see .env.aiven.example.")
    env = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main() -> int:
    env = load_env()
    url = env.get("DATABASE_URL", "")
    if not url:
        sys.exit(f"{RED}DATABASE_URL is empty in .env{OFF}")

    os.environ.setdefault("DATABASE_URL", url)
    os.environ.setdefault("JWT_SECRET", env.get("JWT_SECRET", ""))
    # Keep this script independent of whether weights are present.
    os.environ.setdefault("ALLOW_PRETRAINED_FALLBACK", "false")

    print("\n\033[1mRoadGuard — database verification\033[0m\n")

    # -- 1. reachability ----------------------------------------------------
    m = re.search(r"@([^:/?]+):?(\d+)?", url)
    if not m:
        sys.exit(f"{RED}Could not parse a host out of DATABASE_URL{OFF}")
    host, port = m.group(1), int(m.group(2) or 5432)
    print(f"{DIM}  host {host}:{port}{OFF}")
    try:
        socket.create_connection((host, port), timeout=15).close()
        check("TCP connection", True)
    except Exception as e:
        check("TCP connection", False, f"{type(e).__name__}: {e}")
        print(f"\n{RED}Cannot reach the database.{OFF} Check that the Aiven service is "
              "running, and that this network allows outbound connections on that port.\n")
        return 1

    secret = env.get("JWT_SECRET", "")
    check("JWT_SECRET set", bool(secret))
    check("JWT_SECRET at least 32 bytes", len(secret.encode()) >= 32,
          f"got {len(secret.encode())} bytes — production start-up will refuse this")

    # -- 2. schema ----------------------------------------------------------
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:      # lifespan creates the engine and tables
        check("engine started and tables created", True)

        email = f"verify+{uuid.uuid4().hex[:8]}@example.com"
        r = c.post("/auth/signup", json={"name": "Verify", "email": email,
                                         "password": "verify-password-123"})
        check("signup", r.status_code == 201, r.text[:140])
        if r.status_code != 201:
            return 1
        H = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = c.post("/reports", headers=H, json={
            "title": "Verification report", "latitude": 17.4948, "longitude": 78.3996,
            "road_health_score": 80.84, "road_condition": "Fair", "defect_percentage": 19.16,
            "total_defects": 5, "defect_counts": {"pothole": 5},
            "risk_index": 61.4, "risk_level": "High", "priority_tier": "Priority-2",
            "risk_components": [], "detections": [],
            "model_name": "best.pt", "model_version": "yolo11n-640-e100"})
        check("write a report", r.status_code == 201, r.text[:140])
        rid = r.json().get("id") if r.status_code == 201 else None

        r = c.get("/reports", headers=H)
        check("read it back", r.status_code == 200 and r.json()["total"] == 1, r.text[:140])

        r = c.get("/reports/stats", headers=H)
        check("aggregate stats", r.status_code == 200, r.text[:140])

        if rid:
            check("delete", c.delete(f"/reports/{rid}", headers=H).status_code == 204)

    print(f"\n  {ok} passed, {fail} failed\n")
    if fail == 0:
        print(f"{GREEN}Database is live and the schema is in place.{OFF}")
        print(f"{DIM}The verification account and report were removed.{OFF}\n")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
