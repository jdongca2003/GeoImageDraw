#----------------------------------------
# This code is from https://github.com/rossant/smopy/blob/master/smopy.py
# Written by Cyrille Rossant (https://github.com/rossant)
#

import numpy as np

def deg2num(latitude, longitude, zoom, do_round=True):
    """Convert from latitude and longitude to tile numbers.

    If do_round is True, return integers. Otherwise, return floating point
    values.

    Source: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    lat_rad = np.radians(latitude)
    n = 2.0 ** zoom
    if do_round:
        f = np.floor
    else:
        f = lambda x: x
    xtile = f((longitude + 180.) / 360. * n)
    ytile = f((1.0 - np.log(np.tan(lat_rad) + (1 / np.cos(lat_rad))) / np.pi) /
              2. * n)
    if do_round:
        if isinstance(xtile, np.ndarray):
            xtile = xtile.astype(np.int32)
        else:
            xtile = int(xtile)
        if isinstance(ytile, np.ndarray):
            ytile = ytile.astype(np.int32)
        else:
            ytile = int(ytile)
    return (xtile, ytile)


def num2deg(xtile, ytile, zoom):
    """Convert from x and y tile numbers to latitude and longitude.

    Source: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    n = 2.0 ** zoom
    longitude = xtile / n * 360. - 180.
    latitude = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * ytile / n))))

    return (latitude, longitude)


def correct_box(box, z):
    """Get good box limits"""
    x0, y0, x1, y1 = box
    new_x0 = max(0, min(x0, x1))
    new_x1 = min(2**z - 1, max(x0, x1))
    new_y0 = max(0, min(y0, y1))
    new_y1 = min(2**z - 1, max(y0, y1))

    return (new_x0, new_y0, new_x1, new_y1)


def get_box_size(box):
    """Get box size"""
    x0, y0, x1, y1 = box
    sx = abs(x1 - x0) + 1
    sy = abs(y1 - y0) + 1
    return (sx, sy)


def determine_scale(latitude, z):
    """Determine the amount of meters per pixel

    :param latitude: latitude in radians
    :param z: zoom level

    Source: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Resolution_and_Scale

    """
    # For zoom = 0 at equator
    meter_per_pixel = 156543.03

    resolution = meter_per_pixel * np.cos(latitude) / (2 ** z)

    return resolution


def get_tile_box(box_latlon, z):
    """Convert a box in geographical coordinates to a box in
    tile coordinates (integers), at a given zoom level.

    box_latlon is lat0, lon0, lat1, lon1.

    """
    lat0, lon0, lat1, lon1 = box_latlon
    x0, y0 = deg2num(lat0, lon0, z)
    x1, y1 = deg2num(lat1, lon1, z)
    return (x0, y0, x1, y1)


def get_tile_coords(lat, lon, z):
    """Convert geographical coordinates to tile coordinates (integers),
    at a given zoom level."""
    return deg2num(lat, lon, z, do_round=False)


def extend_box(box_latlon, margin=.1):
    """Extend a box in geographical coordinates with a relative margin."""
    (lat0, lon0, lat1, lon1) = box_latlon
    lat0, lat1 = min(lat0, lat1), max(lat0, lat1)
    lon0, lon1 = min(lon0, lon1), max(lon0, lon1)
    dlat = max((lat1 - lat0) * margin, 0.0005)
    dlon = max((lon1 - lon0) * margin, 0.0005 / np.cos(np.radians(lat0)))
    return (
        max(lat0 - dlat, -80),
        max(lon0 - dlon, -180),
        min(lat1 + dlat, 80),
        min(lon1 + dlon, 180),
    )

