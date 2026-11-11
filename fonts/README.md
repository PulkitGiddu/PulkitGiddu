# Fonts

Subset (printable ASCII plus arrows/symbols) WOFF builds of Instrument Serif,
Geist, and Geist Mono. Embedded into cards by `scripts/render_readme_cards.py`
as base64 data URIs (GitHub `<img>` SVGs cannot load external fonts).

All three are licensed under the SIL Open Font License 1.1
(https://openfontlicense.org).

Rebuild subsets with `pyftsubset` if you change the glyph set:

```bash
pyftsubset InstrumentSerif-Regular.ttf \
  --output-file=fonts/serif-400.woff --flavor=woff \
  --unicodes=U+0020-007E,U+00A0,U+2013,U+2014,U+2018,U+2019,U+201C,U+201D,U+2022,U+2192,U+2197
```
