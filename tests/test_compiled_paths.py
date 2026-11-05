#!/usr/bin/env python3
"""Exercise the released loader with native and Windows-style paths; no firmware or compiler."""
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from z8patch import compiled
from tools.check_release import TAG

UNITS = ('precapture','pixelshift','pixelshift-af','opengate','anamorphic','h265','log','quality','shared')
FOLDERS = {'precapture':'z8precapture/', 'pixelshift':'z8pixelshift/src/', 'pixelshift-af':'z8pixelshift/src/', 'opengate':'z8opengate/src/', 'anamorphic':'z8anamorphic/', 'h265':'z8h265/', 'log':'z8log/', 'quality':'z8quality/', 'shared':'z8patch/src/'}


class WindowsPathView:
    """Keep host file I/O, but let pathlib render relative names as on Windows."""
    def __init__(self, path):
        self.path = path

    def __truediv__(self, other):
        return type(self)(self.path / other)

    def __lt__(self, other):
        return self.path < other.path

    def __getattr__(self, name):
        return getattr(self.path, name)

    def iterdir(self):
        return (type(self)(p) for p in self.path.iterdir())

    def rglob(self, pattern):
        return (type(self)(p) for p in self.path.rglob(pattern))

    def relative_to(self, other):
        relative = self.path.relative_to(other.path)
        return PureWindowsPath(*relative.parts)


class CompiledPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nikon-path-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Independently specified manifest keys; no production path/hash helper is used.
        self.sources = {
            'z8precapture/firmware.c': b'/* test fixture, not firmware */\r\n',
            'z8precapture/crc32_table.inc': b'0, 1, 2,\n',
            'z8pixelshift/src/ps8.c': b'/* pixel-shift fixture */\n',
            'z8pixelshift/src/af_unit.c': b'/* AF fixture */\n',
            'z8pixelshift/src/fixture.h': b'#define FIXTURE 1\n',
            'z8opengate/src/d10_hooks.S': b'/* assembly fixture */\n',
            'z8opengate/src/fixture.inc': b'/* include fixture */\n',
            'z8anamorphic/src/hooks.S': b'/* geometry fixture */\n',
            'z8h265/src/hooks.S': b'/* bitrate fixture */\n',
            'z8h265/tiers.json': b'{}\n',
            'z8log/src/hooks.S': b'/* log fixture */\n',
            'z8log/data.json': b'{}\n',
            'z8quality/src/hooks.S': b'/* star fixture */\n',
            'z8quality/icons/fixture.png': b'fake png fixture\n',
            'z8patch/src/shared.S': b'/* shared fixture */\n',
        }
        for name, raw in self.sources.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (self.root / 'resources').mkdir()
        self.profiles = {}
        self.code = {}
        for name in UNITS:
            folder = FOLDERS[name]
            code = b'test-only byte sequence: ' + name.encode('ascii')
            self.code[name] = code
            resource = 'resources/' + name + '.bin'
            (self.root / resource).write_bytes(code)
            self.profiles[name] = {
                'source_sha256': {key: hashlib.sha256(raw).hexdigest()
                                  for key, raw in self.sources.items() if key.startswith(folder)},
                'resource': resource, 'bytes': len(code),
                'sha256': hashlib.sha256(code).hexdigest(), 'symbols': {},
            }
        (self.root / 'resources/compiled.json').write_text(
            json.dumps({'units': self.profiles}), encoding='utf-8')

    def roots(self):
        return (('native', self.root), ('Windows', WindowsPathView(self.root)))

    def test_reviewed_repository_sources_match_on_both_path_flavours(self):
        expected = json.loads((ROOT / 'resources/compiled.json').read_text(encoding='utf-8'))['units']
        for label, root in (('native', ROOT), ('Windows', WindowsPathView(ROOT))):
            with patch.object(compiled, 'ROOT', root):
                for name in UNITS:
                    with self.subTest(paths=label, unit=name):
                        self.assertEqual(compiled.source_files(name), expected[name]['source_sha256'])

    def test_exact_prebuilt_loads_without_compiler(self):
        for label, root in self.roots():
            with patch.object(compiled, 'ROOT', root), patch.object(
                    compiled, 'compile_unit', side_effect=AssertionError('Unexpected compiler')):
                for name in UNITS:
                    with self.subTest(paths=label, unit=name):
                        code, profile = compiled.load(name)
                        self.assertEqual(code, self.code[name])
                        self.assertEqual(profile, self.profiles[name])

    def test_source_mode_uses_same_path_guard(self):
        for label, root in self.roots():
            with patch.object(compiled, 'ROOT', root):
                for name in UNITS:
                    with self.subTest(paths=label, unit=name), patch.object(
                            compiled, 'compile_unit', return_value=(self.code[name], {'symbols': {}})) as compiler:
                        code, _ = compiled.load(name, 'source', 'test-compiler')
                        self.assertEqual(code, self.code[name])
                        compiler.assert_called_once_with(name, 'test-compiler')

    def test_source_byte_changes_are_rejected_before_compilation(self):
        name = 'z8precapture/firmware.c'
        # CRLF -> LF is a byte change, even though paths are normalized.
        (self.root / name).write_bytes(self.sources[name].replace(b'\r\n', b'\n'))
        for label, root in self.roots():
            for mode in ('prebuilt', 'source'):
                with self.subTest(paths=label, mode=mode), patch.object(compiled, 'ROOT', root), patch.object(
                        compiled, 'compile_unit', side_effect=AssertionError('Unexpected compiler')):
                    with self.assertRaisesRegex(ValueError, 'Compiled patch source does not match'):
                        compiled.load('precapture', mode)

    def test_missing_or_additional_source_is_rejected(self):
        missing = self.root / 'z8precapture/firmware.c'
        extra = self.root / 'z8precapture/unreviewed.h'
        for label, root in self.roots():
            with patch.object(compiled, 'ROOT', root):
                for kind in ('missing', 'extra'):
                    with self.subTest(paths=label, change=kind):
                        if kind == 'missing':
                            missing.unlink()
                        else:
                            extra.write_bytes(b'/* extra */\n')
                        try:
                            with self.assertRaisesRegex(ValueError, 'Compiled patch source does not match'):
                                compiled.load('precapture')
                        finally:
                            if kind == 'missing':
                                missing.write_bytes(self.sources['z8precapture/firmware.c'])
                            else:
                                extra.unlink()

    def test_changed_binary_is_rejected(self):
        for label, root in self.roots():
            with patch.object(compiled, 'ROOT', root):
                for name in UNITS:
                    with self.subTest(paths=label, unit=name):
                        path = self.root / self.profiles[name]['resource']
                        raw = self.code[name]
                        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                        try:
                            with self.assertRaisesRegex(ValueError, 'Patch code differs from the reviewed recipe'):
                                compiled.load(name)
                        finally:
                            path.write_bytes(raw)

    def test_missing_binary_has_no_fallback(self):
        for label, root in self.roots():
            with patch.object(compiled, 'ROOT', root), patch.object(
                    compiled, 'compile_unit', side_effect=AssertionError('Unexpected compiler')):
                for name in UNITS:
                    with self.subTest(paths=label, unit=name):
                        path = self.root / self.profiles[name]['resource']
                        path.unlink()
                        try:
                            with self.assertRaisesRegex(ValueError, 'Precompiled patch missing'):
                                compiled.load(name)
                        finally:
                            path.write_bytes(self.code[name])

    def test_revision_release_tag_is_explicit(self):
        for value in ('v0.3.0', 'v0.3.0-rc.1', 'v0.3.0-r1', 'v0.3.0-r12'):
            with self.subTest(tag=value):
                self.assertIsNotNone(re.fullmatch(TAG, value))
        for value in ('v0.3.0-r0', 'v0.3.0-r01', 'v0.3.0-r', 'v0.3.0-other'):
            with self.subTest(tag=value):
                self.assertIsNone(re.fullmatch(TAG, value))


if __name__ == '__main__':
    unittest.main(verbosity=2)
