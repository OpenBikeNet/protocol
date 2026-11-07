# OpenBikeNet Protocol

**Status: early draft. Nothing here is stable yet, and everything is open for discussion.**

This repository holds the open protocol that lets indoor cycling apps share riders, so riders
of different apps can meet on the same road. See the [organisation profile](https://github.com/OpenBikeNet)
for the overall goal.

## Contents

- [`spec/v0.md`](spec/v0.md): the specification (messages, transport, versioning).
- [`routes/`](routes/): shared route files with stable IDs, so that a position on a route means
  the same spot in every app. A route may also come as a GPX track (`routes/<id>.gpx`) for apps
  that only ride GPS routes; the JSON file stays the authority. `tools/velodrome_gpx.py` writes
  the velodrome's track.
- [`schemas/`](schemas/): JSON Schemas for routes and messages.
- [`examples/`](examples/): example messages, used as shared test data.
- [`apps.md`](apps.md): optional list of apps that speak the protocol.

Run `python3 tools/validate.py` to check routes, GPX tracks, schemas and examples.

## Servers

The reference server lives in [OpenBikeNet/server](https://github.com/OpenBikeNet/server). A
public instance runs at [openbikenet.cloud](https://openbikenet.cloud): apps connect to
`wss://openbikenet.cloud/v0`. Anyone can run their own server; apps choose which one to use.

## Stages

1. **Shared presence:** apps report their riders' positions on shared routes and see the
   riders of other apps. Each app keeps its own physics.
2. **Shared physics (later):** apps send power and cadence, and the server calculates speed
   with one common model, so fair races become possible.

## Taking part

If you build an indoor cycling app and want your riders to meet riders of other apps, join the
conversation in [Discussions](../../discussions). Ideas, needs and objections are all welcome,
especially from developers who already run multiplayer.

## License

- Specification and documentation text: [CC BY 4.0](LICENSE)
- Schemas, examples, test code and other code: [MIT](LICENSE-CODE)

Both are permissive, so any app can implement the protocol, open source or not.
