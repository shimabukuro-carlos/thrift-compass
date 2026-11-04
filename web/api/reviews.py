import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def get_reviews(place_id):
    req = urllib.request.Request(
        f"https://places.googleapis.com/v1/places/{place_id}",
        headers={"X-Goog-Api-Key": os.environ["GOOGLE_PLACES_KEY"],
                 "X-Goog-FieldMask": "rating,userRatingCount,reviews,googleMapsUri"})
    with urllib.request.urlopen(req, timeout=10) as r:
        place = json.load(r)
    return {
        "rating": place.get("rating"),
        "count": place.get("userRatingCount"),
        "url": place.get("googleMapsUri"),
        "reviews": [{"author": rv["authorAttribution"]["displayName"],
                     "rating": rv["rating"],
                     "text": rv.get("text", {}).get("text", "")}
                    for rv in place.get("reviews", [])[:3]],
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        place_id = parse_qs(urlparse(self.path).query).get("id", [None])[0]
        if not place_id:
            body, status = {"error": "Missing id"}, 400
        else:
            try:
                body, status = get_reviews(place_id), 200
            except Exception:
                body, status = {"error": "Reviews not available"}, 502
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


if __name__ == "__main__":
    print(json.dumps(get_reviews("ChIJKTx6LCXlsIkRwrG-oSsRs5E"), indent=2))