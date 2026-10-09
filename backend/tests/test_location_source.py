"""
Where a complaint's coordinates came from, and whether that claim is true.

A gallery upload must be located where the photo was taken, not where the
citizen is when they upload it. The frontend reads the GPS a camera saved in
the photo; the server re-reads it here so a report can only say "from the
photo" when the photo actually agrees.
"""
import io

from PIL import Image

from app.utils.geotag import distance_m, read_photo_gps

NAGOLE = (17.3737, 78.555)          # where the synthetic photo was "taken"
KUKATPALLY = (17.4948, 78.3996)     # ~20 km away


def geotagged_jpeg(lat=NAGOLE[0], lon=NAGOLE[1], taken="2026:10:09 18:30:00",
                   width=800, height=600) -> bytes:
    def dms(v):
        v = abs(v)
        d = int(v); m = int((v - d) * 60); s = round(((v - d) * 60 - m) * 60, 4)
        return (float(d), float(m), s)
    exif = Image.Exif()
    exif[0x8825] = {1: "N" if lat >= 0 else "S", 2: dms(lat),
                    3: "E" if lon >= 0 else "W", 4: dms(lon)}
    exif[0x8769] = {0x9003: taken}
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (90, 90, 90)).save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def _post(client, image: bytes, lat, lon, source=None):
    data = {"latitude": str(lat), "longitude": str(lon)}
    if source is not None:
        data["location_source"] = source
    return client.post("/analyze?include_pdf=false&include_image=false",
                       files={"image": ("road.jpg", image, "image/jpeg")}, data=data)


# ------------------------------------------------------------- reading GPS --
def test_reads_the_gps_a_camera_saved():
    gps = read_photo_gps(geotagged_jpeg())
    assert gps is not None
    assert abs(gps.latitude - NAGOLE[0]) < 1e-4 and abs(gps.longitude - NAGOLE[1]) < 1e-4
    assert gps.taken_at == "2026:10:09 18:30:00"


def test_southern_and_western_references_are_negative():
    gps = read_photo_gps(geotagged_jpeg(-33.8688, -151.2093))
    assert gps.latitude < 0 and gps.longitude < 0


def test_photo_without_location_is_none_not_an_error(jpeg_bytes):
    assert read_photo_gps(jpeg_bytes) is None


def test_garbage_is_none():
    assert read_photo_gps(b"not an image") is None


def test_distance_is_sane():
    assert 19_000 < distance_m(*NAGOLE, *KUKATPALLY) < 22_000


# ------------------------------------------------------------- /analyze --
def test_photo_source_accepted_when_it_matches(client):
    r = _post(client, geotagged_jpeg(), *NAGOLE, source="photo")
    assert r.status_code == 200, r.text
    loc = r.json()["location"]
    assert loc["source"] == "photo"
    assert loc["source_label"].startswith("Photo's embedded GPS")
    assert loc["photo_taken_at"] == "2026:10:09 18:30:00"


def test_photo_source_refused_when_photo_has_no_gps(client, jpeg_bytes):
    r = _post(client, jpeg_bytes, *NAGOLE, source="photo")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "location_source_invalid"


def test_photo_source_refused_when_coordinates_disagree(client):
    # Claiming "from the photo" while sending somewhere 20 km away is exactly
    # the false statement the report must not carry.
    r = _post(client, geotagged_jpeg(), *KUKATPALLY, source="photo")
    assert r.status_code == 422
    assert r.json()["error"]["details"]["distance_m"] > 19_000


def test_map_pin_far_from_photo_is_allowed_but_warned(client):
    r = _post(client, geotagged_jpeg(), *KUKATPALLY, source="map")
    assert r.status_code == 200
    assert r.json()["location"]["source"] == "map"
    assert any("km from the location" in w for w in r.json()["warnings"])


def test_device_source_recorded(client, jpeg_bytes):
    r = _post(client, jpeg_bytes, *NAGOLE, source="device")
    assert r.status_code == 200
    assert r.json()["location"]["source_label"].startswith("Device GPS")


def test_unknown_source_rejected(client, jpeg_bytes):
    r = _post(client, jpeg_bytes, *NAGOLE, source="guess")
    assert r.status_code == 422


def test_pdf_states_where_the_location_came_from(client):
    from pypdf import PdfReader
    import base64
    r = client.post("/analyze?include_image=false&include_pdf=true",
                    files={"image": ("road.jpg", geotagged_jpeg(), "image/jpeg")},
                    data={"latitude": str(NAGOLE[0]), "longitude": str(NAGOLE[1]),
                          "location_source": "photo"})
    assert r.status_code == 200
    pdf = PdfReader(io.BytesIO(base64.b64decode(r.json()["report"]["data"])))
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "Location from" in text and "embedded GPS" in text
