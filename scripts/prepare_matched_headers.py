"""Fetch exact development packages using authenticated Ubuntu historical indexes.
Does not change APT sources/indexes or install packages.
"""
from pathlib import Path
import hashlib
import json
import lzma
import subprocess
import urllib.request

project = Path(__file__).resolve().parents[1]
destination = project / 'resources/Downloads/Ubuntu24.04/Baseline-Matched'
destination.mkdir(parents=True, exist_ok=True)
base = 'https://snapshot.ubuntu.com/ubuntu/20260215T000000Z/'
wanted = {'libdrm-dev': '2.4.125-1ubuntu0.1~24.04.1',
          'libpciaccess-dev': '0.17-3ubuntu0.24.04.2',
          'libncurses-dev': '6.4+20240113-1ubuntu2'}
found = {}

def fetch(url, path):
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.part')
        with urllib.request.urlopen(url, timeout=45) as source, temporary.open('wb') as target:
            while block := source.read(1024 * 1024):
                target.write(block)
        temporary.replace(path)
    return path.read_bytes()

for suite in ['noble-updates', 'noble']:
    folder = destination / 'metadata' / suite
    folder.mkdir(parents=True, exist_ok=True)
    release = folder / 'InRelease'
    text = fetch(base + f'dists/{suite}/InRelease', release).decode()
    result = subprocess.run(['gpgv', '--keyring', '/usr/share/keyrings/ubuntu-archive-keyring.gpg', str(release)],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (folder / 'signature-verification.txt').write_text(result.stdout)
    result.check_returncode()
    index_name = 'main/binary-amd64/Packages.xz'
    sha_section = text.split('SHA256:\n', 1)[1].split('\nSHA512:', 1)[0]
    entries = [line.split() for line in sha_section.splitlines() if len(line.split()) == 3]
    expected, length, _ = next(parts for parts in entries if parts[2] == index_name)
    raw = fetch(base + f'dists/{suite}/{index_name}', folder / 'Packages.xz')
    assert len(raw) == int(length) and hashlib.sha256(raw).hexdigest() == expected
    for paragraph in lzma.decompress(raw).decode().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        name = fields.get('Package')
        if name in wanted and fields.get('Version') == wanted[name] and fields.get('Architecture') == 'amd64':
            found[name] = {**fields, 'suite': suite}
assert set(found) == set(wanted), ('Missing exact packages', set(wanted) - set(found))
manifest = []
for name in sorted(found):
    fields = found[name]
    filename = Path(fields['Filename']).name
    data = fetch(base + fields['Filename'], destination / filename)
    assert len(data) == int(fields['Size']) and hashlib.sha256(data).hexdigest() == fields['SHA256']
    manifest.append({'package': name, 'version': fields['Version'], 'path': str((destination / filename).relative_to(project)),
                     'sha256': fields['SHA256'], 'source': base + fields['Filename'], 'suite': fields['suite'],
                     'verification': 'Ubuntu signed InRelease -> Packages.xz SHA256 -> DEB SHA256'})
    print(name, fields['Version'], 'AUTHENTICATED SHA256 PASS', flush=True)
(project / 'docs/M3/matched-header-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
