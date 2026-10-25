#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Apply reviewed platform series to exact clean bases; never reset user work."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--without-host-support', action='store_true')
    p.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    source = a.source_root.resolve(strict=True)
    patch_root = Path(__file__).resolve().parents[1] / 'patches'
    rows = json.loads((patch_root / 'index.json').read_text())['repositories']
    plan = []
    for row in rows:
        if a.without_host_support and row['path'] == 'build/soong':
            continue
        path = PurePosixPath(row['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('unsafe repository path')
        repo = (source / str(path)).resolve(strict=True)
        patch = (patch_root / row['file']).resolve(strict=True)
        if not repo.is_relative_to(source) or patch.parent != patch_root:
            raise ValueError('input escapes root')
        if hashlib.sha256(patch.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('patch checksum differs')
        for operation in ('rebase-apply', 'rebase-merge', 'CHERRY_PICK_HEAD', 'MERGE_HEAD'):
            state = Path(git(repo, 'rev-parse', '--git-path', operation).decode().strip())
            if not state.is_absolute():
                state = repo / state
            if state.exists():
                raise ValueError('repository has an in-progress Git operation: ' + row['path'])
        if git(repo, 'status', '--porcelain', '--untracked-files=normal').strip():
            raise ValueError('repository has local work: ' + row['path'])
        head = git(repo, 'rev-parse', 'HEAD').decode().strip()
        tree = git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip()
        if head == row['base']:
            plan.append((repo, patch, row))
        elif tree != row['expected_final_tree']:
            raise ValueError('repository is neither exact base nor expected result: ' + row['path'])
    if a.check_only:
        print(f'Preflight passed; {len(plan)} series pending, no source changes')
        return
    for repo, patch, row in plan:
        # No reset/rebase/force; git am preserves original author and message.
        subprocess.run(['git', '-C', str(repo), 'am', str(patch)], check=True)
        if git(repo, 'rev-parse', 'HEAD^{tree}').decode().strip() != row['expected_final_tree']:
            raise RuntimeError('applied tree differs: ' + row['path'])
    print(f'Applied {len(plan)} series; all resulting trees verified')


if __name__ == '__main__':
    main()
