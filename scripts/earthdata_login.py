"""User-run interactive Earthdata login, then start a local authenticated app.

Credentials are not persisted. The short-lived token is passed only in the
child process environment, never in command-line arguments or a file.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8512)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        print('Run this script yourself in an interactive terminal. Do not send credentials in chat.')
        return 1
    import earthaccess
    try:
        auth = earthaccess.login(strategy='interactive', persist=False)
        if not auth.authenticated:
            print('Earthdata authentication did not succeed.')
            return 1
        token = auth.token["access_token"]
    except Exception:
        # Authentication exceptions may contain private server/request details.
        print('Earthdata Login failed. Check your account and connection, then retry.')
        return 1
    env = os.environ.copy()
    env['EARTHDATA_TOKEN'] = token
    env.pop('EARTHDATA_USERNAME', None)
    env.pop('EARTHDATA_PASSWORD', None)
    root = Path(__file__).resolve().parents[1]
    print(f'Login succeeded. Starting TrendLens locally at http://127.0.0.1:{args.port}')
    print('Select NASA Giovanni live (point). Keep this terminal open; Ctrl+C stops the app.')
    try:
        return subprocess.call([sys.executable, '-m', 'streamlit', 'run', str(root / 'app.py'),
            '--server.address', '127.0.0.1', '--server.port', str(args.port),
            '--server.headless', 'true', '--browser.gatherUsageStats', 'false'], cwd=root, env=env)
    except KeyboardInterrupt:
        return 0
    finally:
        env.pop('EARTHDATA_TOKEN', None)


if __name__ == '__main__':
    sys.exit(main())
