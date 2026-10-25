#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Clone the three pinned public source candidates into an Android checkout."""
import argparse
import json
import subprocess
from pathlib import Path


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args]).decode().strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--repositories-parent', type=Path,
                   default=Path(__file__).resolve().parents[2])
    a = p.parse_args()
    root = a.source_root.resolve()
    base = a.repositories_parent.resolve(strict=True)
    integration = Path(__file__).resolve().parents[1]
    rows = json.loads((integration / 'baseline.json').read_text())['device_repositories']
    plan = []
    for row in rows:
        source = base / row['repository']
        target = root / row['path']
        if git(source, 'rev-parse', 'HEAD') != row['commit']:
            raise ValueError('public input revision differs: ' + row['repository'])
        if git(source, 'status', '--porcelain', '--untracked-files=normal'):
            raise ValueError('public input has local edits: ' + row['repository'])
        if not target.resolve().is_relative_to(root):
            raise ValueError('target escapes source root')
        if target.exists():
            if git(target, 'rev-parse', 'HEAD') != row['commit'] or git(target, 'status', '--porcelain', '--untracked-files=normal'):
                raise ValueError('target exists with different revision/work: ' + row['path'])
        else:
            plan.append((source, target, row['commit']))
    for source, target, expected in plan:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--no-local', '--single-branch',
                        '--branch', 'lineage-23.2', str(source), str(target)], check=True)
        if git(target, 'rev-parse', 'HEAD') != expected:
            raise RuntimeError('source branch moved during clone; inspect the new checkout')
        # An existing recorded commit remains pinned even if upstream main advances.
    print(f'Staged {len(plan)} source repositories; existing matching checkouts retained')


if __name__ == '__main__':
    main()
