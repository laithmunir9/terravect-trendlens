"""Check an explicit release file set and optionally build a local-only archive.

The secret checks are heuristic, not proof that arbitrary text contains no secrets.
Never print matching values. Never include local environments, credentials or caches.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demos import DEMO_LOCATIONS, load_demo
from giovanni_snapshot import load_giovanni_snapshot

FILES = [
    'app.py', 'analysis.py', 'charts.py', 'dashboard.py', 'data_sources.py',
    'demos.py', 'giovanni.py', 'giovanni_snapshot.py', 'insights.py', 'release.py',
    'requirements.txt', 'requirements-dev.txt', 'requirements-public.txt',
    'cloud/streamlit_app.py', 'cloud/requirements.txt',
    '.streamlit/config.toml', '.gitignore', '.dockerignore', 'Dockerfile',
    'README.md', 'LICENSE', 'AI_USE.md', 'THIRD_PARTY_NOTICES.md',
    'docs/RELEASE_READINESS.md', 'docs/DEPLOYMENT.md', 'docs/verification_sources.json',
    'data/demos/README.md', 'data/demos/manifest.json',
    'data/demos/abu_dhabi_source.json', 'data/demos/oslo_source.json',
    'data/demos/giovanni_manifest.json', 'data/demos/giovanni_abu_dhabi_2001_2025.csv',
    'data/demos/giovanni_abu_dhabi_2020.csv', 'docs/GIOVANNI_ACQUISITION.md',
    'scripts/check_release.py', 'scripts/earthdata_login.py',
    'scripts/verify_live_power.py', 'scripts/verify_live_giovanni.py',
]
PATTERNS = {
    'private-key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'aws-access-key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'github-token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'openai-key': r'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}',
    'jwt': r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',
    'url-credentials': r'https?://[^\s/"\']+:[^\s/@"\']+@',
}


def scan(text):
    return [name for name, pattern in PATTERNS.items() if re.search(pattern, text)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, help='Optional local output; never uploads or deploys.')
    args = parser.parse_args()
    files = sorted(FILES + [str(p.relative_to(ROOT)) for p in (ROOT / 'tests').glob('test_*.py')])
    hashes, problems = {}, []
    for relative in files:
        path = ROOT / relative
        components = [ROOT.joinpath(*Path(relative).parts[:i])
                      for i in range(1, len(Path(relative).parts) + 1)]
        if not path.is_file() or any(p.is_symlink() for p in components):
            problems.append({'path': relative, 'issue': 'Missing file or symlink'})
            continue
        body = path.read_bytes()
        hits = scan(body.decode('utf-8'))
        if hits:
            problems.append({'path': relative, 'issue': hits})
        hashes[relative] = hashlib.sha256(body).hexdigest()
    for name in DEMO_LOCATIONS:
        load_demo(name, 2001, 2025)  # Existing NASA parser and source-hash verification.
    load_giovanni_snapshot()
    if problems:
        print(json.dumps({'status': 'FAIL', 'findings_without_values': problems}, indent=2))
        return 1
    if args.archive:
        if args.archive.resolve().is_relative_to(ROOT):
            raise ValueError('Write release archives outside the source tree.')
        with tarfile.open(args.archive, 'w:gz') as archive:
            for relative in files:
                archive.add(ROOT / relative, arcname=f'trendlens/{relative}', recursive=False)
    print(json.dumps({'status': 'PASS', 'files_checked': len(files),
                      'secret_pattern_findings': 0, 'hashes': hashes,
                      'limitations': 'Heuristic scan of release files only; Git history is not audited.',
                      'git_history_present': (ROOT / '.git').exists(),
                      'archive': str(args.archive) if args.archive else None}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
