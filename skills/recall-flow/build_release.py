"""Build reproducible local archives; never publish, install or upload anything."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / 'knowledge-cards-coach'
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parent / 'v2-deliverables'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bundle(destination, paths, prefix):
    assert 0 < len(paths) <= 30, (destination, len(paths))
    total = sum(p.stat().st_size for p in paths)
    assert total <= 40 * 1024 * 1024, total
    entries = []
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            rel = path.relative_to(SKILL if prefix == SKILL.name else ROOT)
            name = prefix + '/' + rel.as_posix()
            assert '..' not in Path(name).parts and not name.startswith(('/', '\\'))
            raw = path.read_bytes()
            info = zipfile.ZipInfo(name, (2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
            entries.append({'path': name, 'bytes': len(raw), 'sha256': digest(raw)})
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert len(archive.infolist()) == len(paths)
    return {'archive': destination.name, 'files': len(paths), 'uncompressed_bytes': total,
            'archive_bytes': destination.stat().st_size, 'sha256': digest(destination.read_bytes()),
            'entries': entries}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    skill_files = sorted(p for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    assert all(p.suffix not in {'.pyc', '.apkg', '.exe'} for p in skill_files)
    extras = ['README.md', 'requirements-dev.txt', 'HANDOFF.md', 'TEST_REPORT.md', 'build_release.py',
              'tests/create_fixtures.py', 'tests/test_workflow.py', 'tests/test_web.py', 'tests/test_core.mjs']
    source_files = sorted(skill_files + [ROOT / p for p in extras])
    manifests = [bundle(OUT / 'knowledge-cards-coach-v2.skill', skill_files, SKILL.name),
                 bundle(OUT / 'knowledge-cards-coach-v2-source.zip', source_files, ROOT.name)]
    manifest = {'release': '2.0', 'status': 'local tested candidate; platform integration unverified',
                'limits': {'maximum_files': 30, 'maximum_content_bytes': 40 * 1024 * 1024},
                'archives': manifests}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'archives': [{k: v for k, v in m.items() if k != 'entries'} for m in manifests]}, indent=2))


if __name__ == '__main__':
    main()
