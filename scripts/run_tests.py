"""Run cumulative tests with their original colocated layout, outside the checkout."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pattern', default='test_*.py')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='storagescope-tests-') as tmp:
        checkout = Path(tmp) / 'checkout'
        shutil.copytree(root, checkout, ignore=shutil.ignore_patterns(
            '.git', '__pycache__', '.venv', '.build-venv', '.build-stage',
            '.pytest_cache', '.publish-pending', '.publish-backup'))
        stage = checkout / '03-Sources'
        for folder in ('02-Compilation-Windows', '04-Tests-et-Qualification'):
            for path in (checkout / folder).iterdir():
                if path.is_file() and (folder == '02-Compilation-Windows'
                                       or path.match('test_*.py')):
                    shutil.copy2(path, stage / path.name)
        shutil.copytree(checkout / '.github', stage / '.github', dirs_exist_ok=True)
        shutil.copy2(checkout / '07-Manifestes/VERSION', stage / 'VERSION')
        return subprocess.run([
            sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', '.', '-p', args.pattern], cwd=stage).returncode


if __name__ == '__main__':
    sys.exit(main())
