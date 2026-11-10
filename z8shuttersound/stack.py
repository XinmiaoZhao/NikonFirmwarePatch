# SPDX-License-Identifier: GPL-3.0-or-later
"""Add the custom shutter-sound port to a checked EG; repackage with the longer module."""
import binascii
import hashlib
import os
import struct
import tempfile
from pathlib import Path
from z8prores.package import AUTH_APPEND, OUTER_FIELD, transform, require
from . import builder

# Folder holding clang, ld.lld, llvm-nm, llvm-objcopy and llvm-objdump.
LLVM = os.environ.get('Z8_LLVM_BIN', '')
TAIL_BYTES = 13  # 'Ver.' + eight identity bytes + NUL, before the CRC


def stack(stock_eg, base_eg, llvm=LLVM, keep=None, code_source='prebuilt'):
    """Return the finished EG; `keep` receives the builder's working files.

    prebuilt fills resources/shuttersound.bin from the input; source compiles with `llvm`.
    """
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        (work / 'stock.eg').write_bytes(stock_eg)
        (work / 'base.eg').write_bytes(base_eg)
        output = Path(keep) if keep else work / 'build'
        report = builder.build(work / 'stock.eg', output, work / 'base.eg', llvm, tail=base_eg[-2 - TAIL_BYTES:-2],
                               code_source=code_source)
        return (output / 'patched-eg.bi').read_bytes(), report


def pack(package, eg, name):
    """Stock body with module 2 replaced; later modules move, nothing else."""
    require(binascii.crc_hqx(eg, 0) == 0, 'Invalid replacement EG')
    body = bytearray(package.body[:208])
    for i, module in enumerate(package.modules):
        data = eg if i == 2 else package.body[module['start']:module['start'] + module['bytes']]
        label = name if i == 2 else module['name']
        struct.pack_into('>16s4I', body, 48 + i * 32, label.encode().ljust(16, b'\0'), len(body), len(data), 0, 0)
        body.extend(data)
    body.extend(binascii.crc_hqx(body, 0).to_bytes(2, 'big'))
    body.extend(bytes(14))
    return hashlib.sha1(body + AUTH_APPEND).digest() + OUTER_FIELD + transform(body, package.tables)


def unpack(package, packet, name):
    """Independent container readback; return the EG after checking the rest."""
    require(packet[20:32] == OUTER_FIELD, 'Outer package context differs')
    body = transform(packet[32:], package.tables)
    require(hashlib.sha1(body + AUTH_APPEND).digest() == packet[:20], 'Package SHA1 mismatch')
    require(body[-14:] == bytes(14) and binascii.crc_hqx(body[:-14], 0) == 0, 'Package CRC mismatch')
    require(struct.unpack_from('>4I', body, 32) == (5, 208, 0, 0), 'Module directory differs')
    require(body[:48] == package.body[:48], 'Package header changed')
    at, result = 208, None
    for i, module in enumerate(package.modules):
        label, start, size, r0, r1 = struct.unpack_from('>16s4I', body, 48 + i * 32)
        require((start, r0, r1) == (at, 0, 0), 'Module layout differs')
        data = body[start:start + size]
        require(binascii.crc_hqx(data, 0) == 0, 'Module CRC mismatch')
        require(label.rstrip(b'\0').decode() == (name if i == 2 else module['name']), 'Module name differs')
        if i == 2:
            result = data
        else:
            require(data == package.body[module['start']:module['start'] + module['bytes']], 'Unselected module changed')
        at = start + size
    require(at + 16 == len(body), 'Package length differs')
    return result
