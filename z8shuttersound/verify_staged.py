"""04.23 staged PCM/IO regressions using the exact compiled ARM payload.

Run: python -m z8shuttersound.verify_staged PATH_TO_SHUTTER_SOUND_BUILD
Importing verify_integration first runs its shared integration scenarios.
The CPU/DMA view model below is an explicit synthetic test, not hardware evidence.
"""
import gc
import hashlib
import json
import struct

from z8shuttersound import verify_integration as integration

Lab = integration.Lab
C, RAM, HEAP, P, K = integration.C, integration.RAM, integration.HEAP, integration.P, integration.K
SYMS, LAY, wav = integration.SYMS, integration.LAY, integration.wav
X0 = integration.UC_ARM64_REG_X0
PATH = r'A:\CUSTOM_SOUND\tone.wav'
SYNC = 0x40d2b9e4
READ = 0x402dab4c
MAX_PCM = 288000
IO_BYTES = 4096
UINT_MAX = 0xffffffff
rows = []
assert integration.STAGED, 'verify_staged requires a payload built with M2_STAGED_CONFIRM'
assert 'buffered_read' in SYMS and 'm2_native_import_buffered' in SYMS


def passed(name, **extra):
    rows.append(dict(name=name, passed=True, **extra))
    print('PASS_STAGED', name, flush=True)
    gc.collect()


def retained(lab, slot):
    return lab.r64(K + LAY['picker']['retained'] + slot * 8)


def aligned(raw):
    return (raw + 63) & ~63 if raw else 0


def scan(lab, blob=None):
    lab.files[PATH] = wav()[0] if blob is None else blob
    lab.select(5)


def pcm_wav(pcm):
    body = (b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 2, 48000, 192000, 4, 16)
            + b'data' + struct.pack('<I', len(pcm)) + pcm)
    return b'RIFF' + struct.pack('<I', len(body)) + body


def profiles(lab):
    return {key: value for key, value in lab.files.items() if key.endswith('.CFG')}


def test_repeated_mismatch_does_not_fill_cache():
    lab = Lab()
    scan(lab)
    def alternate(current):
        current.files[PATH] = wav(192, current.import_calls)[0]
    lab.before_import = alternate
    fixed_heap = None
    for attempt in range(6):
        lab.select(6)
        assert lab.field('import_status', True) == 14
        assert lab.field('cache_count', True) == 0
        assert lab.field('cache_allocations', True) == 0
        assert lab.field('cache_full', True) == 0
        assert lab.field('imports', True) == 0
        assert retained(lab, 3) == 0
        assert not profiles(lab) and not lab.fds
        if fixed_heap is None:
            fixed_heap = lab.heap
        assert lab.heap == fixed_heap, 'failed confirmations must reuse staging storage'
    assert lab.import_calls == 24
    assert not any(event[0] == 'bind' for event in lab.events)
    lab.before_import = None
    lab.files[PATH] = wav(192, 77)[0]
    lab.select(6)
    assert lab.field('import_status', True) == 0 and lab.field('imports', True) == 1
    assert lab.field('cache_count', True) == 1 and lab.field('cache_allocations', True) == 1
    assert lab.field('profile_commits', True) == 1 and retained(lab, 3) == 0
    assert bytes(lab.u.mem_read(lab.pointer('pcm'), 192)) == wav(192, 77)[1]
    assert sum(event[0] == 'bind' for event in lab.events) == 1
    assert not lab.api_requests and not lab.pcm_requests


def test_metadata_is_compared_even_with_identical_padded_pcm():
    lab = Lab()
    scan(lab, pcm_wav(bytes(188)))
    def alternate_length(current):
        current.files[PATH] = pcm_wav(bytes(188 if current.import_calls % 2 else 192))
    lab.before_import = alternate_length
    lab.select(6)
    assert lab.field('import_status', True) == 14
    assert lab.field('confirm_reason', True) == 2 | 8
    assert lab.field('confirm_diff', True) == UINT_MAX
    assert lab.field('raw_first_hash', True) == lab.field('raw_second_hash', True)
    assert lab.field('valid_first', True) == 188 and lab.field('valid_second', True) == 192
    assert lab.field('play_first', True) == lab.field('play_second', True) == 192
    assert lab.field('cache_count', True) == 0 and not profiles(lab)
    assert not any(event[0] == 'bind' for event in lab.events)


class CorruptPendingOnce(Lab):
    def __init__(self):
        self.corrupt_pending = True
        self.corruptions = 0
        super().__init__()

    def hook(self, u, address, size, user):
        if address == SYNC and self.corrupt_pending:
            pointer = u.reg_read(X0)
            pending = aligned(retained(self, 3))
            if pending and pointer == pending:
                old = bytes(u.mem_read(pointer + 64, 1))
                u.mem_write(pointer + 64, bytes([old[0] ^ 1]))
                self.corrupt_pending = False
                self.corruptions += 1
        return super().hook(u, address, size, user)


def test_failed_copy_is_rejected_and_pending_is_reused():
    lab = CorruptPendingOnce()
    scan(lab)
    lab.select(6)
    pending = aligned(retained(lab, 3))
    failed_heap = lab.heap
    assert lab.corruptions == 1 and pending
    assert lab.field('import_status', True) == lab.field('confirm_error', True) == 15
    assert lab.field('copy_diff', True) == 64
    assert lab.field('copy_before_hash', True) != lab.field('copy_after_hash', True)
    assert lab.field('cache_count', True) == lab.field('imports', True) == 0
    assert not profiles(lab) and not any(event[0] == 'bind' for event in lab.events)
    lab.select(6)
    assert lab.field('import_status', True) == 0 and lab.pointer('pcm') == pending
    assert lab.heap == failed_heap and retained(lab, 3) == 0
    assert lab.field('cache_count', True) == lab.field('cache_allocations', True) == 1
    assert bytes(lab.u.mem_read(pending, 192)) == wav()[1]


def test_bind_busy_keeps_pending_unpublished():
    lab = Lab()
    scan(lab)
    lab.w32(P + LAY['state']['active'], 1)
    lab.select(6)
    pending = aligned(retained(lab, 3))
    failed_heap = lab.heap
    assert pending and lab.field('import_status', True) == 13
    assert lab.field('cache_count', True) == lab.field('imports', True) == 0
    assert lab.field('selected') == 0 and not profiles(lab)
    lab.w32(P + LAY['state']['active'], 0)
    lab.select(6)
    assert lab.field('import_status', True) == 0 and lab.pointer('pcm') == pending
    assert lab.heap == failed_heap and retained(lab, 3) == 0
    assert lab.field('cache_count', True) == 1 and lab.field('imports', True) == 1


def test_published_pcm_is_immutable_across_reselection_and_failure():
    lab = Lab()
    lab.choose_setup(192, 1)
    first = lab.pointer('pcm')
    first_bytes = bytes(lab.u.mem_read(first, 192))
    lab.files[PATH] = wav(192, 2)[0]
    lab.select(6)
    second = lab.pointer('pcm')
    second_bytes = bytes(lab.u.mem_read(second, 192))
    assert second != first and lab.field('cache_count', True) == 2
    saved_profiles = profiles(lab)
    def alternate(current):
        current.files[PATH] = wav(192, current.import_calls + 10)[0]
    lab.before_import = alternate
    lab.select(6)
    assert lab.field('import_status', True) == 14 and lab.pointer('pcm') == second
    assert lab.field('cache_count', True) == 2 and profiles(lab) == saved_profiles
    assert bytes(lab.u.mem_read(first, 192)) == first_bytes
    assert bytes(lab.u.mem_read(second, 192)) == second_bytes
    lab.before_import = None
    lab.files[PATH] = wav(192, 1)[0]
    lab.select(6)
    assert lab.field('import_status', True) == 0 and lab.pointer('pcm') == first
    assert lab.field('cache_count', True) == 2 and lab.field('cache_hits', True) >= 1
    assert bytes(lab.u.mem_read(first, 192)) == first_bytes
    assert bytes(lab.u.mem_read(second, 192)) == second_bytes
    assert all(aligned(retained(lab, slot)) not in (first, second) for slot in range(3))


class IOTrace(Lab):
    def __init__(self):
        self.io_trace = []
        self.parser_destinations = []
        super().__init__()
        self.instruction_limit = 80000000

    def hook(self, u, address, size, user):
        if address not in (SYMS['buffered_read'], SYNC, READ):
            return super().hook(u, address, size, user)
        x = [u.reg_read(X0 + offset) for offset in range(4)]
        if address == SYMS['buffered_read']:
            self.parser_destinations.append((x[1], x[2]))
        if address == SYNC:
            self.io_trace.append(('sync', x[0], x[1]))
        if address == READ:
            f = self.fds.get(x[0])
            if f and f['path'].endswith('.wav'):
                self.io_trace.append(('read', x[1], x[2]))
        return super().hook(u, address, size, user)


def test_native_reads_use_dedicated_io_for_headers_and_pcm():
    lab = IOTrace()
    lab.choose_setup(5000)
    io = aligned(retained(lab, 2))
    assert io and io % 64 == 0
    reads = [(index, event) for index, event in enumerate(lab.io_trace) if event[0] == 'read']
    assert len(reads) > 10, 'short reads should exercise repeated parser IO'
    for index, event in reads:
        _, destination, request = event
        assert destination == io and 0 < request <= IO_BYTES
        assert lab.io_trace[index - 1] == ('sync', io, IO_BYTES)
        assert lab.io_trace[index + 1] == ('sync', io, IO_BYTES)
    destinations = lab.parser_destinations
    assert {12, 8, 16, 4096}.issubset({request for _, request in destinations})
    assert any(RAM + 0x1e0000 <= destination < RAM + 0x200000 for destination, _ in destinations)
    assert all(destination != io for destination, _ in destinations)
    assert bytes(lab.u.mem_read(lab.pointer('pcm'), 5184)) == wav(5000)[1] + bytes(184)


class RawReadFault(IOTrace):
    def __init__(self, fault=None):
        self.fault = fault
        super().__init__()

    def hook(self, u, address, size, user):
        if address == READ and self.fault:
            x = [u.reg_read(X0 + offset) for offset in range(4)]
            self.io_trace.append(('read', x[1], x[2]))
            self.w32(x[3], x[2] + 1 if self.fault == 'oversize' else 0)
            self.ret(0 if self.fault == 'oversize' else 0x80000002)
            return
        return super().hook(u, address, size, user)


def raw_read_fixture(lab):
    ctx, dst, actual, io = RAM + 0x10000, RAM + 0x20000, RAM + 0x22000, HEAP + 0xe00000
    lab.files[PATH] = bytes((index + 7) % 256 for index in range(6000))
    lab.fds[100] = dict(path=PATH, pos=0)
    lab.u.mem_write(ctx, bytes(56))
    lab.w32(ctx + 12, 100)
    lab.w64(ctx + 24, len(lab.files[PATH]))
    lab.w64(ctx + 40, io)
    lab.w32(ctx + 48, IO_BYTES)
    lab.u.mem_write(dst, bytes([0xa5]) * (IO_BYTES + 1))
    lab.w32(actual, 0xdeadbeef)
    return ctx, dst, actual, io


def test_buffered_short_read_preserves_actual_and_bounds():
    lab = RawReadFault()
    ctx, dst, actual, io = raw_read_fixture(lab)
    assert lab.call('buffered_read', ctx, dst, IO_BYTES, actual) == 0
    assert lab.r32(actual) == 997
    assert bytes(lab.u.mem_read(dst, 997)) == lab.files[PATH][:997]
    assert bytes(lab.u.mem_read(dst + 997, IO_BYTES + 1 - 997)) == bytes([0xa5]) * (IO_BYTES + 1 - 997)
    assert lab.io_trace == [('sync', io, IO_BYTES), ('read', io, IO_BYTES), ('sync', io, IO_BYTES)]


def test_buffered_read_error_and_oversized_actual_do_not_copy():
    for fault in ('error', 'oversize'):
        lab = RawReadFault(fault)
        ctx, dst, actual, io = raw_read_fixture(lab)
        assert lab.call('buffered_read', ctx, dst, IO_BYTES, actual) != 0
        assert lab.r32(actual) == 0
        assert bytes(lab.u.mem_read(dst, IO_BYTES + 1)) == bytes([0xa5]) * (IO_BYTES + 1)
        assert lab.io_trace == [('sync', io, IO_BYTES), ('read', io, IO_BYTES), ('sync', io, IO_BYTES)]
        gc.collect()


def test_buffered_oversized_request_is_rejected_before_io():
    lab = RawReadFault()
    ctx, dst, actual, _ = raw_read_fixture(lab)
    assert lab.call('buffered_read', ctx, dst, IO_BYTES + 1, actual) != 0
    assert lab.r32(actual) == 0 and not lab.io_trace
    assert lab.fds[100]['pos'] == 0
    assert bytes(lab.u.mem_read(dst, IO_BYTES + 1)) == bytes([0xa5]) * (IO_BYTES + 1)


def prepare_import(lab):
    path, info, dst, io = RAM + 0x6000, RAM + 0x7000, RAM + 0x80000, HEAP + 0xe00000
    lab.files[PATH] = wav(5000)[0]
    lab.u.mem_write(path, PATH.encode('ascii') + b'\0')
    lab.u.mem_write(info, bytes([0x5a]) * 20)
    return path, dst, info, io


def test_buffered_import_rejects_unowned_io_ranges():
    for mode in ('null', 'unaligned', 'short', 'long'):
        lab = IOTrace()
        path, dst, info, io = prepare_import(lab)
        pointer = 0 if mode == 'null' else io + (1 if mode == 'unaligned' else 0)
        size = IO_BYTES - 64 if mode == 'short' else IO_BYTES + 64 if mode == 'long' else IO_BYTES
        assert lab.call('m2_native_import_buffered', path, dst, MAX_PCM, info, pointer, size) == 1
        assert not lab.io_trace and not lab.fds
        assert bytes(lab.u.mem_read(info, 20)) == bytes([0x5a]) * 20
        gc.collect()


class SyntheticDMAViews(Lab):
    """Model only: DMA updates backing RAM while the CPU can retain dirty/stale lines.

    Pre-sync removes a modeled dirty CPU view. Post-sync exposes pending device
    bytes only if pre-sync happened; otherwise a dirty writeback wins. Neither
    this model nor Unicorn proves the camera's actual cache/DMA behavior.
    """
    def __init__(self, pre_sync=True, post_sync=True):
        self.model_pre_sync = pre_sync
        self.model_post_sync = post_sync
        self.cleaned = set()
        self.device_pending = {}
        self.device_reads = 0
        self.visible_device_writes = 0
        super().__init__()
        self.instruction_limit = 80000000

    def hook(self, u, address, size, user):
        if address == SYNC:
            pointer, length = u.reg_read(X0), u.reg_read(X0 + 1)
            if pointer in self.device_pending:
                data, precleaned = self.device_pending.pop(pointer)
                if precleaned and self.model_post_sync:
                    u.mem_write(pointer, data)
                    self.visible_device_writes += 1
            elif self.model_pre_sync:
                self.cleaned.add((pointer, length))
            self.events.append(('flush', pointer, length))
            self.ret(0)
            return
        if address == READ:
            x = [u.reg_read(X0 + offset) for offset in range(4)]
            f = self.fds[x[0]]
            data = self.files[f['path']][f['pos']:f['pos'] + min(x[2], 997)]
            f['pos'] += len(data)
            precleaned = any(start <= x[1] and x[1] + len(data) <= start + length
                             for start, length in self.cleaned)
            self.cleaned.clear()
            self.device_pending[x[1]] = (data, precleaned)
            self.device_reads += 1
            self.w32(x[3], len(data))
            self.ret(0)
            return
        return super().hook(u, address, size, user)


def test_synthetic_dma_views_require_owned_pre_and_post_sync():
    direct = SyntheticDMAViews()
    path, dst, info, _ = prepare_import(direct)
    assert direct.call('m2_native_import', path, dst, MAX_PCM, info) == 7
    assert direct.device_reads == 1 and direct.visible_device_writes == 0
    assert not direct.fds
    for pre_sync, post_sync in ((False, True), (True, False), (True, True)):
        lab = SyntheticDMAViews(pre_sync, post_sync)
        path, dst, info, io = prepare_import(lab)
        result = lab.call('m2_native_import_buffered', path, dst, MAX_PCM, info, io, IO_BYTES)
        print('DMA_MODEL', dict(pre_sync=pre_sync, post_sync=post_sync, rc=result,
                                device_reads=lab.device_reads, visible_writes=lab.visible_device_writes,
                                pcm_head=bytes(lab.u.mem_read(dst, 16)).hex()), flush=True)
        if pre_sync and post_sync:
            assert result == 0
            assert bytes(lab.u.mem_read(dst, 5184)) == wav(5000)[1] + bytes(184)
            assert lab.visible_device_writes == lab.device_reads >= 10
        else:
            assert result == 7 and lab.visible_device_writes == 0
        assert not lab.fds
        gc.collect()


def test_first_staging_mutation_is_detected_even_if_pair_now_matches():
    lab = Lab()
    scan(lab, pcm_wav(bytes(192)))
    changed = bytearray(192)
    changed[64] = 1
    def change_first_during_second_read(current):
        if current.import_calls % 2:
            current.files[PATH] = pcm_wav(bytes(192))
        else:
            current.u.mem_write(aligned(retained(current, 0)) + 64, b'\1')
            current.files[PATH] = pcm_wav(bytes(changed))
    lab.before_import = change_first_during_second_read
    lab.select(6)
    assert lab.field('import_status', True) == 14
    assert lab.field('confirm_reason', True) == 128 and lab.field('confirm_diff', True) == UINT_MAX
    assert lab.field('raw_first_hash', True) != lab.field('first_recheck_hash', True)
    assert lab.field('cache_count', True) == 0 and not profiles(lab)
    assert not any(event[0] == 'bind' for event in lab.events)


def fnv(pcm):
    value = 2166136261
    for byte in pcm:
        value = ((value ^ byte) * 16777619) & UINT_MAX
    return value


def colliding_pcm_pair():
    # Meet in the middle on four suffix bytes. This deliberately exercises a
    # real FNV-1a collision so equality cannot accidentally rely on diagnostics.
    original = bytes(192)
    target = fnv(original)
    inverse = pow(16777619, -1, 1 << 32)
    for seed in range(1, 12):
        prefix = bytes([seed]) + bytes(187)
        start = fnv(prefix)
        forwards = {}
        for first in range(256):
            value = ((start ^ first) * 16777619) & UINT_MAX
            for second in range(256):
                forwards[((value ^ second) * 16777619) & UINT_MAX] = bytes([first, second])
        for fourth in range(256):
            before_fourth = ((target * inverse) & UINT_MAX) ^ fourth
            for third in range(256):
                middle = ((before_fourth * inverse) & UINT_MAX) ^ third
                if middle in forwards:
                    candidate = prefix + forwards[middle] + bytes([third, fourth])
                    assert candidate != original and fnv(candidate) == target
                    return original, candidate
    raise AssertionError('failed to construct deterministic FNV collision')


def test_full_byte_confirmation_rejects_equal_diagnostic_hashes():
    first, second = colliding_pcm_pair()
    lab = Lab()
    scan(lab, pcm_wav(first))
    def alternate(current):
        current.files[PATH] = pcm_wav(first if current.import_calls % 2 else second)
    lab.before_import = alternate
    lab.select(6)
    assert lab.field('import_status', True) == 14
    assert lab.field('raw_first_hash', True) == lab.field('raw_second_hash', True)
    assert lab.field('confirm_reason', True) == 1 and lab.field('confirm_diff', True) == 0
    assert lab.field('cache_count', True) == 0 and not profiles(lab)


TESTS = [
    test_repeated_mismatch_does_not_fill_cache,
    test_metadata_is_compared_even_with_identical_padded_pcm,
    test_failed_copy_is_rejected_and_pending_is_reused,
    test_bind_busy_keeps_pending_unpublished,
    test_published_pcm_is_immutable_across_reselection_and_failure,
    test_native_reads_use_dedicated_io_for_headers_and_pcm,
    test_buffered_short_read_preserves_actual_and_bounds,
    test_buffered_read_error_and_oversized_actual_do_not_copy,
    test_buffered_oversized_request_is_rejected_before_io,
    test_buffered_import_rejects_unowned_io_ranges,
    test_synthetic_dma_views_require_owned_pre_and_post_sync,
    test_first_staging_mutation_is_detected_even_if_pair_now_matches,
    test_full_byte_confirmation_rejects_equal_diagnostic_hashes,
]
for test in TESTS:
    test()
    passed(test.__name__, synthetic_model=test is test_synthetic_dma_views_require_owned_pre_and_post_sync)

report = {
    'status': 'PASS_BOUNDED_ARM_STAGED_REGRESSION',
    'payload_sha256': hashlib.sha256(integration.PAYLOAD).hexdigest(),
    'shared_integration_tests': len(integration.rows),
    'staged_tests': len(rows),
    'rows': rows,
    'executed': ['actual compiled staged picker and buffered importer',
                 'original native file wrappers and status conversion',
                 'actual byte comparisons, metadata checks and pending ownership transitions'],
    'mocked': ['card filesystem', 'allocator', 'cache maintenance effects',
               'upper audio worker and UI storage'],
    'synthetic_dma_model': True,
    'synthetic_dma_model_is_hardware_evidence': False,
    'full_QEMU': False,
    'hardware': False,
}
(C / 'staged-regression-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('ALL_STAGED_PASS', len(rows), flush=True)
