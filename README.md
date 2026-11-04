# NH-L9i bracket generator

Shop files for the fastening bar on a Noctua NH-L9i (this repo is named LH-N9i). The cooler uses two identical bars. The countersunk holes in the middle bolt to the heatsink. The threaded holes in the ears take the screws that come up through the motherboard.

On a normal LGA115x board those ear holes are 75 mm apart, and the heatsink holds the two bars 75 mm apart as well. The HP ProLiant MicroServer Gen8 uses an LGA1155 CPU with cooler holes at 75 × 65 mm. Each bar is generated at a 65 mm ear span so the pair can stay 75 mm apart.

The [Thermalright write-up](https://www.reddit.com/r/homelab/comments/1b1emib/hp_microserver_gen8_with_thermalright_cpu_cooler/) calls the stock pattern 65 × 65 mm and the Gen8 pattern 65 × 55 mm. Those sizes are wrong. The procedure is the one this generator builds directly: take 10 mm out of the 75 mm span, and keep the heatsink holes 23 mm apart. That is the same as shortening each arm by 5 mm. There are no leftover holes.

```
make bracket CHIPSET=lga115x
make bracket CHIPSET=hp-microserver-gen8
```

Each command writes `build/<chipset>/`:

| File | What it is |
| --- | --- |
| `bracket.step` | Formed solid, uniform thickness, plain holes |
| `bracket-flat.dxf` | Flat blank. Dashed lines are bend centers |
| `bracket-drawing.pdf` | Hole table and flat view |
| `quote-sendcutsend.txt` | Paste into a SendCutSend quote |
| `quote-pcbway.txt` | Paste into a PCBWay sheet-metal quote |
| `manifest.json` | Every dimension used, plus `order_ready` |

SendCutSend accepts the DXF (or the STEP). PCBWay accepts the STEP, the DXF, and the PDF. Both shops want plain holes in the file. Countersinks and M3 threads are selected on the quote form, and the text files spell those out. Order quantity is 2.

## Install

Python 3.11 or newer.

```
python3 -m pip install -e ".[dev]"
make test
make brackets
```

`make brackets` builds the stock 75 mm bar and the Gen8 65 mm bar. Those two commands wrote the shop files checked in under `build/`:

```
make bracket CHIPSET=lga115x
make bracket CHIPSET=hp-microserver-gen8
```

Each one runs `python3 -m bracketlab build --chipset <name> --cooler nh-l9i --out build` and fills `build/<chipset>/` with `bracket.step`, `bracket-flat.dxf`, `bracket-drawing.pdf`, `quote-sendcutsend.txt`, `quote-pcbway.txt`, and `manifest.json`. The STEP files are about 580 KB, so they are stored in git directly.

## Other hole patterns

A bar only sets one pitch. The heatsink sets the other, which is 75 mm on the NH-L9i. A square 75 mm pattern (LGA1150, LGA1151, LGA1155, LGA1156, LGA1200) reuses the stock bar. A rectangle that includes 75 mm spans the other side. A pattern with no 75 mm side stops, and the message names the override:

```
make bracket CHIPSET=lga1700 SPAN=78
make bracket CHIPSET=lga1700 ORTHOGONAL=78
```

`SPAN` forces the ear-hole pitch. `ORTHOGONAL` is the distance between the two bars when the cooler is not the stock NH-L9i. `CENTER` replaces the 23 mm heatsink spacing. `SPAN_X` and `SPAN_Y` replace the chipset pitches and must be passed together. `THICKNESS` is the sheet thickness in millimetres. `COOLER` selects a file in `coolers/`.

Presets live in `chipsets/`:

| Chipset | Holes |
| --- | --- |
| `lga115x` | 75 × 75 mm |
| `hp-microserver-gen8` | 75 × 65 mm |
| `lga1700`, `lga1851` | 78 × 78 mm |
| `lga2011-square` | 80 × 80 mm |
| `lga2011-narrow` | 56 × 94 mm |
| `am4` | 54 × 90 mm (AM5 uses the same holes) |

Patterns without a 75 mm side need `SPAN` or `ORTHOGONAL` because the stock heatsink cannot reach both pitches by changing arm length alone.

## Before you order

`order_ready` stays false until the assumed dimensions in `coolers/nh-l9i.yaml` and `materials/sendcutsend-5052-0125.yaml` are marked `measured` or `known`. The hole math still exports, so you can review the span and the 23 mm spacing before that.

Measure the stock bar and set the matching `status` field:

- `center_spacing_mm` — distance between the countersunk holes. The default is 23 mm.
- `web_width_mm` — width of the center section. The ears are semicircles of this width (`ear_diameter_mm` follows it).
- `bend_angle_deg` — angle of each ear from the web. One bend per side.
- `ear_height_mm` — add this if you measure the rise from the web midplane to the ear-hole center. Leave it unset and the ear is only as long as the bend clearance allows.
- `inside_bend_radius_in` — confirm against the current SendCutSend bend table for 5052 H32 at 0.125 in.

Two things the stock screws care about:

- The generated bar is 3.175 mm (0.125 in) 5052-H32, which SendCutSend can countersink and tap for M3. That is thicker than the stamped bar in the box. Check that the NH-L9i NM-IBT4 screws still have thread left.
- Each ear is a single bend, so the M3 thread is perpendicular to the ear and tilted by `bend_angle_deg` from vertical. The stock screw is vertical. Set `bend_angle_deg` from the real bar before relying on the tilt.

The default shop rules are the SendCutSend 0.125 in 5052 limits: M3 countersink depth within 60% of thickness, and holes kept at least 0.315 in (half of the 0.630 in die) off each bend line. A build that misses those rules stops without writing files.

## Contributing a chipset

Add `chipsets/<name>.yaml` with `name`, `holes_mm` as two numbers, and a `source`. Open an issue with the chipset form if you only have the measurements, or a pull request that includes the YAML. See [CONTRIBUTING.md](CONTRIBUTING.md).

This project is not affiliated with Noctua or HP. The license is [MIT](LICENSE).
