from PIL import Image, ImageDraw
import numpy as np
import json
from .TileUtil import (
    extend_box,
    get_tile_box,
    correct_box,
    get_box_size,
    get_tile_coords,
)

def draw_text(img, xy, text, fillColor=None, font=None):
    d = ImageDraw.Draw(img)
    x = int(xy[0])
    y = int(xy[1])
    d.text((x,y), text, fill=fillColor, font=font)

def draw_points(img, xy, fill_color):
    d = ImageDraw.Draw(img)
    new_xy = [(int(p[0]), int(p[1])) for p in xy]
    d.point(new_xy, fill=fill_color)

def draw_line(img, xy, fill_color, width=2):
    d = ImageDraw.Draw(img)
    new_xy = [ (int(p[0]), int(p[1])) for p in xy]
    d.line(new_xy, fill=fill_color, width=width)

def draw_polygon(img, xy, fill_color, outlineColor=None, width=2):
    d = ImageDraw.Draw(img)
    new_xy = [ (int(p[0]), int(p[1])) for p in xy]
    d.polygon(new_xy, fill=fill_color, outline=outlineColor, width=width)

class GeoMapImageDraw(object):
    """
     Convert geographic coordinate box for a given zoom level to pixel image
     usage:
        geoImageDraw = GeoMapImageDraw( (lon_min, lat_min, lon_max, lat_max), z=z)
     where zoom level from 1 to maximum zoom 19

     color: what color to use for the image. The default is black. color string is supported
    """
    def __init__(self, lnglatBox, z=18, tilesize=256, maxtiles=16, margin=None, color=0):
        self.tilesize = tilesize
        self.maxtiles = maxtiles
        # (lat_min, lon_min, lat_max, lon_max)
        box = (lnglatBox[1], lnglatBox[0], lnglatBox[3], lnglatBox[2])
        if margin != None:
            box = extend_box(box, margin)
        self.box = box
        self.z = self.get_allowed_zoom(z)
        if z < self.z:
            self.z = z
        self.box_tile = get_tile_box(self.box, self.z)
        self.xmin = min(self.box_tile[0], self.box_tile[2])
        self.ymin = min(self.box_tile[1], self.box_tile[3])
        box = correct_box(self.box_tile, self.z)
        sx, sy = get_box_size(box)
        self.img = Image.new('RGB', (sx * tilesize, sy * tilesize), color=color)

    def get_allowed_zoom(self, z=18):
        box_tile = get_tile_box(self.box, z)
        box = correct_box(box_tile, z)
        sx, sy = get_box_size(box)
        if sx * sy >= self.maxtiles:
            z = self.get_allowed_zoom(z - 1)
        return z

    def geo_to_pixelCoord(self, lonlat):
        """Convert from geographical coordinates to pixels in the image.
        lonlat -- np.array([[lon, lat], [lon, lat],... ])
        """
        assert (isinstance(lonlat, np.ndarray))
        assert (lonlat.ndim == 2)
        assert (lonlat.shape[1] == 2)
        lon, lat = lonlat.T
        x, y = get_tile_coords(lat, lon, self.z)
        px = (x - self.xmin) * self.tilesize
        py = (y - self.ymin) * self.tilesize
        return np.c_[px, py]

    def get_pillow_image(self, boundedBox=None):
        """ Retrieve drawn image
        if boundedBox is not None, it will return cropped image bounded by it

        boundedBox -- tuple (lon_min, lat_min, lon_max, lat_max)
        """
        if boundedBox == None:
            return self.img
        lon_min, lat_min, lon_max, lat_max = boundedBox
        box_coords = np.array([[lon_min, lat_min],[lon_max, lat_max]], dtype=np.double)
        pixel_bbox = [(int(e[0]), int(e[1])) for e in self.geo_to_pixelCoord(box_coords)]
        left, bottom = pixel_bbox[0]
        right, top = pixel_bbox[1]
        width, height = self.img.size
        padding = 0
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(width - 1, right + padding)
        bottom = min(height - 1, bottom + padding)
        new_img = self.img.crop((left, top, right, bottom))
        return new_img

    def text(self, lon, lat, text, fillColor=None, font=None):
        coords = np.array([[lon,lat]], dtype=np.double)
        pixel_xy = self.geo_to_pixelCoord(coords)
        draw_text(self.img, pixel_xy[0], text, fillColor=fillColor, font=font)
        return self.img

    def draw_points(self, lonlat_points, fillColor=None):
        """ draw a list of points with [longitude, latitude] """
        if isinstance(lonlat_points, np.ndarray) and (lonlat_points.ndim == 2) and (lonlat_points.shape[-1] == 2):
            coords = lonlat_points
        else:
            coords = np.array(lonlat_points, dtype=np.double)
        pixel_xy = self.geo_to_pixelCoord(coords)
        draw_points(self.img, pixel_xy, fillColor)
        return self.img


    def draw_shape(self, geoJson_geom, fillColor=None, outlineColor=None):
        """ Map the geographical coordinates in geoJson geometry to tile coordinates and draw the geometry in tile images.
        Note: only support Polygon, MultiPolygon, LineString and MultiLineString. The polygon interior holes are not supported.
        """
        geometry_type = geoJson_geom['type']
        if geometry_type not in ['Polygon', 'LineString', 'MultiLineString', 'MultiPolygon']:
            raise Exception(f'shape type: {geometry_type} is not supported in draw_shape function')
        if geometry_type == 'LineString':
            coords = np.array(geoJson_geom['coordinates'], dtype=np.double)
            pixel_xy = self.geo_to_pixelCoord(coords)
            draw_line(self.img, pixel_xy, fillColor)
        elif geometry_type == 'MultiLineString':
            coords = geoJson_geom['coordinates']
            for line_coords in coords:
                coords = np.array(line_coords, dtype=np.double)
                pixel_xy = self.geo_to_pixelCoord(coords)
                draw_line(self.img, pixel_xy, fillColor)
        elif geometry_type == 'Polygon':
            coords = np.array(geoJson_geom['coordinates'][0], dtype=np.double)
            pixel_xy = self.geo_to_pixelCoord(coords)
            draw_polygon(self.img, pixel_xy, fillColor, outlineColor=outlineColor)
        elif geometry_type == 'MultiPolygon':
            coords = geoJson_geom['coordinates']
            for polygon_coords in coords:
                exterior_coords = polygon_coords[0]
                polygon_coords = np.array(exterior_coords, dtype=np.double)
                pixel_xy = self.geo_to_pixelCoord(polygon_coords)
                draw_polygon(self.img, pixel_xy, fillColor, outlineColor = outlineColor)
        return self.img


def geojson_coords(obj):
    """
    Yields the coordinates from a Feature or Geometry.

    source: https://raw.githubusercontent.com/jazzband/geojson/main/geojson/utils.py

    :param obj: A geometry or feature to extract the coordinates from.
    :type obj: Feature, Geometry
    :return: A generator with coordinate tuples from the geometry or feature.
    :rtype: generator
    """
    # Handle recursive case first
    if 'features' in obj:  # FeatureCollection
        for f in obj['features']:
            yield from geojson_coords(f)
    elif 'geometry' in obj:  # Feature
        yield from geojson_coords(obj['geometry'])
    elif 'geometries' in obj:  # GeometryCollection
        for g in obj['geometries']:
            yield from geojson_coords(g)
    else:
        if isinstance(obj, (tuple, list)):
            coordinates = obj
        else:
            coordinates = obj.get('coordinates', obj)
        for e in coordinates:
            if isinstance(e, (float, int)):
                yield tuple(coordinates)
                break
            for f in geojson_coords(e):
                yield f

def bounded_box(coord_list):
    x = [e[0] for e in coord_list]
    y = [e[1] for e in coord_list]
    return ( min(x), min(y), max(x), max(y))

def generate_image_from_geojson(geojson_feature_collection, z=19, lnglatbox=None, maxtiles=32,  backgroundColor=0, foregroundColor='#ffffff'):
    """ Draw geometries in geojson collections and return pillow image
    color can be specified in properties with key name 'color' (e.g. "properties": {"color": "#065535"}
    if color is not in the properties, the foregroundColor will be used
    lnglatbox: (lon_min, lat_min, lon_max, lat_max). If this value is None, bounded box will be calculated based on geometries within
    feature collection.
    """
    if lnglatbox == None:
        coord_list = list(geojson_coords(geojson_feature_collection))
        bbox = bounded_box(coord_list)
    else:
        bbox = lnglatbox
    box_map = GeoMapImageDraw(bbox, z=z, maxtiles=maxtiles, color=backgroundColor)
    features = geojson_feature_collection['features']
    for feature in features:
        fillColor = foregroundColor
        if 'properties' in feature:
            if 'color' in feature['properties']:
                fillColor= feature['properties']['color']
        box_map.draw_shape(feature['geometry'], fillColor=fillColor)
    img = box_map.get_pillow_image(boundedBox=bbox)
    return img

