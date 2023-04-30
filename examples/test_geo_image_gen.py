import json
from GeoImageDraw import GeoDraw

json_data = json.load(open("data.geojson", 'rt'))
bbox=(-122.4142502344969, 37.77962861208424, -122.4130318215348, 37.780245220041735)
img = GeoDraw.generate_image_from_geojson(json_data, lnglatbox=bbox, z=19)
img.save("out_image.png")
