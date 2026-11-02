import censusgeocode as cg
from geopy.distance import geodesic
import pandas as pd

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

