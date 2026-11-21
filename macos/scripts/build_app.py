#!/usr/bin/env python3
"""Assemble Z8 Patch Builder.app from a verified toolkit ZIP and the pinned runtime; never reads firmware.

The app bundles the runtime members of the toolkit ZIP byte for byte, CPython 3.12 from
python-build-standalone with only the standard-library modules the toolkit uses, and capstone.
Signing is ad hoc unless --identity names a Developer ID Application certificate; --notary-profile
then notarizes and staples the app, builds the disk image from the stapled app, and notarizes and
staples the disk image too.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / 'macos'
sys.path.insert(0, str(ROOT))
from tools.check_release import MANIFEST, check_release  # noqa: E402

APP_NAME = 'Z8 Patch Builder'
EXECUTABLE = 'Z8PatchBuilder'
BUNDLE_ID = 'io.github.xinmiaozhao.Z8PatchBuilder'
RUNTIME_TOP = ('patch.py', 'features.py', 'verify.py', 'LICENSE', 'NOTICE.md', MANIFEST)
LANGS = ('en', 'zh-Hans', 'zh-Hant')                # .lproj folders; English is the source language
STRINGS = MACOS / 'Resources/Localizable.xcstrings'  # interface String Catalog
DMG_WINDOW = (640, 400)    # disk-image window size in points; make_dmg_background.swift draws to it
DMG_ICONS = (160, 480, 225)  # icon centres: app x, Applications x, shared y (points, origin top left)


def need(ok, message):
    if not ok:
        raise SystemExit('ERROR: ' + message)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run(*cmd, **kw):
    print('+ ' + ' '.join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def toolkit_member(name):
    """Members the app needs to check, build and verify; documents, tests and tools are not bundled."""
    return name in RUNTIME_TOP or name.startswith('resources/') or re.match(r'z8[a-z0-9]+/', name) is not None


def fetch(spec, given, cache):
    """Use a local file or download into the cache; either way the pinned size and SHA-256 must match."""
    if given:
        path = Path(given)
    else:
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / urllib.request.unquote(spec['url'].rsplit('/', 1)[1])
        if not path.is_file() or sha256(path) != spec['sha256']:
            print('Downloading ' + spec['url'], flush=True)
            part = path.with_suffix(path.suffix + '.part')
            with urllib.request.urlopen(spec['url'], timeout=120) as r, open(part, 'wb') as f:
                shutil.copyfileobj(r, f)
            part.replace(path)
    need(path.is_file() and path.stat().st_size == spec['bytes'] and sha256(path) == spec['sha256'],
         'Pinned dependency mismatch: ' + path.name)
    return path


def extract_toolkit(archive, dest):
    with zipfile.ZipFile(archive) as z:
        prefix = z.namelist()[0].split('/')[0]
        record = json.loads(z.read(prefix + '/' + MANIFEST))
        names = sorted(n for n in record['files'] if toolkit_member(n)) + [MANIFEST]
        for name in names:
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(prefix + '/' + name))
    for name in names[:-1]:
        need(sha256(dest / name) == record['files'][name]['sha256'], 'Extracted member differs: ' + name)
    need('resources/gui-catalog.json' in names, 'Toolkit has no resources/gui-catalog.json')
    packages = {n.split('/')[0] for n in record['files'] if n.startswith('z8') and '/' in n}
    need(packages and all(any(n.startswith(p + '/') for n in names) for p in packages), 'A z8 package is missing from the app')
    return record, len(names)


COMPILE = r'''
import json, py_compile, sys
for src, cfile, dfile in json.load(sys.stdin):
    py_compile.compile(src, cfile=cfile, dfile=dfile, doraise=True,
                       invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
'''


def build_runtime(python_tgz, wheel, dest, spec, licenses):
    with tempfile.TemporaryDirectory(prefix='z8gui-runtime-') as tmp:
        tmp = Path(tmp)
        with tarfile.open(python_tgz) as t:
            t.extractall(tmp, filter='data')
        py = tmp / 'python/bin/python3.12'
        lib = tmp / 'python/lib/python3.12'
        need(py.is_file() and lib.is_dir(), 'Unexpected python-build-standalone layout')
        jobs = []
        for name in spec['stdlib']:
            base = lib / name.replace('.', '/')
            if (base / '__init__.py').is_file():
                jobs.append(base / '__init__.py')
            else:
                need(base.with_suffix('.py').is_file(), 'Missing stdlib module ' + name)
                jobs.append(base.with_suffix('.py'))
        for package in spec['stdlib_packages']:
            jobs += [p for p in (lib / package).rglob('*.py') if 'test' not in p.relative_to(lib).parts[1:]]
        jobs = sorted(set(jobs))
        pyc = tmp / 'pyc'
        work = [(str(src), str(pyc / src.relative_to(lib).with_suffix('.pyc')), str(src.relative_to(lib)))
                for src in jobs]
        subprocess.run([str(py), '-E', '-s', '-B', '-c', COMPILE], input=json.dumps(work), text=True, check=True)
        (dest / 'bin').mkdir(parents=True)
        shutil.copy2(py, dest / 'bin/python3.12')
        (dest / 'lib/python3.12/lib-dynload').mkdir(parents=True)  # exec_prefix landmark; no extensions
        with zipfile.ZipFile(dest / 'lib/python312.zip', 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for _, cfile, dfile in work:
                info = zipfile.ZipInfo(str(Path(dfile).with_suffix('.pyc')), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, Path(cfile).read_bytes())
        shutil.copy2(tmp / spec['python']['license'], licenses / 'Python-LICENSE.txt')
        site = dest / 'lib/python3.12/site-packages'
        site.mkdir()
        with zipfile.ZipFile(wheel) as z:
            for name in z.namelist():
                if name.startswith('capstone/') and not name.endswith('/') and '/include/' not in name:
                    target = site / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read(name))
            (licenses / 'capstone-LICENSE.txt').write_bytes(z.read(spec['capstone']['license']))
        sources = sorted((site / 'capstone').rglob('*.py'))
        work = [(str(p), str(p.parent / '__pycache__' / (p.stem + '.cpython-312.pyc')), str(p.relative_to(site)))
                for p in sources]
        subprocess.run([str(py), '-E', '-s', '-B', '-c', COMPILE], input=json.dumps(work), text=True, check=True)
        return len(jobs)


def check_strings(stringsdata):
    """Every string the release binary localizes must have a translation in the String Catalog."""
    catalog = json.loads(STRINGS.read_text(encoding='utf-8'))['strings']
    used = set()
    for path in sorted(stringsdata.glob('*.stringsdata')):
        for table, entries in json.loads(path.read_text(encoding='utf-8'))['tables'].items():
            need(table == 'Localizable', f'{path.name}: unexpected strings table {table}')
            used |= {e['key'] for e in entries}
    need(used, 'The compiler reported no localizable strings')
    for key in sorted(used):
        entry = catalog.get(key)
        need(entry is not None, 'Not in Localizable.xcstrings (run macos/scripts/sync_strings.py): ' + repr(key))
        if entry.get('shouldTranslate') is not False:
            for lang in LANGS[1:]:
                unit = entry.get('localizations', {}).get(lang, {}).get('stringUnit', {})
                need(unit.get('state') == 'translated', f'No {lang} translation in Localizable.xcstrings: {key!r}')
    return len(used)


def install_strings(resources, scratch):
    compiled = scratch / 'strings'
    run('xcrun', 'xcstringstool', 'compile', STRINGS, '--output-directory', compiled)
    for lang in LANGS:
        target = resources / f'{lang}.lproj'
        shutil.copytree(MACOS / f'Resources/{lang}.lproj', target)
        if (compiled / f'{lang}.lproj').is_dir():  # English has only its plural rules
            for path in (compiled / f'{lang}.lproj').iterdir():
                need(not (target / path.name).exists(), 'Duplicate localized resource ' + path.name)
                shutil.copy2(path, target / path.name)


def make_icon(resources, scratch):
    iconset = scratch / 'AppIcon.iconset'
    run('swift', MACOS / 'scripts/make_icon.swift', iconset)
    run('iconutil', '-c', 'icns', iconset, '-o', resources / 'AppIcon.icns')


def info_plist(tag, commit, build_number):
    numeric = re.match(r'v(\d+\.\d+\.\d+)', tag).group(1)
    return {
        'CFBundleDevelopmentRegion': 'en',
        'CFBundleDisplayName': APP_NAME,
        'CFBundleExecutable': EXECUTABLE,
        'CFBundleIconFile': 'AppIcon',
        'CFBundleIdentifier': BUNDLE_ID,
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleLocalizations': list(LANGS),
        'CFBundleName': APP_NAME,
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': numeric,
        'CFBundleVersion': str(build_number),
        'LSApplicationCategoryType': 'public.app-category.photography',
        'LSArchitecturePriority': ['arm64'],
        'LSMinimumSystemVersion': '14.0',
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': '© 2026 Xinmiao Zhao and contributors',  # localized in InfoPlist.strings
        'NSSupportsAutomaticTermination': False,
        'Z8ToolkitTag': tag,
        'Z8ToolkitCommit': commit,
    }


def sign(app, identity, timestamp):
    runtime_flags = ['--options', 'runtime'] + (['--timestamp'] if timestamp else ['--timestamp=none'])
    resources = app / 'Contents/Resources'
    inner = [resources / 'runtime/lib/python3.12/site-packages/capstone/lib/libcapstone.dylib',
             resources / 'runtime/bin/python3.12']
    # Hardened Runtime library validation requires the interpreter and libcapstone to share a Team ID.
    # Ad-hoc signatures have none, so local test builds sign these two without the runtime flag;
    # Developer ID builds sign everything with it.
    inner_flags = runtime_flags if identity != '-' else ['--timestamp=none']
    for path in inner:
        run('codesign', '--force', '--sign', identity, *inner_flags,
            *(['--entitlements', MACOS / 'Resources/Python.entitlements'] if path.name == 'python3.12' else []), path)
    run('codesign', '--force', '--sign', identity, *runtime_flags,
        '--entitlements', MACOS / 'Resources/Z8PatchBuilder.entitlements', app)
    run('codesign', '--verify', '--strict', '--deep', '--verbose=2', app)


def check_signatures(app):
    """Before a notary round trip: every Mach-O carries a Team ID, the Hardened Runtime and a secure timestamp."""
    resources = app / 'Contents/Resources'
    for path in (resources / 'runtime/lib/python3.12/site-packages/capstone/lib/libcapstone.dylib',
                 resources / 'runtime/bin/python3.12', app):
        info = subprocess.run(['codesign', '-dv', '--verbose=4', str(path)], capture_output=True, text=True).stderr
        team = re.search(r'^TeamIdentifier=(.+)$', info, re.M)
        need(team and team.group(1) != 'not set', f'{path.name}: no Team ID')
        need(re.search(r'flags=0x[0-9a-f]+\([^)]*runtime', info), f'{path.name}: no Hardened Runtime')
        need(re.search(r'^Timestamp=', info, re.M), f'{path.name}: no secure timestamp')
    entitlements = subprocess.run(['codesign', '-d', '--entitlements', '-', '--xml', str(app)], capture_output=True).stdout
    need(b'get-task-allow' not in entitlements, 'The app allows debugging (get-task-allow)')
    return team.group(1)


def notarize(path, profile, out_dir, label):
    """Submit to Apple's notary service and wait; keep the log; staple the ticket once accepted."""
    upload = path
    if path.suffix == '.app':
        upload = out_dir / f'{path.stem}-notary.zip'
        run('ditto', '-c', '-k', '--keepParent', path, upload)
    print(f'+ xcrun notarytool submit {upload.name} --wait', flush=True)
    r = subprocess.run(['xcrun', 'notarytool', 'submit', str(upload), '--keychain-profile', profile, '--wait',
                        '--timeout', '45m', '--output-format', 'json'], capture_output=True, text=True)
    if upload != path:
        upload.unlink()
    try:
        info = json.loads(r.stdout)
    except ValueError:
        raise SystemExit('ERROR: notarytool submit failed:\n' + r.stdout + r.stderr)
    log = out_dir / f'notary-{label}.json'
    if info.get('id'):
        subprocess.run(['xcrun', 'notarytool', 'log', info['id'], '--keychain-profile', profile, str(log)],
                       capture_output=True, text=True)
    need(info.get('status') == 'Accepted',
         f'Notarization of {path.name}: {info.get("status")} ({info.get("message")}); see {log.name}')
    run('xcrun', 'stapler', 'staple', path)
    run('xcrun', 'stapler', 'validate', path)
    return dict(submission=info['id'], status=info['status'], log=log.name)


def gatekeeper(path, kind):
    """Gatekeeper's own verdict, which must name a notarized Developer ID."""
    context = ['--context', 'context:primary-signature'] if kind == 'open' else []
    r = subprocess.run(['spctl', '--assess', '--type', kind, *context, '--verbose=2', str(path)], capture_output=True, text=True)
    verdict = (r.stdout + r.stderr).strip()
    need(r.returncode == 0 and 'source=Notarized Developer ID' in verdict, f'Gatekeeper rejects {path.name}: {verdict}')
    return verdict.splitlines()[-1].split('=', 1)[-1]


def make_dmg(app, out_dir, tag, identity, timestamp, wheels):
    """Disk image that opens as a drag-to-Applications window. dmgbuild (pinned in runtime.json, used
    only here) writes the window size, icon positions and background into the image's .DS_Store
    directly, so Finder is never scripted."""
    need(sys.version_info >= (3, 10), 'The disk image needs Python 3.10 or newer (dmgbuild)')
    sys.path[:0] = [str(w) for w in wheels]
    import dmgbuild
    dmg = out_dir / f'NikonFirmwarePatch-{tag}-macOS.dmg'
    app_x, apps_x, icon_y = DMG_ICONS
    with tempfile.TemporaryDirectory(prefix='z8gui-dmg-') as stage:
        stage = Path(stage)
        run('swift', MACOS / 'scripts/make_dmg_background.swift', stage, *DMG_WINDOW, app_x, apps_x, icon_y, tag)
        print('+ dmgbuild ' + dmg.name, flush=True)
        # No hide_extensions: it stores a Finder flag on the app bundle, which travels with the app
        # dragged out of the image and fails `codesign --verify --strict` there. Finder already hides
        # ".app" unless the user shows all extensions.
        dmgbuild.build_dmg(str(dmg), APP_NAME, settings=dict(
            files=[str(app)], symlinks={'Applications': '/Applications'},
            icon=str(app / 'Contents/Resources/AppIcon.icns'),
            background=str(stage / 'background.tiff'),
            window_rect=((200, 120), DMG_WINDOW), default_view='icon-view', icon_size=128, text_size=13,
            icon_locations={app.name: (app_x, icon_y), 'Applications': (apps_x, icon_y)},
            show_status_bar=False, show_tab_view=False, show_toolbar=False, show_pathbar=False, show_sidebar=False,
            format='ULFO', filesystem='APFS'))
    if identity != '-':
        run('codesign', '--force', '--sign', identity, *(['--timestamp'] if timestamp else []), dmg)
    return dmg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--toolkit-zip', type=Path, required=True, help='NikonFirmwarePatch-<tag>-toolkit.zip from tools/build_release.py')
    ap.add_argument('--output', type=Path, required=True, help='New directory for the app and disk image')
    ap.add_argument('--python-archive', help='Local copy of the pinned python-build-standalone archive')
    ap.add_argument('--capstone-wheel', help='Local copy of the pinned capstone wheel')
    ap.add_argument('--cache', type=Path, default=Path.home() / 'Library/Caches/NikonFirmwarePatch-macos')
    ap.add_argument('--identity', default='-', help='codesign identity; "-" (default) signs ad hoc for local tests')
    ap.add_argument('--notary-profile', help='notarytool keychain profile; requires a Developer ID identity')
    ap.add_argument('--build-number', type=int, default=1)
    ap.add_argument('--no-dmg', action='store_true')
    a = ap.parse_args()
    need(not a.output.exists(), 'Output directory already exists')
    need(not a.notary_profile or a.identity != '-', '--notary-profile requires --identity')
    spec = json.loads((MACOS / 'runtime.json').read_text())
    verified = check_release(a.toolkit_zip)
    python_tgz = fetch(spec['python'], a.python_archive, a.cache)
    wheel = fetch(spec['capstone'], a.capstone_wheel, a.cache)
    dmg_wheels = [] if a.no_dmg else [fetch(p, None, a.cache) for p in spec['dmg_tools']['packages']]

    a.output.mkdir(parents=True)
    scratch = a.output / '.work'
    scratch.mkdir()
    app = a.output / (APP_NAME + '.app')
    contents = app / 'Contents'
    resources = contents / 'Resources'
    (contents / 'MacOS').mkdir(parents=True)
    licenses = resources / 'licenses'
    licenses.mkdir(parents=True)

    record, toolkit_files = extract_toolkit(a.toolkit_zip, resources / 'toolkit')
    stdlib_files = build_runtime(python_tgz, wheel, resources / 'runtime', spec, licenses)
    stringsdata = scratch / 'stringsdata'
    stringsdata.mkdir()
    run('swift', 'build', '-c', 'release', '--arch', 'arm64', '--package-path', MACOS,
        '--scratch-path', scratch / 'swift', *[f for arg in ('-emit-localized-strings', '-emit-localized-strings-path', stringsdata)
                                               for f in ('-Xswiftc', arg)])
    interface_strings = check_strings(stringsdata)
    binary = scratch / 'swift/arm64-apple-macosx/release' / EXECUTABLE
    shutil.copy2(binary, contents / 'MacOS' / EXECUTABLE)
    make_icon(resources, scratch)
    install_strings(resources, scratch)
    with open(contents / 'Info.plist', 'wb') as f:
        plistlib.dump(info_plist(record['tag'], record['source_commit'], a.build_number), f)
    (contents / 'PkgInfo').write_text('APPL????')
    shutil.rmtree(scratch)

    timestamp = a.identity != '-'
    sign(app, a.identity, timestamp)
    smoke = subprocess.run([str(contents / 'MacOS' / EXECUTABLE), '--self-test'], capture_output=True, text=True, timeout=120)
    need(smoke.returncode == 0, 'App self-test failed:\n' + smoke.stdout + smoke.stderr)
    team = check_signatures(app) if a.identity != '-' else None
    notary = {}
    if a.notary_profile:
        # The app gets its own ticket first, so a copy dragged out of the disk image passes
        # Gatekeeper offline; the image is then built from the stapled app and notarized as well.
        notary['app'] = notarize(app, a.notary_profile, a.output, 'app')
        notary['app']['gatekeeper'] = gatekeeper(app, 'execute')
    dmg = None if a.no_dmg else make_dmg(app, a.output, record['tag'], a.identity, timestamp, dmg_wheels)
    if a.notary_profile and dmg:
        notary['dmg'] = notarize(dmg, a.notary_profile, a.output, 'dmg')
        notary['dmg']['gatekeeper'] = gatekeeper(dmg, 'open')
    if dmg:
        (a.output / 'SHA256SUMS.txt').write_text(sha256(dmg) + '  ' + dmg.name + '\n')
    size = sum(p.stat().st_size for p in app.rglob('*') if p.is_file() and not p.is_symlink())
    print(json.dumps(dict(status='BUILT', app=str(app), tag=record['tag'], source_commit=record['source_commit'],
                          toolkit_archive_sha256=verified['archive_sha256'], toolkit_files=toolkit_files,
                          stdlib_modules=stdlib_files, interface_strings=interface_strings, app_bytes=size,
                          dmg=str(dmg) if dmg else None, dmg_bytes=dmg.stat().st_size if dmg else None,
                          dmg_sha256=sha256(dmg) if dmg else None,
                          signature='ad hoc (local test only)' if a.identity == '-' else 'Developer ID, team ' + team,
                          notarized=bool(notary), notary=notary or None,
                          self_test=json.loads(smoke.stdout)), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile, tarfile.TarError, ValueError, KeyError) as e:
        raise SystemExit('ERROR: ' + str(e))
