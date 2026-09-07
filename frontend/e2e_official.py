"""
The official's queue, driven in a real browser against the live stack.

Runs two browser contexts side by side: a citizen who files a complaint, and
an official who acts on it. The point is the handover — the citizen must see
the status the official set, on a screen the citizen never had the buttons to
reach.

Needs the backend started with OFFICIAL_EMAILS including @ghmc.gov.in.
"""

import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

API = "http://127.0.0.1:8000"
APP = "http://127.0.0.1:5173"
CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

STAMP = int(time.time())
CITIZEN = f"cit{STAMP}@example.com"
OFFICIAL = f"eng{STAMP}@ghmc.gov.in"
PASSWORD = "queue-password-123"

ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {extra}")


def db(sql):
    out = subprocess.run(
        ["psql", "-h", "127.0.0.1", "-p", "5433", "-U", "postgres", "-d", "roadguard",
         "-tAc", sql], capture_output=True, text=True)
    return out.stdout.strip()


def sign_up(page, name, email):
    page.goto(APP + "/signup", wait_until="networkidle")
    page.wait_for_timeout(500)
    page.fill("#name", name)
    page.fill("#email2", email)
    page.fill("#pw2", PASSWORD)
    page.click("button:has-text('Create account')")
    page.wait_for_url("**/app", timeout=20000)
    page.wait_for_timeout(1200)


def file_report(page, title, submit=True):
    """Create a report through the API from inside the signed-in page."""
    return page.evaluate("""async ([title, submit]) => {
        const t = localStorage.getItem('roadguard_token');
        // A real JPEG, made in the page: the PDF is rebuilt from the stored
        // photograph, so filing without one only tests the refusal path.
        const cv = document.createElement('canvas');
        cv.width = 640; cv.height = 480;
        const g = cv.getContext('2d');
        g.fillStyle = '#5a5a5a'; g.fillRect(0, 0, 640, 480);
        g.fillStyle = '#1a1a1a'; g.fillRect(120, 160, 180, 130);
        const b64 = cv.toDataURL('image/jpeg', 0.8).split(',')[1];
        const r = await fetch('%s/reports', {
            method: 'POST',
            headers: {Authorization: 'Bearer ' + t, 'Content-Type': 'application/json'},
            body: JSON.stringify({
                title, latitude: 17.4948, longitude: 78.3996,
                road_health_score: 61.2, road_condition: 'Poor',
                defect_percentage: 38.8, total_defects: 4,
                defect_counts: {pothole: 4},
                risk_index: 77.3, risk_level: 'High', priority_tier: 'Priority-2',
                response_window: 'Remediate within 7 days',
                model_name: 'best.pt', model_version: 'yolo11n-935e809b',
                detections: [{id: 1, class_id: 0, class_name: 'pothole',
                              confidence: 0.83, bbox: [120, 160, 300, 290],
                              area: 23400, area_percentage: 7.6,
                              severity: 'High', severity_rank: 2,
                              severity_colour: '#E8833A',
                              recommended_action: 'Patch within the week.'}],
                image_base64: b64, image_mime: 'image/jpeg',
                image_width: 640, image_height: 480,
                submit,
            }),
        });
        return (await r.json()).reference;
    }""" % API, [title, submit])


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CH)

    # -- 1. the citizen files ------------------------------------------------
    print("\n1. Citizen")
    cit_ctx = browser.new_context(viewport={"width": 1320, "height": 950})
    cit = cit_ctx.new_page()
    errors = []
    cit.on("pageerror", lambda e: errors.append(str(e)))
    sign_up(cit, "Citizen", CITIZEN)

    ref_filed = file_report(cit, "Filed complaint", True)
    ref_draft = file_report(cit, "Private draft", False)
    check("citizen filed one and drafted one",
          bool(ref_filed) and bool(ref_draft), f"{ref_filed} / {ref_draft}")

    cit.goto(APP + "/app/reports", wait_until="networkidle")
    cit.wait_for_timeout(1500)
    check("citizen sees no Queue link",
          cit.get_by_role("link", name="Queue").count() == 0)
    cit.goto(APP + "/app/queue", wait_until="networkidle")
    cit.wait_for_timeout(1500)
    check("citizen visiting /app/queue is bounced to the dashboard",
          cit.url.rstrip("/").endswith("/app"), cit.url)

    # -- 2. the official signs in --------------------------------------------
    print("\n2. Official")
    off_ctx = browser.new_context(viewport={"width": 1320, "height": 950},
                                  accept_downloads=True)
    off = off_ctx.new_page()
    off.on("pageerror", lambda e: errors.append(str(e)))
    sign_up(off, "Engineer", OFFICIAL)

    check("the allow-listed domain got the official role",
          db(f"select role from users where email = '{OFFICIAL}'") == "official")
    check("official sees the Queue link",
          off.get_by_role("link", name="Queue").count() >= 1)

    off.click("a[href='/app/queue']")
    off.wait_for_timeout(2500)
    body = off.content()
    check("the filed complaint is in the queue", ref_filed in body, ref_filed)
    check("the citizen's draft is NOT", ref_draft not in body, ref_draft)
    check("the queue says why drafts are absent", "not a complaint" in body)
    off.screenshot(path="q1_queue.png", full_page=True)

    # -- 3. acting on it ------------------------------------------------------
    print("\n3. Acting")
    card = off.locator(".glass-hover").filter(has_text=ref_filed)
    check("the card for this complaint is findable", card.count() == 1,
          f"{card.count()} cards match {ref_filed}")
    card.get_by_role("button", name="Acknowledge").click()
    off.wait_for_timeout(2500)
    check("database records the acknowledgement",
          db(f"select status from reports where reference = '{ref_filed}'") == "Acknowledged")

    off.click("text=In progress")
    off.wait_for_timeout(2000)
    check("it moved to the In progress tab", ref_filed in off.content())

    card = off.locator(".glass-hover").filter(has_text=ref_filed)
    with off.expect_download(timeout=60000) as dl:
        card.get_by_role("button", name="PDF").click()
    check("official can pull the complaint document",
          open(dl.value.path(), "rb").read(5) == b"%PDF-")

    off.locator(".glass-hover").filter(has_text=ref_filed) \
       .get_by_role("button", name="Mark resolved").click()
    off.wait_for_timeout(2500)
    check("database records the resolution",
          db(f"select status from reports where reference = '{ref_filed}'") == "Resolved")
    off.screenshot(path="q2_resolved.png", full_page=True)

    # -- 4. the citizen sees it ----------------------------------------------
    print("\n4. Back to the citizen")
    cit.goto(APP + "/app/reports", wait_until="networkidle")
    cit.wait_for_timeout(2000)
    check("the citizen's screen shows Resolved",
          "Resolved" in cit.content())
    check("and attributes it to the authority",
          "set by the authority" in cit.content())
    check("the citizen still has no Resolve button",
          cit.get_by_role("button", name="Mark resolved").count() == 0)
    cit.screenshot(path="q3_citizen_view.png", full_page=True)

    # -- 5. limits -------------------------------------------------------------
    print("\n5. Limits")
    code = off.evaluate("""async (ref) => {
        const t = localStorage.getItem('roadguard_token');
        const list = await (await fetch('%s/reports?mine=false',
            {headers: {Authorization: 'Bearer ' + t}})).json();
        const row = list.items.find(i => i.reference === ref);
        const r = await fetch(`%s/reports/${row.id}/status`, {
            method: 'PATCH',
            headers: {Authorization: 'Bearer ' + t, 'Content-Type': 'application/json'},
            body: JSON.stringify({status: 'Draft'})});
        return r.status;
    }""" % (API, API), ref_filed)
    check("an official cannot un-file a citizen's complaint (403)", code == 403, f"got {code}")

    check("no page errors", not errors, str(errors[:3]))
    browser.close()

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
