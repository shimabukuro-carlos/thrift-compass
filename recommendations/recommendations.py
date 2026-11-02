import censusgeocode as cg
from geopy.distance import geodesic
import pandas as pd
from pathlib import Path

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

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "raw" / "overture.csv"
stores = pd.read_csv(CSV_PATH)
# drop rows if lat/lon cols are na
stores = stores.dropna(subset = ['lat', 'lon'])

def stores_in_range(coords: tuple[float, float], user_range: float = 5) -> pd.DataFrame | None:
    '''
    Calculate distance from user's coordinates to all stores in the dataset, then returns just stores
    within the user's specified range (5 miles default).
    '''
    if coords is not None:
        stores['miles_from_user'] = stores.apply(lambda row: geodesic(coords, (row.lat, row.lon)).miles, axis = 1)
        stores_in_range = stores[stores['miles_from_user'] <= user_range].sort_values(by = 'miles_from_user')
        return stores_in_range

    return None

if __name__ == "__main__":
    user_coords = addr_to_coords('200 Stadium Drive, Williamsburg, VA, 23185')
    store_recs_in_range = stores_in_range(user_coords)
    print(store_recs_in_range)
