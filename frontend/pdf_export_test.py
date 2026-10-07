"""The Export PDF button must hand over the BACKEND's report, not a print-out."""
import io, os, sys, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

APP = "http://127.0.0.1:5173"
IMG = str(Path(__file__).resolve().parents[1] / "datasets/pothole/test/images/11_jpg.rf.7ef3d543d83c0f883b9145bb22c860a5.jpg")
CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ok = fail = 0
def check(l, c, x=""):
    global ok, fail
    if c: ok += 1; print(f"  PASS  {l}")
    else: fail += 1; print(f"  FAIL  {l}  {x}")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH)
    pg = b.new_context(viewport={"width": 1400, "height": 950}, accept_downloads=True).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    pg.goto(APP + "/signup", wait_until="networkidle"); pg.wait_for_timeout(600)
    pg.fill("#name", "PDF Tester")
    pg.fill("#email2", f"pdf{int(time.time())}@example.com")
    pg.fill("#pw2", "pdf-export-password-1")
    pg.click("button:has-text('Create account')")
    pg.wait_for_url("**/app", timeout=20000)

    pg.goto(APP + "/app/upload", wait_until="networkidle"); pg.wait_for_timeout(700)
    pg.set_input_files("#photo", IMG)
    pg.fill("#lat", "17.4948"); pg.fill("#lon", "78.3996")
    pg.click("button:has-text('Analyse road')")
    pg.wait_for_url("**/app/result", timeout=90000)
    pg.wait_for_timeout(2500)

    with pg.expect_download(timeout=60000) as dl:
        pg.get_by_role("button", name="Export PDF").click()
    d = dl.value
    data = open(d.path(), "rb").read()

    check("a PDF was downloaded", data[:5] == b"%PDF-", data[:20])
    check("named as a road health report",
          d.suggested_filename.startswith("road_health_report_"), d.suggested_filename)

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join(pp.extract_text() or "" for pp in reader.pages)

    # The tell-tale of the browser print path.
    check("NOT the browser's print output",
          "about:blank" not in text.lower(), "still printing the page")

    # Things only the ReportLab report has.
    for label, needle in [
        ("risk assessment section", "ROAD RISK ASSESSMENT"),
        ("weighted risk components", "REMEDIATION URGENCY"),
        ("geospatial telemetry panel", "GEOSPATIAL"),
        ("municipal routing panel", "MUNICIPAL JURISDICTION"),
        ("the grievance statement", "Official Citizen Grievance Statement"),
        ("the defect inventory", "DEFECT"),
        ("the annotated evidence page", "VISUAL EVIDENCE"),
        ("the detector it came from", "yolo11n-"),
    ]:
        check(label, needle.lower() in text.lower(), f"missing {needle!r}")

    check("more than one page", len(reader.pages) >= 3, f"{len(reader.pages)} pages")
    check("no page errors", not errs, str(errs[:2]))
    open(os.path.join(tempfile.gettempdir(), "export_from_ui.pdf"), "wb").write(data)
    b.close()

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
