# OpenBikeNet Protocol

**Status: early draft. Nothing here is stable yet, and everything is open for discussion.**

This repository holds the open protocol that lets indoor cycling apps share riders, so riders
of different apps can meet on the same road. See the [organisation profile](https://github.com/OpenBikeNet)
for the overall goal.

## Contents

- [`spec/v0.md`](spec/v0.md): the specification (messages, transport, versioning).
- [`routes/`](routes/): shared route files with stable IDs, so that a position on a route means
  the same spot in every app.
- [`schemas/`](schemas/): JSON Schemas for routes and messages.
- [`examples/`](examples/): example messages, used as shared test data.
- [`apps.md`](apps.md): optional list of apps that speak the protocol.

Run `python3 tools/validate.py` to check routes, schemas and examples.

The reference server will live in its own repository.

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
