"""Opt-in live verification. Saves genuine API responses outside the repository.

Run from the repository root:
  .venv/bin/python scripts/verify_live_power.py --output /tmp/trendlens-power-check
No synthetic substitute is used if requests fail.
"""
import argparse
import calendar
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import align_annual, annualize_monthly, calculate_trend
from charts import build_chart
from data_sources import load_power


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start', type=int, default=2001)
    parser.add_argument('--end', type=int, default=2025)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    annuals, records = [], {}
    for name, lat, lon in [('abu_dhabi', 24.4539, 54.3773), ('oslo', 59.9139, 10.7522)]:
        dataset = load_power(lat, lon, args.start, args.end)
        (args.output / f'{name}_source.json').write_bytes(dataset.original)
        raw = json.loads(dataset.original)['properties']['parameter']['T2M']
        annual = annualize_monthly(dataset.monthly)
        # Independent arithmetic against retained raw monthly numbers, with
        # calendar.monthrange rather than the aggregation implementation.
        assert dataset.provenance['source_units'] == 'C'
        for row in annual.itertuples():
            days = [calendar.monthrange(row.year, m)[1] for m in range(1, 13)]
            expected = sum(float(raw[f'{row.year}{m:02d}']) * days[m - 1] for m in range(1, 13)) / sum(days)
            assert abs(row.value - expected) < 1e-10
        assert len(dataset.monthly) == (args.end - args.start + 1) * 12
        annual.to_csv(args.output / f'{name}_annual.csv', index=False)
        dataset.monthly.to_csv(args.output / f'{name}_monthly.csv', index=False)
        records[name] = {'provenance': dataset.provenance, 'warnings': dataset.warnings,
                         'complete_years': annual.year.tolist(), 'raw_monthly_weighting_verified': True}
        annuals.append(annual)
    left, right = align_annual(*annuals)
    assert left.year.tolist() == right.year.tolist()
    for name, annual in zip(records, (left, right)):
        info = calculate_trend(annual)
        fig = build_chart(annual, info, name, args.start, args.end)
        assert tuple(fig.layout.xaxis.range) == (args.start - .5, args.end + .5)
        assert fig.data[0].x[0] == args.start and fig.data[0].x[-1] == args.end
        records[name]['comparison_statistics'] = {k: v for k, v in info.items() if k != 'fitted'}
        (args.output / f'{name}_provenance.json').write_text(json.dumps(records[name], indent=2, allow_nan=False))
    print(json.dumps({'checks': 'PASS', 'selected_years': [args.start, args.end],
                      'common_complete_years': left.year.tolist(),
                      'output': str(args.output.resolve()),
                      'sources': {k: v['provenance']['response_sha256'] for k, v in records.items()}}, indent=2))


if __name__ == '__main__':
    main()
