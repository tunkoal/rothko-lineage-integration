#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Small fixture tests for copy/preflight helpers; no Android checkout or phone."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def main():
    scripts = Path(__file__).resolve().parent
    passed = []
    with tempfile.TemporaryDirectory(prefix='rothko-public-tools-') as directory:
        root = Path(directory)
        roots = {k: root / k for k in ('dump', 'artifacts', 'images')}
        for path in roots.values():
            path.mkdir()
        content = b'kernel fixture\n'
        (roots['images'] / 'dtbo.img').write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        recipe = {'schema_version': 1, 'firmware': 'fixture', 'files': [
            {'path': 'dtbo.img', 'input': 'images', 'source': 'dtbo.img',
             'sha256': digest, 'bytes': len(content), 'mode': '0644'}]}
        recipe_file = root / 'recipe.json'
        dump(recipe_file, recipe)
        def kernel(name, expected):
            output = root / name
            proc = subprocess.run([sys.executable, str(scripts / 'extract-kernel.py'),
                '--recipe', str(recipe_file), '--stock-dump', str(roots['dump']),
                '--stock-artifacts', str(roots['artifacts']), '--stock-images', str(roots['images']),
                '--output', str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if (proc.returncode == 0) != expected:
                raise RuntimeError('kernel fixture result differs: ' + name)
            return output
        output = kernel('valid', True)
        if (output / 'dtbo.img').read_bytes() != content:
            raise RuntimeError('kernel bytes differ')
        passed.append('kernel-valid')
        recipe['files'][0]['sha256'] = '0' * 64; dump(recipe_file, recipe)
        if kernel('bad-hash', False).exists():
            raise RuntimeError('preflight created output')
        passed.append('kernel-unknown-input-no-write')
        recipe['files'][0]['sha256'] = digest
        recipe['files'][0]['source'] = '../escape'; dump(recipe_file, recipe)
        if kernel('escape', False).exists():
            raise RuntimeError('escape created output')
        passed.append('kernel-source-traversal-no-write')
        recipe['files'][0]['source'] = 'dtbo.img'; dump(recipe_file, recipe)
        kernel('valid', False)
        if (output / 'dtbo.img').read_bytes() != content:
            raise RuntimeError('existing output changed')
        passed.append('kernel-existing-output-preserved')
        checkouts = {k: root / ('checkout-' + k) for k in ('device', 'vendor', 'kernel')}
        payloads = {k: root / ('payload-' + k) for k in checkouts}
        paths = {'device': 'prebuilts/ims/a.jar', 'vendor': 'proprietary/vendor/lib64/a.so',
                 'kernel': 'dtbo.img'}
        for kind, path in paths.items():
            checkouts[kind].mkdir(); dest = payloads[kind] / path
            dest.parent.mkdir(parents=True); dest.write_bytes(content)
        dump(checkouts['device'] / 'device-prebuilts.json', {'files': [
            {'destination': paths['device'], 'output_sha256': digest, 'mode': '0644'}]})
        dump(checkouts['vendor'] / 'PUBLIC_PROVENANCE.json', {'files': [
            {'destination': 'vendor/lib64/a.so', 'extracted_sha256': digest}]})
        dump(checkouts['vendor'] / 'payload-modes.json', {paths['vendor']: '0644'})
        dump(checkouts['kernel'] / 'extraction-recipe.json', recipe)
        command = [sys.executable, str(scripts / 'populate-payloads.py')]
        for kind in checkouts:
            command += ['--'+kind, str(checkouts[kind]), '--'+kind+'-payloads', str(payloads[kind])]
        def populate(ok):
            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if (proc.returncode == 0) != ok:
                raise RuntimeError('populate fixture result differs')
        conflict = checkouts['vendor'] / paths['vendor']; conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b'user file')
        populate(False)
        if conflict.read_bytes() != b'user file' or (checkouts['device'] / paths['device']).exists():
            raise RuntimeError('conflict preflight modified target')
        passed.append('populate-conflict-all-targets-preserved')
        conflict.unlink(); populate(True); populate(True)
        if any((checkouts[kind] / path).read_bytes() != content for kind, path in paths.items()):
            raise RuntimeError('populate bytes differ')
        passed.append('populate-valid-and-idempotent')
        (checkouts['device'] / paths['device']).unlink()
        (checkouts['device'] / paths['device']).symlink_to(root / 'outside')
        populate(False)
        if (root / 'outside').exists():
            raise RuntimeError('symlink target written')
        passed.append('populate-target-symlink-rejected')
    print(json.dumps({'passed': passed, 'phone_access': False}, indent=2))


if __name__ == '__main__':
    main()
