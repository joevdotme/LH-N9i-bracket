# Contributing a hole pattern

A new motherboard pattern is a YAML file in `chipsets/`. The file stem and the `name` field match.

```yaml
name: example-board
sockets: [lga1155]
holes_mm: [75, 65]
notes: >
  What the two pitches are, and which side the bar should span.
source: >
  Where the spacing was measured or published.
```

`holes_mm` is the full cooler pattern, not the length of one bar. The generator spans the side that is not the heatsink's 75 mm spacing. If neither side is 75 mm, say so in `notes`. People then build it with `SPAN=` or `ORTHOGONAL=`.

Check the addition locally:

```
make test
make bracket CHIPSET=example-board
```

The pull request should include the YAML. The checklist on the pull request template is the rest: tests pass, and `make bracket` was run for the new name.

If you have a pitch and no YAML, open a chipset issue instead. Include both hole pitches and a source.
