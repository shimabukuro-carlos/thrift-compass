import censusgeocode as cg
from geopy.distance import geodesic
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
STORES_PATH = BASE_DIR / 'web' / 'data' / 'stores.json'
OWNERSHIP = ['chain', 'independent', 'unknown']
TAGS = ['consignment', 'charity', 'vintage']

def addr_to_coords(address: str) -> tuple[float, float] | None:
    '''
    Converts a user's provided address into latitude and longitude.
    Address str is a single line address in the format:
    'street, city, state, zip'
    '''
    try:
        result = cg.onelineaddress(address)

        if result:
            coords = result[0]['coordinates']
            user_coords = coords['y'], coords['x']
        else:
            print('No matches found.')
            return None
        return user_coords
    except Exception as e:
        print(f'Error {e}')

def tags_str_to_list(value) -> list[str]:
    """Convert tags string to a list."""
    if isinstance(value, str):
        return [t for t in value.split('|') if t]
    else:
        return []

def load_stores(path: Path = STORES_PATH) -> list[dict]:
    """Read stores.json into list of dictionaries."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def user_vals_to_list(category: str, values, allowed_vals: list[str]) -> list[str]:
    """Convert user picks into a list and don't allow unknown values."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    values = list(values)
    for v in values:
        if v not in allowed_vals:
            raise ValueError(f'Unknown {category} {v!r}. Allowed: {', '.join(allowed_vals)}')

    return values

def recommend_stores(location: tuple[float, float] | str, max_dist: float = 5, ownership: list[str] | None = None, tags: list[str] | None = None) -> list[dict]:
    """
    Recommend stores to user based on their max distance, ownership, and tags selected.
    location can be coordinates (lat, lon) or an address.
    max_dist is the distance limit (miles), defaults to 5 miles.
    ownership is any combination of chain, independent, unknown, or none.
    tags is any combination of consignment, vintage, charity, or none.

    """
    if max_dist is None or max_dist < 0:
        raise ValueError('Maximum distance must be 0 or more miles.')
    chosen_ownership = user_vals_to_list('ownership', ownership, OWNERSHIP)
    chosen_tags = user_vals_to_list('tags', tags, TAGS)

    if isinstance(location, str):
        coords = addr_to_coords(location)
        if coords is None:
            raise ValueError('No location found for {location}')
        else:
            if len(coords) != 2:
                raise ValueError('Coordinates must be address or (lat, lon) pair.')

    results = []
    for store in load_stores():
        if chosen_ownership and store['ownership'] not in chosen_ownership:
            # skip to next store if ownership doesn't match user pick
            continue
        # check for overlap between the user tags and the store tags - if no overlap (false), skip
        if chosen_tags and not (set(tags_str_to_list(store['tags'])) & set(chosen_tags)):
            # skip to next store if tags don't match user pick
            continue
        # distance from store to user coords
        miles = geodesic(coords, (store['lat'], store['lon'])).miles
        if miles <= max_dist:
            # unpack store info, add miles from user to dict
            results.append({**store, 'miles_from_user': miles})

    # sort by distance and then store name
    return sorted(results, key = lambda s: (s['miles_from_user'], s['name']))

# def stores_in_range(coords: tuple[float, float], user_range: float = 5) -> pd.DataFrame | None:
#     '''
#     Calculate distance from user's coordinates to all stores in the dataset, then returns just stores
#     within the user's specified range (5 miles default).
#     '''
#     if coords is not None:
#         stores['miles_from_user'] = stores.apply(lambda row: geodesic(coords, (row.lat, row.lon)).miles, axis = 1)
#         stores_in_range = stores[stores['miles_from_user'] <= user_range].sort_values(by = 'miles_from_user')
#         return stores_in_range

#     return None

if __name__ == "__main__":
    # user_coords = addr_to_coords('200 Stadium Drive, Williamsburg, VA, 23185')
    # store_recs_in_range = stores_in_range(user_coords)
    # print(store_recs_in_range)

    # example run - address, dist 5, no preference on ownership or tags
    recs = recommend_stores(
        '200 Stadium Drive, Williamsburg, VA, 23185',
        max_dist = 5,
        ownership = ['independent'],
        tags = []
        )

    Path("store_recs.json").write_text(json.dumps(recs, indent=2))

    for s in recs:
        print(f"{s['miles_from_user']:5.1f} mi  {s['name']} ({s['city']}, {s['ownership']}, {s['tags'] or 'no tags'})")
