#!/usr/bin/env python3
"""Write routes/velodrome-250.gpx, a GPS track for apps that only ride GPS routes:

    python3 tools/velodrome_gpx.py > routes/velodrome-250.gpx

The oval is the one OpenRadlr draws: two 50 m straights and two semicircles, a point every
~2.5 m on the bends, starting at the start/finish line and riding anticlockwise. It is placed
at ANCHOR and scaled so the closed track, measured with the haversine formula on a sphere of
radius 6378.1 km (the radius Incyclist uses), is 250 m long to within a millimetre. The last
point is the first point again, so the track ends where it starts.

routes/velodrome-250.json stays the authority: the GPX is only a convenience. The output is
deterministic, so running this again gives the same file byte for byte.
"""
import math
import sys

LENGTH = 250.0
STRAIGHT = 50.0
BEND_STEP = 2.5
EARTH_RADIUS = 6378100.0
# The start/finish line. Round numbers on purpose: this is not a real velodrome.
ANCHOR = (47.0, 8.0)
DIGITS = 8


def oval():
    """The unscaled oval as (x, y) metres, x to the east and y to the north."""
    radius = (LENGTH - 2 * STRAIGHT) / (2 * math.pi)
    steps = round(math.pi * radius / BEND_STEP)
    points = [(0.0, 0.0), (STRAIGHT, 0.0)]
    for i in range(1, steps):
        a = -math.pi / 2 + math.pi * i / steps
        points.append((STRAIGHT + radius * math.cos(a), radius + radius * math.sin(a)))
    points += [(STRAIGHT, 2 * radius), (0.0, 2 * radius)]
    for i in range(1, steps):
        a = math.pi / 2 + math.pi * i / steps
        points.append((radius * math.cos(a), radius + radius * math.sin(a)))
    return points


def to_lat_lng(points, scale):
    lat0, lng0 = ANCHOR
    metres_per_degree = EARTH_RADIUS * math.pi / 180
    lng_factor = metres_per_degree * math.cos(math.radians(lat0))
    return [
        (round(lat0 + y * scale / metres_per_degree, DIGITS),
         round(lng0 + x * scale / lng_factor, DIGITS))
        for x, y in points
    ]


def haversine(p, q):
    lat1, lng1, lat2, lng2 = map(math.radians, (*p, *q))
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(a))


def track_length(track):
    return sum(haversine(p, q) for p, q in zip(track, track[1:]))


def velodrome_track():
    """The closed track as (lat, lng) points, the first point repeated at the end."""
    points = oval()
    points.append(points[0])
    scale = 1.0
    for _ in range(3):
        scale *= LENGTH / track_length(to_lat_lng(points, scale))
    return to_lat_lng(points, scale)


def gpx(track):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="OpenBikeNet tools/velodrome_gpx.py"'
        ' xmlns="http://www.topografix.com/GPX/1/1">',
        '  <metadata>',
        '    <name>Velodrome 250 m</name>',
        '    <desc>OpenBikeNet shared route velodrome-250: a flat 250 m loop.</desc>',
        '    <link href="https://github.com/OpenBikeNet/protocol/blob/main/routes/velodrome-250.json">',
        '      <text>velodrome-250</text>',
        '    </link>',
        '  </metadata>',
        '  <trk>',
        '    <name>Velodrome 250 m</name>',
        '    <trkseg>',
    ]
    lines += [f'      <trkpt lat="{lat:.{DIGITS}f}" lon="{lng:.{DIGITS}f}"><ele>0</ele></trkpt>'
              for lat, lng in track]
    lines += ['    </trkseg>', '  </trk>', '</gpx>']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    sys.stdout.write(gpx(velodrome_track()))
