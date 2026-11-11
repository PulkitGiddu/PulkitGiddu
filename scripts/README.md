# Profile card scripts

- `fetch_contributions.py` — scrape public GitHub contribution calendar → `data/contributions.json`
- `render_readme_cards.py` — draw animated SVGs into `cards/`

```bash
pip install -r scripts/requirements.txt
python scripts/fetch_contributions.py
python scripts/render_readme_cards.py          # animated
STATIC=1 python scripts/render_readme_cards.py # end-state for screenshots
```

Hand-set achievement numbers live at the top of `render_readme_cards.py`.
