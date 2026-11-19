# HAProxy Documentation - Sphinx based & material-themed

Sphinx-based documentation site for [HAProxy-Community](https://github.com/haproxy/haproxy), converting the official plain-text manuals into reStructuredText and rendering them with the [sphinx-immaterial](https://github.com/jbms/sphinx-immaterial) theme.

----

## Build

```bash
pip install -r requirements.txt
bash html.sh
```

----

## Licensing

- **Repository / tooling** (scripts, `renderer/`, CI) — **Apache-2.0**.

- **Documentation content** (derived from the HAProxy manuals, which are
  GPL-2.0) — **GPL-2.0**. The generated site is a derivative of the upstream
  manuals and retains HAProxy attribution.

- The vendored `haproxy-dconv` parser remains under its own **Apache-2.0**
  license (see `vendor/haproxy-dconv/LICENSE` + `NOTICE`).
