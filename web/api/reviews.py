import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def minute_of_week(point):
    return point["day"] * 1440 + point["hour"] * 60 + point.get("minute", 0)


def weekly_hours(place):
    """Google's hours as [[open, close], ...] in minutes since Sunday midnight."""
    hours = []
    for period in place.get("regularOpeningHours", {}).get("periods", []):
        # a period with no close means open all the time
        if "close" not in period:
            return [[0, 10080]]
        start, end = minute_of_week(period["open"]), minute_of_week(period["close"])
        # Saturday night into Sunday morning
        if end <= start:
            end += 10080
        hours.append([start, end])
    return hours


def get_reviews(place_id):
    req = urllib.request.Request(
        f"https://places.googleapis.com/v1/places/{place_id}",
        headers={"X-Goog-Api-Key": os.environ["GOOGLE_PLACES_KEY"],
                 "X-Goog-FieldMask": "rating,userRatingCount,reviews,googleMapsUri,regularOpeningHours"})
    with urllib.request.urlopen(req, timeout=10) as r:
        place = json.load(r)
    return {
        "rating": place.get("rating"),
        "count": place.get("userRatingCount"),
        "url": place.get("googleMapsUri"),
        "hours": weekly_hours(place),
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