#!/usr/bin/env python3
"""Independent byte/container verification. Imports no builder, encoder or packer."""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    need(len(raw) == 99051117 and raw[20:32].hex() == '5866cd124269c27e621da226', 'Wrong Z8 package context')
    # Independent recovery, with a different normalization than the packer:
    # A'[x]=cipher(zero+x), B'[y]=cipher(zero+256y)^cipher(zero), C'[g]=0.
    cipher = memoryview(raw)[32:]
    zero, embedded = 0xB10000, 0x3FF1F84
    low = bytes(cipher[zero:zero+256])
    middle = bytes(cipher[zero+256*y] ^ cipher[zero] for y in range(256))
    temporary = bytes(cipher[embedded+i] ^ low[(embedded+i)%256] ^ middle[((embedded+i)//256)%256] for i in range(256))
    plane = (zero//65536)%256
    high_key = bytes(t ^ temporary[plane] for t in temporary)
    keys = low, middle, high_key
    b = bytearray(raw[32:])
    masks = {}
    # Separate 64 KiB stream construction, indexed by absolute position in body.
    for a in range(0, len(b), 65536):
        z = min(a + 65536, len(b))
        high = (a >> 16) & 255
        if high not in masks:
            masks[high] = b''.join(bytes(x ^ keys[1][j] ^ keys[2][high] for x in keys[0]) for j in range(256))
        mask = masks[high]
        value = int.from_bytes(b[a:z], 'little') ^ int.from_bytes(mask[:z-a], 'little')
        b[a:z] = value.to_bytes(z-a, 'little')
    b[:32] = raw[32:64]
    b = bytes(b)
    need(b[:32] == b' '*32 and struct.unpack_from('>4I', b, 32) == (5, 208, 0, 0), 'Wrong directory')
    need(b[-14:] == bytes(14) and binascii.crc_hqx(b[:-14], 0) == 0, 'Body CRC or trailer mismatch')
    need(hashlib.sha1(b + bytes.fromhex('6c12037e6fcec19a')).digest() == raw[:20], 'SHA1 mismatch')
    expected = [(208,524290),(524498,57346),(581844,81807711),(82389555,838664),(83228219,15822850)]
    for i,(a,n) in enumerate(expected):
        _, start, size, r0, r1 = struct.unpack_from('>16s4I', b, 48+32*i)
        need((start,size,r0,r1) == (a,n,0,0), 'Module boundary mismatch')
        need(binascii.crc_hqx(b[a:a+n], 0) == 0, 'Module CRC mismatch')
    return b


def verify_pair(original, candidate, features=None, *, expected_version=None, expected_tag=None):
    # Trusted published data only: do not accept a candidate's own manifest as its specification.
    requested_features = features is not None
    source = json.loads((HERE / 'resources/input.json').read_text())
    need(len(original) == source['bytes'] and sha(original) == source['sha256'],
         'Original must match the official Nikon Z8 C 3.11 SHA-256')
    need(expected_version is not None or expected_tag is None, 'Expected tag requires an expected version')
    if expected_version is not None:
        need(re.fullmatch(r'[0-9]{2}\.[0-9]{2}', expected_version), 'Invalid expected version')
        expected_tag = 'p0' if expected_tag is None else expected_tag
        need(re.fullmatch(r'[a-z][0-9]', expected_tag), 'Invalid expected tag')
    a, b = decode(original), decode(candidate)
    need(a[:112] == b[:112] and a[128:581844] == b[128:581844] and
         a[82389555:-16] == b[82389555:-16], 'Non-EG module or header changed')
    old, new = a[581844:82389555], b[581844:82389555]
    order=('framing','video-quality','log-colour','photo-tools','video-orientation')
    recipes=json.loads((HERE/'resources/combinations.json').read_text())
    need(recipes['schema']==2,'Unsupported recipe schema')
    profiles=recipes['profiles']
    if features is None:
        features=[]
        for name,offset in [('framing',0x62E150),('video-quality',0x1C5D48),('log-colour',0xFBA508),('photo-tools',0xE0FE90),('video-orientation',0xB8FD60)]:
            if old[offset:offset+4]!=new[offset:offset+4]:features.append(name)
    need(features and len(features)==len(set(features)) and set(features)<=set(order),'Invalid feature selection')
    features=[f for f in order if f in features]
    profile=profiles['+'.join(features)]
    identity=new[0x14EAA90:0x14EAA98]
    old_identity=old[0x14EAA90:0x14EAA98]
    if expected_version is not None:
        need(identity==f'{expected_version}.{expected_tag}'.encode(), 'Output identity differs from requested version/tag')
    spans = []
    for buf, text in [(old, old_identity), (new, identity)]:
        need(re.fullmatch(rb'[0-9]{2}\.[0-9]{2}\.[a-z]\d', text) and buf[-11:-3] == text, 'Internal identity mismatch')
        w0,w1,w2 = struct.unpack_from('<3I',buf,0xEB29FC)
        need((w0 & ~0x1FFFE0,w1 & ~0x1FFFE0,w2 & ~0x1FFFE0) == (0x52800008,0x72A00008,0x52800009), 'Version instruction shape')
        value = struct.pack('<I',((w0>>5)&65535)|(((w1>>5)&65535)<<16)) + struct.pack('<H',(w2>>5)&65535)
        need(value == text[:5] + b'\0', 'Public identity mismatch')
    module = b'eg2070_' + identity[:5].replace(b'.',b'') + identity[6:] + b'.bi'
    need(b[112:128] == module.ljust(16,b'\0'), 'Output directory EG name mismatch')
    expected={}
    for index in profile['patches']:
        e=recipes['patches'][index]
        start,size=int(e['offset'],16),e['bytes']
        need(sha(old[start:start+size])==e['old_sha256'],'Input patch bytes differ')
        need(start not in expected,'Duplicate reviewed patch start')
        expected[start]=e
    for start, e in expected.items():
        size = e['bytes']
        need(sha(new[start:start+size]) == e['new_sha256'], 'Output differs from reviewed feature patch bytes')
        spans.append((start,start+size))
    spans += [(0xEB29FC,0xEB2A08),(0x14EAA90,0x14EAA98),(len(old)-11,len(old)-3),(len(old)-2,len(old))]
    end = 0
    for lo,hi in sorted(spans):
        need(end <= lo and old[end:lo] == new[end:lo], 'Overlapping edits or change outside declared windows')
        end = hi
    need(old[end:] == new[end:], 'Unlisted final change')
    from z8patch.contract import verify_contract
    contract=verify_contract(old,new,features)
    return dict(status='PASS',composition_contract=contract, input_sha256=sha(original), output_sha256=sha(candidate),
                output_identity=identity.decode(), features=sorted(features), patch_matches_reviewed_profile=True,
                official_input_verified=True, requested_identity_checked=expected_version is not None,
                requested_features_checked=requested_features,
                all_non_patch_EG_bytes_preserved=True, other_modules_preserved=True,
                scope='Offline byte equivalence and integrity; not a camera test')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('original',type=Path)
    ap.add_argument('candidate',type=Path)
    ap.add_argument('--features', nargs='+', choices=['framing','video-quality','log-colour','photo-tools','video-orientation'], help='Expected new features; otherwise detect changed entry hooks')
    ap.add_argument('--version', help='Expected output version NN.NN; otherwise check identity consistency only')
    ap.add_argument('--tag', help='Expected output tag; requires --version; default p0 when --version is set')
    a = ap.parse_args()
    # Bound file reads before decoding.
    need(a.original.stat().st_size == a.candidate.stat().st_size == 99051117, 'Wrong file lengths')
    print(json.dumps(verify_pair(a.original.read_bytes(),a.candidate.read_bytes(),a.features,
                                expected_version=a.version, expected_tag=a.tag),indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        raise SystemExit('ERROR: ' + str(e))
