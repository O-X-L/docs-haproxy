# haproxy-dconv (vendored)

This directory contains a **verbatim copy** of the `parser/` package from [`cbonte/haproxy-dconv`](https://github.com/cbonte/haproxy-dconv), vendored for licensing and reproducibility.

- **Upstream project:** https://github.com/cbonte/haproxy-dconv
- **License:** Apache-2.0 (see `LICENSE`)
- **Attribution:** Copyright 2012 Cyril Bonté (see `NOTICE`)
- **Vendored commit:** see `COMMIT`

The parser here is kept **unmodified** as the reference implementation and
attribution target. This project's RST conversion logic lives in `../../renderer/`
and adapts (ports) the upstream detection patterns; those files carry their own
attribution headers pointing back to this upstream.

The upstream parser is entangled with Mako/HTML rendering and is therefore not
used as a runtime dependency. It is retained for license compliance and as the
source of truth for the detection logic.
