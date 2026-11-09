import csv
import json
import math
import re

# OpenStreetMap already has hours for some stores, so these cost no Google calls
DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
SAME_PLACE = 0.3  # miles
COMMON_WORDS = {"thrift", "store", "stores", "shop", "the", "and", "for", "of", "as"}


def miles(a, b):
    dy = (a[0] - b[0]) * 69
    dx = (a[1] - b[1]) * 69 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def name_words(name):
    return set(re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()) - COMMON_WORDS


def expand_days(text):
    """'Mo-Sa' or 'Tu, Th' -> list of day numbers, Sunday = 0"""
    days = []
    for part in text.replace(" ", "").split(","):
        if "-" in part:
            start, end = part.split("-")
            i = DAYS.index(start)
            while True:
                days.append(i)
                if DAYS[i] == end:
                    break
                i = (i + 1) % 7
        else:
            days.append(DAYS.index(part))
    return days


def to_minutes(clock):
    hour, minute = clock.split(":")
    return int(hour) * 60 + int(minute)


def parse_hours(text):
    """'Mo-Sa 09:00-20:00; Su 12:00-17:00' -> [[open, close], ...] in minutes since Sunday midnight"""
    hours = []
    for rule in text.split(";"):
        match = re.fullmatch(r"\s*([A-Za-z, -]+?)\s+(\d\d:\d\d)-(\d\d:\d\d)\s*", rule)
        if not match:
            print("SKIPPED:", text)
            return []
        for day in expand_days(match.group(1)):
            start = day * 1440 + to_minutes(match.group(2))
            hours.append([start, day * 1440 + to_minutes(match.group(3))])
    return sorted(hours)


stores = [s for s in csv.DictReader(open("data/raw/overture.csv"))
          if s["operating_status"] != "permanently_closed"]

found = {}
for o in csv.DictReader(open("data/raw/osm.tsv"), delimiter="\t"):
    if not o["opening_hours"].strip():
        continue
    hours = parse_hours(o["opening_hours"])
    point = (float(o["@lat"]), float(o["@lon"]))
    matched = [s for s in stores
               if miles(point, (float(s["lat"]), float(s["lon"]))) <= SAME_PLACE
               and name_words(o["name"]) & name_words(s["name"])]
    if not matched:
        print("NO MATCH:", o["name"], "|", o["addr:city"])
    for s in matched:
        found[s["id"]] = hours
        print("MATCHED:", o["name"], "->", s["name"], "|", s["address"])

with open("data/store_hours.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "hours"])
    for store_id, hours in found.items():
        w.writerow([store_id, json.dumps(hours, separators=(",", ":"))])

print("Stores with free hours:", len(found))
