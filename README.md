# zreprenaria

Pandas/PyArrow pipeline that turns the French public company registry
(SIRENE / INSEE "stock" files) into a scored, address-enriched lead list.

Scripts are meant to run in order:

1. `scripts/filter_active.py` — keep active establishments
2. `scripts/build_leads.py` — join with NAF sections and build the working set
3. `scripts/enrich_addresses.py` — attach geocoded addresses
4. `scripts/final_leads.py` — apply the final scoring/filters
5. `scripts/export_deliverables.py` — write the CSV/Parquet deliverables

Large raw inputs and outputs (`data/raw`, `data/work`, `data/leads.db`) are not
published — download the source files from the official SIRENE/INSEE open-data
portal and place them under `data/raw/` using the filenames referenced in the
scripts.
