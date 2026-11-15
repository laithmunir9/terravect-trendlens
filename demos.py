"""Reproducible, explicitly selected NASA POWER snapshots; never a live fallback."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_sources import MonthlyDataset, parse_power_payload

DEMO_DIR = Path(__file__).resolve().parent / 'data' / 'demos'
DEMO_YEARS = (2001, 2025)
DEMO_LOCATIONS = ['Abu Dhabi, UAE', 'Oslo, Norway']
DEMO_SOURCE = 'NASA POWER saved demo'


def load_demo(name: str, start: int, end: int) -> MonthlyDataset:
    if (start, end) != DEMO_YEARS:
        raise ValueError('Saved demos cover exactly 2001–2025. Choose live POWER for another period.')
    try:
        manifest = json.loads((DEMO_DIR / 'manifest.json').read_text())
        record = manifest['records'][name]
        original = (DEMO_DIR / record['file']).read_bytes()
        provenance = record['provenance']
        if hashlib.sha256(original).hexdigest() != provenance['response_sha256']:
            raise ValueError('Saved NASA demo checksum mismatch. Restore the original snapshot before using it.')
        dataset = parse_power_payload(json.loads(original), start, end)
        if provenance['selected_years'] != [start, end]:
            raise ValueError('Saved NASA demo provenance does not match its selected years.')
        dataset.provenance.update(provenance)
        dataset.provenance['access_mode'] = 'Saved NASA response; not a live retrieval'
        dataset.provenance['snapshot_manifest'] = 'data/demos/manifest.json'
        dataset.original = original
        return dataset
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Saved NASA demo is unavailable or incomplete. Restore data/demos or choose live POWER.') from exc
