"""
End-to-end check of the frontend wired to the REAL backend.

Everything here is deliberately checked against the server rather than the
screen where possible: a screen can render a report that was never stored.
The reload and the second browser context are the load-bearing tests — they
are the difference between "the app remembered" and "this browser remembered".

    python3 e2e_real.py

Needs: backend on 127.0.0.1:8000 (persistence on), dist/ built with
VITE_USE_MOCK=false and served on 127.0.0.1:5173.
"""

import json
import re
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

API = "http://127.0.0.1:8000"
APP = "http://127.0.0.1:5173"
IMG = "/home/claude/training/datasets/pothole/test/images/11_jpg.rf.7ef3d543d83c0f883b9145bb22c860a5.jpg"
CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

EMAIL = f"e2e{int(time.time())}@example.com"
PASSWORD = "e2e-password-123"

ok = fail = 0
notes = []


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {extra}")


def db(sql):
    """Query the database directly — the app's claims are checked against it."""
    out = subprocess.run(
        ["psql", "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", "roadguard",
         "-tAc", sql],
        capture_output=True, text=True)
    return out.stdout.strip()


def api(path, token=None):
    req = urllib.request.Request(API + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CH)
    ctx = browser.new_context(viewport={"width": 1320, "height": 950},
                              accept_downloads=True)
    pg = ctx.new_page()

    console_errors, api_calls = [], []
    pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: console_errors.append(f"PAGEERROR {e}"))
    pg.on("request", lambda r: api_calls.append((r.method, r.url)) if API in r.url else None)

    # -- 1. landing, in real mode --------------------------------------------
    print("\n1. Landing")
    pg.goto(APP + "/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    check("landing renders", pg.locator("h1").count() > 0)
    check("no demo badge in real mode", pg.locator("text=Demo data").count() == 0,
          f"found {pg.locator('text=Demo data').count()}")

    # -- 2. signup creates a real account ------------------------------------
    print("\n2. Signup")
    before = db("select count(*) from users")
    pg.goto(APP + "/signup", wait_until="networkidle")
    pg.wait_for_timeout(600)
    check("password hint is the real one (8+ chars)",
          "At least 8 characters" in pg.content())
    pg.fill("#name", "E2E Tester")
    pg.fill("#email2", EMAIL)
    pg.fill("#pw2", PASSWORD)
    pg.click("button:has-text('Create account')")
    pg.wait_for_url("**/app", timeout=20000)
    pg.wait_for_timeout(1500)
    after = db("select count(*) from users")
    check("a user row was written", int(after) == int(before) + 1, f"{before} -> {after}")
    check("password is hashed, not stored",
          db(f"select password_hash like '$2%' from users where email='{EMAIL}'") == "t")
    check("POST /auth/signup was called",
          any(m == "POST" and u.endswith("/auth/signup") for m, u in api_calls))
    token = pg.evaluate("() => localStorage.getItem('roadguard_token')")
    check("token stored", bool(token) and token.count(".") == 2)
    check("no user profile cached in localStorage",
          pg.evaluate("() => localStorage.getItem('roadguard_user')") is None)

    # -- 3. session survives a reload via /auth/me ---------------------------
    print("\n3. Session resume")
    api_calls.clear()
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(1800)
    check("still signed in after reload", "/app" in pg.url and "login" not in pg.url, pg.url)
    check("resumed by calling /auth/me, not by trusting a cache",
          any(u.endswith("/auth/me") for _, u in api_calls))
    check("dashboard empty-state, not demo rows",
          pg.locator("text=Demo data").count() == 0)
    check("dashboard asked the database for its totals",
          any(u.rstrip("/").endswith("/reports/stats") for _, u in api_calls))
    check("does not claim reports live in this browser",
          "in this browser" not in pg.content())
    pg.screenshot(path="r1_dashboard_empty.png", full_page=True)

    # -- 4. analyse runs the trained model -----------------------------------
    print("\n4. Analyse")
    pg.click("a[href='/app/upload']")
    pg.wait_for_timeout(700)
    check("no 'sample data' warning in real mode",
          "fixed sample data" not in pg.content())
    pg.set_input_files("#photo", IMG)
    pg.fill("#lat", "17.4948")
    pg.fill("#lon", "78.3996")
    api_calls.clear()
    pg.click("button:has-text('Analyse road')")
    pg.wait_for_url("**/app/result", timeout=60000)
    pg.wait_for_timeout(2000)
    check("POST /analyze was called",
          any(m == "POST" and "/analyze" in u for m, u in api_calls))
    rows = pg.locator("table tbody tr").count()
    check("model returned detections", rows > 0, f"{rows} rows")
    check("result is not badged as demo", pg.locator("text=Demo data").count() == 0)
    pg.screenshot(path="r2_result.png", full_page=True)

    # -- 5. filing writes to the database ------------------------------------
    print("\n5. File the report")
    reports_before = int(db("select count(*) from reports"))
    pg.click("button:has-text('File now')")
    pg.wait_for_timeout(2500)
    reports_after = int(db("select count(*) from reports"))
    check("a report row was written", reports_after == reports_before + 1,
          f"{reports_before} -> {reports_after}")
    row = db(f"select reference || '|' || status || '|' || model_version || '|' || total_defects "
             f"from reports order by created_at desc limit 1")
    check("stored as Submitted with provenance", "|Submitted|" in row, row)
    # A weights fingerprint, not "trained": arch + content hash, e.g.
    # yolo11n-935e809b. Retraining changes it, so a regenerated PDF that no
    # longer matches its report can be spotted.
    check("model version is a weights fingerprint, not a status word",
          re.fullmatch(r"[\w.-]+-[0-9a-f]{8}", row.split("|")[2] or "") is not None, row)
    check("photograph stored with the report",
          db("select image_bytes is not null from reports order by created_at desc limit 1") == "t")
    check("stored photograph is byte-identical to the file that was analysed",
          db("select encode(sha256(image_bytes),'hex') = image_sha256 "
             "from reports order by created_at desc limit 1") == "t")
    served = pg.evaluate("""async () => {
        const t = localStorage.getItem('roadguard_token');
        const list = await (await fetch('%s/reports', {headers:{Authorization:'Bearer '+t}})).json();
        const r = await fetch(`%s/reports/${list.items[0].id}/image`,
                              {headers:{Authorization:'Bearer '+t}});
        return [r.status, r.headers.get('content-type'), (await r.blob()).size];
    }""" % (API, API))
    check("GET /reports/{id}/image serves it back",
          served[0] == 200 and served[2] > 1000, str(served))

    # -- 6. the reports screen reads the server ------------------------------
    print("\n6. Reports screen")
    pg.goto(APP + "/app/reports", wait_until="networkidle")   # full reload, no client state
    pg.wait_for_timeout(2000)
    check("report visible after a cold load", pg.locator(".glass-hover").count() >= 1,
          f"{pg.locator('.glass-hover').count()} cards")
    check("shows the quotable reference, not a UUID",
          pg.locator("text=/RHA-\\d{8}-/").count() >= 1)
    check("no 'stays in this browser' claim in real mode",
          "this browser" not in pg.content().lower())
    # Exact match: the status filter has an "Acknowledged" chip, and a substring
    # match on "Acknowledge" hits it and reads as a bug that is not there.
    check("Acknowledge is not offered to a citizen",
          pg.get_by_role("button", name="Acknowledge", exact=True).count() == 0)
    check("Withdraw is offered instead", pg.locator("button:has-text('Withdraw')").count() == 1)
    pg.screenshot(path="r3_reports.png", full_page=True)

    # -- 6b. the complaint document can be got back --------------------------
    print("\n6b. Rebuild the PDF")
    check("a PDF button is offered on the card",
          pg.get_by_role("button", name="PDF").count() == 1)
    with pg.expect_download(timeout=60000) as dl:
        pg.get_by_role("button", name="PDF").click()
    download = dl.value
    path = download.path()
    head = open(path, "rb").read(5)
    check("clicking it downloads a real PDF", head == b"%PDF-", str(head))
    check("named by the reference, not the UUID",
          download.suggested_filename.startswith("road_health_report_RHA-"),
          download.suggested_filename)
    import os as _os
    check("has real content", _os.path.getsize(path) > 40_000,
          f"{_os.path.getsize(path)} bytes")

    # -- 6c. the dashboard counts what the database holds ---------------------
    print("\n6c. Dashboard totals")
    pg.goto(APP + "/app", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    db_total = db("select count(*) from reports r join users u on u.id = r.user_id "
                  f"where u.email = '{EMAIL}'")
    tiles = pg.locator("main .glass").first
    check("headline count matches the database",
          f">{db_total}<" in pg.content() or db_total in tiles.inner_text(),
          f"database says {db_total}")
    check("the filed report shows as an open grievance",
          "Open grievances" in pg.content())

    # -- 7. withdraw round-trips through the server --------------------------
    print("\n7. Withdraw")
    pg.goto(APP + "/app/reports", wait_until="networkidle")
    pg.wait_for_timeout(2000)
    api_calls.clear()
    pg.click("button:has-text('Withdraw')")
    pg.wait_for_timeout(1800)
    check("PATCH /status was called",
          any(m == "PATCH" and "/status" in u for m, u in api_calls))
    check("database says Draft",
          db("select status from reports order by created_at desc limit 1") == "Draft")
    check("screen agrees", pg.get_by_role("button", name="Submit", exact=True).count() == 1)

    # -- 8. the server refuses what the UI hides -----------------------------
    print("\n8. Server-side authority (the UI is not the only guard)")
    code = pg.evaluate("""async () => {
        const t = localStorage.getItem('roadguard_token');
        const list = await (await fetch('%s/reports', {headers:{Authorization:'Bearer '+t}})).json();
        const id = list.items[0].id;
        const r = await fetch(`%s/reports/${id}/status`, {
            method:'PATCH',
            headers:{Authorization:'Bearer '+t,'Content-Type':'application/json'},
            body: JSON.stringify({status:'Resolved'})});
        return r.status;
    }""" % (API, API))
    check("hand-rolled 'Resolved' is rejected with 403", code == 403, f"got {code}")

    # -- 9. map draws the stored report --------------------------------------
    print("\n9. Map")
    pg.goto(APP + "/app/map", wait_until="networkidle")
    pg.wait_for_timeout(5000)
    check("markers drawn from server rows",
          pg.locator("path.leaflet-interactive").count() >= 1,
          f"{pg.locator('path.leaflet-interactive').count()} markers")
    pg.screenshot(path="r4_map.png", full_page=True)

    # -- 10. profile copy is true in this mode -------------------------------
    print("\n10. Profile")
    pg.goto(APP + "/app/profile", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    body = pg.content()
    check("does not claim the session protects nothing",
          "protects nothing" not in body.lower())
    check("shows the signed-in email", EMAIL in body)
    pg.screenshot(path="r5_profile.png", full_page=True)

    # -- 11. a different browser sees the same account -----------------------
    print("\n11. Second browser (the real test of persistence)")
    ctx2 = browser.new_context(viewport={"width": 1320, "height": 950})
    pg2 = ctx2.new_page()
    pg2.goto(APP + "/login", wait_until="networkidle")
    pg2.wait_for_timeout(800)
    check("second browser starts signed out",
          pg2.evaluate("() => localStorage.getItem('roadguard_token')") is None)
    pg2.fill("#email", EMAIL)
    pg2.fill("#pw", PASSWORD)
    pg2.click("button:has-text('Sign in')")
    pg2.wait_for_url("**/app", timeout=20000)
    pg2.goto(APP + "/app/reports", wait_until="networkidle")
    pg2.wait_for_timeout(2000)
    check("the report filed in browser 1 is here in browser 2",
          pg2.locator("text=/RHA-\\d{8}-/").count() >= 1)
    pg2.screenshot(path="r6_second_browser.png", full_page=True)

    # -- 12. wrong password is refused, and says nothing extra ---------------
    print("\n12. Login failures")
    ctx3 = browser.new_context()
    pg3 = ctx3.new_page()
    pg3.goto(APP + "/login", wait_until="networkidle")
    pg3.fill("#email", EMAIL)
    pg3.fill("#pw", "definitely-not-the-password")
    pg3.click("button:has-text('Sign in')")
    pg3.wait_for_timeout(2000)
    wrong_pw = pg3.locator(".text-\\[color\\:var\\(--color-danger\\)\\], [role=alert]").all_inner_texts()
    check("wrong password does not sign in", "/login" in pg3.url, pg3.url)
    msg1 = " ".join(wrong_pw)
    pg3.fill("#email", "nobody-at-all@example.com")
    pg3.fill("#pw", "definitely-not-the-password")
    pg3.click("button:has-text('Sign in')")
    pg3.wait_for_timeout(2000)
    msg2 = " ".join(pg3.locator(".text-\\[color\\:var\\(--color-danger\\)\\], [role=alert]").all_inner_texts())
    check("unknown email gets the identical message (no account enumeration)",
          msg1 and msg1 == msg2, f"{msg1!r} vs {msg2!r}")

    # -- 13. cleanup ---------------------------------------------------------
    print("\n13. Console")
    real_errors = [e for e in console_errors
                   if "401" not in e and "Failed to load resource" not in e]
    check("no console errors", not real_errors, str(real_errors[:4]))

    browser.close()

print(f"\n{ok} passed, {fail} failed")
for n in notes:
    print("  note:", n)
sys.exit(1 if fail else 0)
