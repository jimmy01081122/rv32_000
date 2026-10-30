# Architecture diagrams

The [current B architecture map](../docs/ARCHITECTURE_MAP.md) was checked against
RTL at `59c6193` on 2026-10-30. [SVG](current-b/architecture.svg) and
[PNG](current-b/architecture.png) show the existing structure and numbered
candidate directions; orange labels are proposals, not implemented gains.
[Graphviz source](current-b/architecture.dot) and a
[Mermaid overview](current-b/architecture.mmd) are editable.

Render with Graphviz and Noto Sans CJK TC installed:

```sh
XDG_CACHE_HOME=/tmp/rv32-diagram-cache dot -Tsvg graph/current-b/architecture.dot -o graph/current-b/architecture.svg
XDG_CACHE_HOME=/tmp/rv32-diagram-cache dot -Tpng -Gdpi=110 graph/current-b/architecture.dot -o graph/current-b/architecture.png
```

## Historical image

[ap5a.png](ap5a.png) is an archived diagram named for the AP5A stage. It has not
been qualified as an exact diagram of current AP5B RTL. Use
[architecture_spec.md](../architecture_spec.md) for current queue, PRF-port,
frontend and memory-tracking details. The root README no longer presents this
image as the current implementation.
