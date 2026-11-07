#!/usr/bin/env python3
"""Check the routes and the invalid fixtures of the OpenBikeNet protocol.

Prints one line per problem as `<path>: <reason>` and exits 1 if there is any problem.
Paths are relative to the repository root.
"""
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
ROUTES = ROOT / "routes"
ROUTE_SCHEMA = ROOT / "schemas" / "route.schema.json"
INVALID_ROUTES = ROOT / "tools" / "fixtures" / "invalid-routes"
MISNAMED_ROUTES = ROOT / "tools" / "fixtures" / "misnamed-route"
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"
SPEC = ROOT / "spec" / "v0.md"
# GPX tracks next to a route are measured on this sphere (metres), the radius Incyclist uses.
EARTH_RADIUS = 6378100.0
GPX_TOLERANCE = 0.01
MESSAGE_SCHEMAS = ("app-message", "server-message", "stats")
# The 14 error codes of spec 7.6.
ERROR_CODES = {
    "hello_required", "hello_repeated", "invalid_message", "unknown_type", "invalid_app_id",
    "unknown_route", "invalid_room", "rider_exists", "unknown_rider", "invalid_value",
    "rate_limited", "limit_exceeded", "message_too_large", "too_many_errors",
}


def rel(path):
    return path.relative_to(ROOT).as_posix()


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_point(value):
    return isinstance(value, list) and len(value) == 2 and all(is_number(v) for v in value)


@lru_cache(maxsize=None)
def route_validator():
    return Draft202012Validator(json.loads(ROUTE_SCHEMA.read_text(encoding="utf-8")))


@lru_cache(maxsize=None)
def schema_validator(name):
    path = SCHEMAS / f"{name}.schema.json"
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def schema_problems(path, value, name):
    """Problem lines for `value` checked against schemas/<name>.schema.json."""
    return [
        f"{rel(path)}: {'/'.join(str(part) for part in error.path) or '(root)'}: {error.message}"
        for error in schema_validator(name).iter_errors(value)
    ]


def load_json(path):
    """Return (value, None) or (None, problem) for a file that is not readable JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as error:
        return None, f"{rel(path)}: cannot read JSON: {error}"


def check_route(path, route):
    name = rel(path)
    if not isinstance(route, dict):
        return [f"{name}: route must be a JSON object"]

    problems = []
    for error in route_validator().iter_errors(route):
        where = "/".join(str(part) for part in error.path) or "(root)"
        problems.append(f"{name}: {where}: {error.message}")

    profile = route.get("profile")
    if isinstance(profile, list) and len(profile) >= 2 and all(is_point(p) for p in profile):
        distances = [p[0] for p in profile]
        if distances[0] != 0:
            problems.append(f"{name}: first profile distance is {distances[0]}, expected 0")
        length = route.get("length")
        if is_number(length) and distances[-1] != length:
            problems.append(
                f"{name}: last profile distance is {distances[-1]}, expected length {length}"
            )
        for before, after in zip(distances, distances[1:]):
            if after <= before:
                problems.append(
                    f"{name}: profile distances do not strictly increase ({before}, then {after})"
                )
        if route.get("loop") is True and profile[0][1] != profile[-1][1]:
            problems.append(
                f"{name}: loop route starts at elevation {profile[0][1]} "
                f"but ends at {profile[-1][1]}"
            )

    if route.get("id") != path.stem:
        problems.append(f"{name}: file name does not match id {route.get('id')!r}")

    return problems


def haversine(p, q):
    lat1, lng1, lat2, lng2 = map(math.radians, (*p, *q))
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(a))


def check_gpx(path, routes):
    """A GPX track is only a convenience copy of a route: it must match the route's length and loop."""
    name = rel(path)
    route = routes.get(path.stem)
    if route is None:
        return [f"{name}: no route {path.stem!r} for this track"]
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        return [f"{name}: not valid XML: {error}"]
    track = [
        (float(point.get("lat")), float(point.get("lon")))
        for point in root.iter("{http://www.topografix.com/GPX/1/1}trkpt")
    ]
    if len(track) < 2:
        return [f"{name}: track has fewer than 2 points"]

    problems = []
    length = sum(haversine(p, q) for p, q in zip(track, track[1:]))
    if is_number(route.get("length")) and abs(length - route["length"]) > GPX_TOLERANCE:
        problems.append(f"{name}: track is {length:.3f} m long, expected {route['length']}")
    if route.get("loop") is True and track[0] != track[-1]:
        problems.append(f"{name}: loop route, but the track does not end at its first point")
    return problems


def spec_objects():
    """Yield (block number, line number, object) for every JSON object in the spec's json blocks."""
    text = SPEC.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    for number, match in enumerate(re.finditer(r"```json\n(.*?)```", text, re.S), 1):
        line = text.count("\n", 0, match.start(1)) + 1
        body = match.group(1)
        position = 0
        while True:
            while position < len(body) and body[position].isspace():
                position += 1
            if position >= len(body):
                break
            try:
                value, position = decoder.raw_decode(body, position)
            except ValueError as error:
                yield number, line, error
                break
            yield number, line, value


def check_valid(path, schema, problems):
    value, error = load_json(path)
    if error:
        problems.append(error)
    else:
        problems.extend(schema_problems(path, value, schema))


def check_messages(problems):
    missing = [n for n in MESSAGE_SCHEMAS if not (SCHEMAS / f"{n}.schema.json").is_file()]
    for name in missing:
        problems.append(f"schemas/{name}.schema.json: message schema is missing")
    if missing:
        return

    for folder, schema in (("app", "app-message"), ("server", "server-message")):
        for path in sorted((EXAMPLES / folder).glob("*.json")):
            check_valid(path, schema, problems)
    check_valid(EXAMPLES / "stats.json", "stats", problems)

    for path in sorted((EXAMPLES / "invalid" / "app").glob("*.json")):
        code, separator, _ = path.stem.partition("--")
        if not separator or code not in ERROR_CODES:
            problems.append(f"{rel(path)}: file name must start with an error code from spec 7.6 and --")
        value, error = load_json(path)
        if error:
            problems.append(error)
        elif not schema_problems(path, value, "app-message"):
            problems.append(f"{rel(path)}: expected invalid, but passed")

    examples = []
    for path in sorted([*EXAMPLES.rglob("*.json"), *ROUTES.glob("*.json")]):
        value, error = load_json(path)
        if not error:
            examples.append(value)
    for number, line, value in spec_objects():
        if isinstance(value, ValueError):
            problems.append(f"spec/v0.md:{line}: json block {number} is not valid JSON: {value}")
        elif value not in examples:
            problems.append(
                f"spec/v0.md:{line}: json block {number}: spec mismatch, "
                f"no file in examples/ or routes/ has the object {json.dumps(value)[:70]}"
            )


def main():
    problems = []

    if not ROUTE_SCHEMA.is_file():
        problems.append(f"{rel(ROUTE_SCHEMA)}: route schema is missing")
        return report(problems)

    ids = {}
    routes = {}
    for path in sorted(ROUTES.glob("*.json")):
        route, error = load_json(path)
        if error:
            problems.append(error)
            continue
        problems.extend(check_route(path, route))
        route_id = route.get("id") if isinstance(route, dict) else None
        if isinstance(route_id, str):
            if route_id in ids:
                problems.append(
                    f"{rel(path)}: duplicate id {route_id!r}, also in {rel(ids[route_id])}"
                )
            else:
                ids[route_id] = path
                routes[route_id] = route

    for path in sorted(ROUTES.glob("*.gpx")):
        problems.extend(check_gpx(path, routes))

    for folder in (INVALID_ROUTES, MISNAMED_ROUTES):
        for path in sorted(folder.glob("*.json")):
            route, error = load_json(path)
            if error or check_route(path, route):
                continue
            problems.append(f"{rel(path)}: expected invalid, but passed")

    check_messages(problems)
    return report(problems)


def report(problems):
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
