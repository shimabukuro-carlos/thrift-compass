import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs


def addr_to_coords(address):
    """Caroline's addr_to_coords: a one-line address to (lat, lon) with the Census geocoder."""
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urlencode(
        {"address": address, "benchmark": "Public_AR_Current", "format": "json"})
    with urllib.request.urlopen(url, timeout=10) as r:
        matches = json.load(r)["result"]["addressMatches"]
    if not matches:
        return None
    coords = matches[0]["coordinates"]
    return coords["y"], coords["x"]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        address = parse_qs(urlparse(self.path).query).get("address", [""])[0].strip()
        if not address:
            body, status = {"error": "Missing address"}, 400
        else:
            try:
                coords = addr_to_coords(address)
                body, status = ({"lat": coords[0], "lon": coords[1]}, 200) if coords else ({"error": "No match"}, 404)
            except Exception:
                body, status = {"error": "Geocoder not available"}, 502
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
