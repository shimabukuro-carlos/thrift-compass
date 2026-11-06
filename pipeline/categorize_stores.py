import csv
import math
import os
import re
from collections import defaultdict
from urllib.parse import urlparse

# paths
OVERTURE_DATA = "data/raw/overture.csv"
OUTPUT = "data/store_categories.csv"

# if a store has multiple points in the same area, count the points within this mileage as one location
SAME_PLACE_DIST = 0.3
# if a store appears this many times or more in the dataset, count as a chain 
CHAIN_MIN_LOCATIONS = 3
# overture's confidence that a store exists should be at least this number to be counted as independent
INDEPENDENT_MIN_CONFIDENCE = 0.5

# independent stores also need phone number/website, and be the only place named this
#OWNERSHIPS = ['independent', 'chain', 'unknown']
# all stores have an ownership value, but tags are optional if they can be determined
#TAGS = ['charity', 'consignment', 'vintage']

"""Lists of related words:"""

# known chain stores
KNOWN_CHAINS = [
    (r"goodwill", "Goodwill"),
    (r"disabled american veterans|\bdav\b|davthrift", "DAV Thrift"),
    (r"chkd|children's hospital of the king", "CHKD Thrift"),
    (r"habitat|restore", "Habitat ReStore"),
    (r"plato'?s closet", "Plato's Closet"),
    (r"once upon a child", "Once Upon A Child"),
    (r"remix market", "Remix Market"),
    (r"salvation army", "Salvation Army"),
    (r"vincent de paul", "St. Vincent de Paul"),
    (r"savers|value village", "Savers / Value Village"),
    (r"clothes mentor", "Clothes Mentor"),
    (r"style encore", "Style Encore"),
    (r"uptown cheapskate", "Uptown Cheapskate"),
    (r"buffalo exchange", "Buffalo Exchange"),
]

# words related to charity stores
CHARITY_WORDS = (
    r"goodwill|disabled american veterans|\bdav\b|davthrift|chkd|children's hospital|"
    r"habitat|restore|boys (?:and|&) girls|rescue mission|humane society|salvation army|"
    r"vincent de paul|homeless|shelter|ministr|\bmission\b|parish|church|volunteer|"
    r"veterans|recovery|spouses|hospice|foundation"
)
# consignment-related words
CONSIGNMENT_WORDS = r"consign|resale"
# vintage-related words
VINTAGE_WORDS = r"vintage|antique|antiquit|curio|collectible|\bretro\b"

# functions for formatting:

def clean(text):
    """Strip whitespace on either end of string, convert curly quotes to regular single quotes to match patterns and stores."""
    # empty str if text is none
    return (text or "").replace("\u2019", "'").replace("\u2018", "'").strip()

def host(website):
    """Strip extra parts from a store's website to determine store types."""
    site = clean(website)
    # if no website for a store in the dataset
    if not site:
        return ""
    # if a website doesn't start with something like http://
    if "//" not in site:
        site = "//" + site
    # splits website url into parts, hostname is the domain
    return (urlparse(site).hostname or "").lower().removeprefix("www.")

def miles(a, b):
    '''Miles between two points.'''
    dy = (a[0] - b[0])*69
    dx = (a[1] - b[1])*69*math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)

def name_key(name):
    '''Convert common store names (that have slight variations) to one same name.'''
    n = clean(name).lower().replace("&", " and ")
    # replace llc, inc, co from string n with ""
    # also gets replaces commas, whitespace, and periods that could be before/after the string with ""
    n = re.sub(r",?\s*\b(llc|inc|co)\b\.?", "", n)
    # only keep what comes before a - in a store name (so "store - location" would just be "store")
    full_name = n
    n = re.split(r"\s+-\s*|-\s+", n)[0]
    
    # remove non alphanumeric characters, split remaining words in list
    words = re.sub(r"[^a-z0-9 ]", " ", n).split()
    # remove common words in a store name
    words = [w for w in words if w not in {"thrift", "store" ,"stores", "shop", "the", "and"}]
    return " ".join(words) or n or full_name

def count_locations(points):
    '''Number of stores farther than the specified radius of other points in the centers list.'''
    centers = []
    for p in points:
        # if p is within SAME_PLACE_DIST miles of a point, omit p from the list (treat like duplicate)
        if not any(miles(p, c) <= SAME_PLACE_DIST for c in centers):
            centers.append(p)
    return len(centers)

# functions for tagging and deciding ownership

def find_ownership(store, locations_by_key):
    '''Determines the ownership of a store: chain, unknown, or independent.'''
    text = f'{clean(store['name'])} {host(store['website'])}'.lower()

    for pattern, brand in KNOWN_CHAINS:
        if re.search(pattern, text):
            # assign store the chain type and reasoning
            return "chain", f"known chain: {brand}"

    brand = clean(store.get("brand"))
    if brand:
        return "chain", f"Overture brand: {brand}"

    n = locations_by_key[name_key(store['name'])]
    # assign chain if n stores have same name
    if n >= CHAIN_MIN_LOCATIONS:
        return 'chain', f'{n} locations with same name'

    # unknown if there are a couple stores, but not necessarily a chain
    if n > 1:
        return 'unknown', f'store name at {n} locations, cannot be determined as chain or independent'

    # store doesn't have a website or phone number, or overture confidence is very low
    problems = []
    if not (clean(store.get('website')) or clean(store.get('phone'))):
        problems.append('no website or phone')
    confidence = float(store.get('confidence') or 0)
    if confidence < INDEPENDENT_MIN_CONFIDENCE:
        problems.append(f'low Overture confidence ({confidence})')
    if problems:
        return 'unknown', 'problems: ' + ', '.join(problems)

    # last option, has a phone number/website and only store with same name in dataset
    return 'independent', 'sole location with no evidence of chain'

def find_tags(store):
    '''Determines the tag for a store: consignment, charity, vintage.'''
    name = clean(store['name']).lower()
    site = host(store['website'])
    tags = []
    reasons = []

    # tag as charity if name or website has charity words
    m = re.search(CHARITY_WORDS, f'{name} {site}')
    # m is none if no match returned, so shop isn't tagged
    if m:
        tags.append('charity')
        reasons.append(f'charity: {m.group()} in name or website')
    # tag as charity if .org is in the website
    elif site.endswith('.org'):
        tags.append('charity')
        reasons.append('charity: .org website')

    # tag as consignment if name has consignment words
    m = re.search(CONSIGNMENT_WORDS, name)
    if m:
        tags.append('consignment')
        reasons.append(f'consignment: {m.group()} in name')

    # tag as vintage if name has vintage words
    m = re.search(VINTAGE_WORDS, name)
    if m:
        tags.append('vintage')
        reasons.append(f'vintage: {m.group()} in name')

    return tags, reasons

        
# main section
def main():
    stores = [s for s in csv.DictReader(open(OVERTURE_DATA, encoding='utf-8')) if s['operating_status'] != 'permanently_closed']
    points = defaultdict(list)
    # add entry for each separate location
    for store in stores:
        points[name_key(store['name'])].append((float(store['lat']), float(store['lon'])))
    locations_by_key = {k: count_locations(v) for k, v in points.items()}

    rows = []
    for s in stores:
        ownership, ownership_reason = find_ownership(s, locations_by_key)
        tags, tag_reason = find_tags(s)
        # ownership_reason is string, tag_reason is list
        reasons = [ownership_reason] + tag_reason

        # new rows
        rows.append({
            'id': s['id'],
            'name': clean(s['name']),
            'address': clean(s['address']),
            'city': clean(s['city']),
            'ownership': ownership,
            'tags': '|'.join(tags),
            'reasons': '; '.join(reasons)
        })

    with open(OUTPUT, 'w', newline = '', encoding = 'utf-8') as f:
        # extrasaction will ignore extra keys that aren't in the dict and only write these specific fields (doesn't raise errors)
        w = csv.DictWriter(f, fieldnames = ['id', 'name', 'address', 'city', 'ownership', 'tags', 'reasons'], extrasaction = 'ignore')
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()