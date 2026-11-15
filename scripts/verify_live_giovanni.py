"""Opt-in live checks of the documented Giovanni point service.

No observations or output CSV are generated when authentication/retrieval fails.
Use --interactive in your own terminal; passwords/tokens are never printed.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import annualize_monthly
from giovanni import VARIABLE, configured_variables, load_giovanni


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--catalogue-only', action='store_true')
    parser.add_argument('--start', type=int, default=2020)
    parser.add_argument('--end', type=int, default=2020)
    parser.add_argument('--latitude', type=float, default=24.4539)
    parser.add_argument('--longitude', type=float, default=54.3773)
    args = parser.parse_args()
    old_token = os.environ.get('EARTHDATA_TOKEN')
    try:
        variables, catalogue = configured_variables()
        print(json.dumps({'catalogue': catalogue, 'requested_variable': VARIABLE,
                          'variable_listed': VARIABLE in variables}, indent=2))
        if VARIABLE not in variables:
            print('BLOCKED: requested variable is not configured. No alternate source was used.')
            return 1
        if args.catalogue_only:
            print('Catalogue check only; no measurements downloaded.')
            return 0
        if args.interactive:
            if not sys.stdin.isatty():
                print('Run --interactive yourself in a terminal, not through an agent tool.')
                return 1
            import earthaccess
            try:
                auth = earthaccess.login(strategy='interactive', persist=False)
                if not auth.authenticated:
                    raise RuntimeError
                os.environ['EARTHDATA_TOKEN'] = earthaccess.get_edl_token()['access_token']
            except Exception:
                print('BLOCKED: Earthdata Login failed. No authentication details are displayed.')
                return 1
        dataset = load_giovanni(args.latitude, args.longitude, args.start, args.end)
        annual = annualize_monthly(dataset.monthly)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'giovanni_source.csv').write_bytes(dataset.original)
        dataset.monthly.to_csv(args.output / 'giovanni_monthly.csv', index=False)
        annual.to_csv(args.output / 'giovanni_annual.csv', index=False)
        (args.output / 'giovanni_provenance.json').write_text(json.dumps(dataset.provenance, indent=2, allow_nan=False))
        print(json.dumps({'retrieval': 'PASS', 'valid_months': int(dataset.monthly.value.notna().sum()),
                          'complete_years': annual.year.tolist(), 'warnings': dataset.warnings,
                          'output': str(args.output.resolve())}, indent=2))
        return 0
    except ValueError as exc:
        print('BLOCKED:', str(exc))
        return 1
    finally:
        if old_token is None:
            os.environ.pop('EARTHDATA_TOKEN', None)
        else:
            os.environ['EARTHDATA_TOKEN'] = old_token


if __name__ == '__main__':
    sys.exit(main())
