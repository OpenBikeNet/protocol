#!/usr/bin/env python3
"""Check the routes and the invalid fixtures of the OpenBikeNet protocol.

Prints one line per problem as `<path>: <reason>` and exits 1 if there is any problem.
Paths are relative to the repository root.
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
ROUTES = ROOT / "routes"
ROUTE_SCHEMA = ROOT / "schemas" / "route.schema.json"
INVALID_ROUTES = ROOT / "tools" / "fixtures" / "invalid-routes"
MISNAMED_ROUTES = ROOT / "tools" / "fixtures" / "misnamed-route"


def rel(path):
    return path.relative_to(ROOT).as_posix()


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_point(value):
    return isinstance(value, list) and len(value) == 2 and all(is_number(v) for v in value)


@lru_cache(maxsize=None)
def route_validator():
    return Draft202012Validator(json.loads(ROUTE_SCHEMA.read_text(encoding="utf-8")))


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


def main():
    problems = []

    if not ROUTE_SCHEMA.is_file():
        problems.append(f"{rel(ROUTE_SCHEMA)}: route schema is missing")
        return report(problems)

    ids = {}
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

    for folder in (INVALID_ROUTES, MISNAMED_ROUTES):
        for path in sorted(folder.glob("*.json")):
            route, error = load_json(path)
            if error or check_route(path, route):
                continue
            problems.append(f"{rel(path)}: expected invalid, but passed")

    return report(problems)


def report(problems):
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
