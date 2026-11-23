import json
import math
from http.server import BaseHTTPRequestHandler
from itertools import permutations

MAX_STORES = 6
MAX_BODY_BYTES = 10000

def _point(value):
    return float(value[0]), float(value[1])

def miles(a, b):
    '''straight-line distance between two points'''
    lat1, lon1, lat2, lon2 = (math.radians(x) for x in (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2*3958.8*math.asin(math.sqrt(h))

def plan_trip(stops, start = None):
    if not isinstance(stops, (list, tuple)) or not stops:
        raise ValueError("stops must be a list with at least one store")

    store_ids = []
    coords = []

    if start is not None:
        origin = _point(start)
    else:
        origin = None

    for i, s in enumerate(stops, start = 1):
        store_ids.append(s['id'])
        coords.append(_point([s.get('lat'), s.get('lon')]))

    dist_between_stores = [[miles(a,b) for b in coords] for a in coords]
    if origin is not None:
        dist_from_origin = [miles(origin, c) for c in coords]
    else:
        dist_from_origin = None

    best_order = None
    best_total = math.inf
    for order in permutations(range(len(stops))):
        # distance from first store in permutation to start location
        if origin:
            total = dist_from_origin[order[0]] 
        else:  # doesn't have a start location, so start directly at first store
            total = 0.0
        # distance from each store to the store after it in the order
        # looks up distances from dist_between_stores table
        total += sum(dist_between_stores[a][b] for a, b in zip(order, order[1:]))
        # avoid ties
        if total < best_total - 1e-9:
            best_order = order
            best_total = total

    if origin:
        legs = [dist_from_origin[best_order[0]]]
    else:
        legs = None
    legs += [dist_between_stores[a][b] for a, b in zip(best_order, best_order[1:])]
    return {'order': [store_ids[i] for i in best_order], 'legs': legs, 'total_miles': best_total}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                raise ValueError('Request too large')
            body = json.loads(self.rfile.read(length) or b"{}")
            result, status = plan_trip(body.get('stops'), body.get('start')), 200
        except ValueError as e:
            result, status = {'error': str(e)}, 400
        except Exception:
            result, status = {'error': 'Could not plan the trip'}, 500
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())


# if __name__ == '__main__':
#     # example/test trip
#     start = [37.27, -76.71]
#     stops = [{"id": "a", "lat": 37.30, "lon": -76.70},
#          {"id": "b", "lat": 37,    "lon": -76},
#          {"id": "c", "lat": 37.10, "lon": -76.40}]
#     print(plan_trip(stops, start))