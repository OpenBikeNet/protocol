#!/usr/bin/env python3
"""Write the GPS tracks of Herne Hill Velodrome in London, one for each way round:

    python3 tools/herne_hill_gpx.py > routes/herne-hill-450.gpx
    python3 tools/herne_hill_gpx.py clockwise > routes/herne-hill-450-clockwise.gpx

Track racing goes anticlockwise, so that is herne-hill-450. herne-hill-450-clockwise is the
same track and the same start/finish line ridden the other way. It is a route of its own
because riders are placed by their distance from the line: on one route ID, riders going
opposite ways would be in the wrong places and coming head-on.

Herne Hill is an outdoor track, opened in 1891 and used for the 1948 Olympics, 450 m round on
the measuring line. Unlike velodrome-250, this is a real place, so apps that build their world
from a GPS track (their own map data and terrain) can draw the real surroundings.

The track is an oval of two straights and two semicircles, ridden anticlockwise. Its centre,
direction and bend radius were fitted to the track's outline in OpenStreetMap
(https://www.openstreetmap.org/relation/2524096); the inside edge fits the oval to within 0.7 m
on average. Only those few numbers come from the map, not the outline itself. The start/finish
line is on the home straight, just north of the pavilion at the south end of the stands, where
aerial imagery shows the white line across the track.

As in velodrome_gpx.py, the closed track, measured with the haversine formula on a sphere of
radius 6378.1 km, is the route's length to within a millimetre, and the last point is the first
point again. The points have no elevation: the track is flat, and apps with terrain data can
use their own heights for the ground there. The route files (.json) stay the authority.
The output is deterministic, so running this again gives the same file byte for byte.
"""
import math
import sys

LENGTH = 450.0
# Bend radius from the fit, in metres; the straights take up the rest of the length.
RADIUS = 45.3
STRAIGHT = (LENGTH - 2 * math.pi * RADIUS) / 2
BEND_STEP = 2.5
EARTH_RADIUS = 6378100.0
# The centre of the oval and the direction of its long axis, in degrees anticlockwise from east.
CENTRE = (51.45105, -0.09142)
AXIS = -76.8
# The start/finish line: this far from the middle of the home straight, against the direction
# of riding (north), just past the north end of the pavilion.
START_OFFSET = 13.0
DIGITS = 8


def oval():
    """The unscaled oval as (a, b) metres from its centre, a along the long axis, starting at the
    start/finish line on the home straight (b = +RADIUS) and riding anticlockwise."""
    half = STRAIGHT / 2
    start = -START_OFFSET
    steps = round(math.pi * RADIUS / BEND_STEP)
    points = [(start, RADIUS), (-half, RADIUS)]
    for i in range(1, steps):
        t = math.pi / 2 + math.pi * i / steps
        points.append((-half + RADIUS * math.cos(t), RADIUS * math.sin(t)))
    points += [(-half, -RADIUS), (half, -RADIUS)]
    for i in range(1, steps):
        t = -math.pi / 2 + math.pi * i / steps
        points.append((half + RADIUS * math.cos(t), RADIUS * math.sin(t)))
    points.append((half, RADIUS))
    return points


def to_lat_lng(points, scale):
    lat0, lng0 = CENTRE
    metres_per_degree = EARTH_RADIUS * math.pi / 180
    lng_factor = metres_per_degree * math.cos(math.radians(lat0))
    c, s = math.cos(math.radians(AXIS)), math.sin(math.radians(AXIS))
    out = []
    for a, b in points:
        x, y = (a * c - b * s) * scale, (a * s + b * c) * scale
        out.append((round(lat0 + y / metres_per_degree, DIGITS), round(lng0 + x / lng_factor, DIGITS)))
    return out


def haversine(p, q):
    lat1, lng1, lat2, lng2 = map(math.radians, (*p, *q))
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(a))


def track_length(track):
    return sum(haversine(p, q) for p, q in zip(track, track[1:]))


def herne_hill_track(clockwise=False):
    """The closed track as (lat, lng) points, the first point repeated at the end."""
    points = oval()
    points.append(points[0])
    scale = 1.0
    for _ in range(3):
        scale *= LENGTH / track_length(to_lat_lng(points, scale))
    track = to_lat_lng(points, scale)
    # The same points the other way round still start and end on the line.
    return track[::-1] if clockwise else track


def gpx(track, clockwise=False):
    route_id = 'herne-hill-450-clockwise' if clockwise else 'herne-hill-450'
    name = 'Herne Hill Velodrome (clockwise)' if clockwise else 'Herne Hill Velodrome'
    way = ', ridden clockwise' if clockwise else ''
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="OpenBikeNet tools/herne_hill_gpx.py"'
        ' xmlns="http://www.topografix.com/GPX/1/1">',
        '  <metadata>',
        f'    <name>{name}</name>',
        f'    <desc>OpenBikeNet shared route {route_id}: the 450 m outdoor track at Herne Hill,'
        f' London{way}. Centre, direction and bend radius fitted to OpenStreetMap'
        ' (© OpenStreetMap contributors).</desc>',
        f'    <link href="https://github.com/OpenBikeNet/protocol/blob/main/routes/{route_id}.json">',
        f'      <text>{route_id}</text>',
        '    </link>',
        '  </metadata>',
        '  <trk>',
        f'    <name>{name}</name>',
        '    <trkseg>',
    ]
    lines += [f'      <trkpt lat="{lat:.{DIGITS}f}" lon="{lng:.{DIGITS}f}"></trkpt>' for lat, lng in track]
    lines += ['    </trkseg>', '  </trk>', '</gpx>']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    args = sys.argv[1:]
    if args not in ([], ['clockwise']):
        sys.exit('usage: herne_hill_gpx.py [clockwise]')
    clockwise = args == ['clockwise']
    sys.stdout.write(gpx(herne_hill_track(clockwise), clockwise))
