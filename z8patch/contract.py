"""Independent structural checks, using fixed firmware facts and group semantics.

No composer, assembler, linker or resource-generator imports; the only
inputs are the two images, the feature list and (for the vrotate unit
bound) the frozen reviewed recipe resources/compiled.json.

The build-time address-coupling guards at the bottom (2026-11-09
vrotate-fix t3) are the machine-enforced form of the NikonFirmwarePatch
iron rules: unit sources stay pure code + pool (.org ban), emit-region
bytes may only name registered unit entry symbols, and a unit's data
stores must resolve outside the read-only cave.
"""
import json, re, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_contract(old,new,features):
    def need(ok,message):
        if not ok:raise ValueError('Composition contract: '+message)
    base=0x40160000
    read=lambda image,fmt,at:struct.unpack_from(fmt,image,at)
    framing,quality,log,photo,vr=(s in features for s in ('framing','video-quality','log-colour','photo-tools','video-orientation'))
    video=framing or quality or log or vr
    if video:
        rows,events,count=read(new,'<QQH',0x4BCC2C0)
        need((rows,events,count)==(0x40A30000,0x40A31000,44+int(quality)+int(vr)),'video menu allocation/count')
        ids=[read(new,'<I',rows-base+44*i+24)[0] for i in range(count)]
        original=[read(old,'<I',0x3AA4758+44*i+24)[0] for i in range(44)]
        need(len(ids)==len(set(ids)) and set(ids)==set(original)|({0x315A} if quality else set())|({0x315B} if vr else set()),'video menu items')
        if log:need(ids.index(0x2E38)==ids.index(0x2FC1)+1,'Log after file type')
        if quality:need(ids.index(0x311B)==ids.index(0x3118)+1 and ids.index(0x315A)==ids.index(0x311B)+1,'quality rows order')
        if vr:need(ids.index(0x315B)==ids.index(0x30A6)-1,'orientation row directly before the image-area row')
        for enabled,site,item,load in ((log,0x40572940,0x2E38,0x40572930),(quality,0x4057295C,0x311B,0x4057294C),(framing,0x40572978,0x310F,0x40572968)):
            need(new[load-base:load-base+4]==old[load-base:load-base+4],f'original hidden-item identity {item:#x}')
            need(new[site-base:site-base+4]==(bytes.fromhex('02008052') if enabled else old[site-base:site-base+4]),f'visibility {item:#x}')
        mask=read(new,'<I',0x40980F00-base)[0]
        need(mask==int(framing)+2*int(quality)+4*int(log)+8*int(vr),'shared feature mask')
        ptrs=read(new,'<5Q',0x40980F08-base)
        need([bool(p) for p in ptrs]==[quality,quality,framing,log,vr],'shared callback presence')
        # The unfrozen shared unit runs an unconditional five-slot callback
        # ring reading CONFIG+0x28 even in four-group builds, where that
        # slot keeps its stock bytes -- pin the stock firmware fact those
        # builds rely on (a nonzero stock byte would be blr'd as a callback).
        need(not any(old[0x40980F28-base:0x40980F30-base]),'fifth callback slot stock zero')
        need(0x40980000<=read(new,'<Q',0x4BF3A80)[0]<0x40980F00,'shared refresh entry')
    else:
        need(new[0x4BCC2B0:0x4BCC300]==old[0x4BCC2B0:0x4BCC300],'photo-only video page preservation')
        need(new[0xEB62EC:0xEB62F0]==old[0xEB62EC:0xEB62F0],'photo-only bank preservation')
    # 36 offset arrays: native text offsets are byte-for-byte retained, added IDs
    # are present exactly for their selected modules. String IDs stay fixed across masks.
    entries=3227 if vr else 3226
    ranges=[(3137,3142,framing),(3142,3147,photo),(3147,3153,quality),
            (3153,3161,framing),(3161,3217,quality),(3217,3225,log)]+([(3225,3226,vr)] if vr else [])
    for language in range(36):
        table=read(new,'<Q',0x311C5A0+8*language)[0]
        original_table=read(old,'<Q',0x311C5A0+8*language)[0]
        need(table==0x40A70000+language*entries*4,'language table position')
        offsets=read(new,f'<{entries}i',table-base)
        need(offsets[:3137]==read(old,'<3137i',original_table-base),'native string offsets')
        blob=read(new,'<Q',0x387AF58+8*language)[0]
        for lo,hi,enabled in ranges:
            for ident in range(lo,hi):
                a,b=blob+offsets[ident],blob+offsets[ident+1]
                need(0x40A50000<=a<=b<=0x40A70000,'added string bounds')
                need(bool(b-a)==enabled,'selected string presence')
                new[a-base:b-base].decode('utf-16le')
    loader=read(new,'<II',0x1024D8C)
    end=((loader[0]>>5)&65535)|(((loader[1]>>5)&65535)<<16)
    need(0x40AE2000<=end<=0x40C00000 and end%4096==0,'copy boundary covers strings')
    if log:need(end>=0x40B50000 and not any(new[0x40B0E000-base:0x40B0F100-base]),'Log private state initialized')
    if quality:need(new[0x40A40000-base]==0,'star force initially clear')
    if framing:need(not any(new[0x4097F000-base:0x40980000-base]),'AP state initialized')
    vrotate=None
    if vr:
        # Fixed facts of the vrotate unit (cave 0x40A08000-0x40A10000;
        # symbol offsets below are fixed facts of the reviewed recipe).
        # The unit length comes from the frozen compiled.json itself, so
        # the reservation-tail bound cannot drift from the shipped bytes.
        units=json.loads((Path(__file__).resolve().parents[1]/'resources/compiled.json').read_text())['units']
        cave=0x40A08000;unit_end=cave+units['vrotate']['bytes']
        need(not any(old[cave-base:0x40A10000-base]),'vrotate cave free in stock')
        # T2b: the row-events clone rides its own fixed sub-window
        # 0x40A09000-0x40A09580; the gap between the unit and that window and
        # the tail past it stay stock zero.
        need(not any(new[unit_end-base:0x40A09000-base]),'vrotate cave gap stays stock zero')
        need(not any(new[0x40A09580-base:0x40A10000-base]),'vrotate cave tail stays stock zero')
        def branch_target(site,word):
            need(word>>26 in (0x05,0x25),f'vrotate hook branch shape at {site:#x}')
            delta=word&0x3FFFFFF
            if delta&0x2000000:delta-=0x4000000
            return site+delta*4
        need(read(old,'<I',0x40cefd60-base)[0]==0x97FFD09F,'vrotate matrix site stock word')
        need(cave<=branch_target(0x40cefd60,read(new,'<I',0x40cefd60-base)[0])<unit_end,'vrotate matrix hook branch into the cave')
        need(old[0x40d17728-base:0x40d17730-base]==bytes.fromhex('08de80d28863a0f2'),'vrotate latch site stock bytes')
        need(cave<=branch_target(0x40d17728,read(new,'<I',0x40d17728-base)[0])<unit_end,'vrotate latch hook branch into the cave')
        need(read(new,'<I',0x40d1772C-base)[0]==0xD503201F,'vrotate latch site trailing nop')
        need(struct.pack('<Q',0xA03D5C26A) in new[cave-base:unit_end-base],'vrotate active value byte literal in the unit')
        # A+ migration (2026-11-09 vrotate-fix t1 report): the unit state
        # lives in the boot-copied data mirror window EG [0x4B25800,0x4B25900)
        # (RAM 0xA0281A800).  Fixed facts: the window base literal rides in
        # the unit, the threshold and axis codes sit at the frozen offsets,
        # the one-shot latch and first-boot sentinel mirror bytes ship 0 and
        # the window tail byte is the 0xA5 magic (a boot-copy witness that
        # zero-initialized RAM cannot fake).
        need(struct.pack('<Q',0xA0281A800) in new[cave-base:unit_end-base],'vrotate state window literal in the unit')
        window=new[0x4B25800:0x4B25900]
        need(struct.unpack_from('<I',window,0x6C)[0]==0x3F333333,'vrotate threshold in the state window')
        need(window[0x70:0x76]==bytes((1,2,0,0,0,3)),'vrotate axis codes in the state window')
        need(window[0x76]==0 and window[0x77]==0,'vrotate one-shot latch and sentinel mirror bytes ship zero')
        need(window[0xFF]==0xA5,'vrotate state window magic byte')
        # T2b fixed events sub-window: the 44-record clone with its 0x3BB
        # terminator, three actions into the unit code, and the 8 B
        # emit-region pointer naming the window (the only external byte that
        # carries the table address).  `events` above is the VIDEO_EVENTS
        # pointer-table VA.
        table=new[0x40A09000-base:0x40A09580-base]
        need(read(table,'<Q',32*43)[0]==0x3BB,'vrotate events window terminator')
        need(sum(1 for i in range(44) if read(table,'<Q',32*i+8)[0] in range(cave,unit_end))==3,
            'vrotate events window toggle actions into the unit')
        need(read(new,'<Q',events-base+8*ids.index(0x315B))[0]==0x40A09000,'vrotate row transition table at the fixed events window')
        imms={ (w>>5)&0xFFFF for w in struct.unpack_from(f'<{(0x2EC)//4}I',new,cave-base) if w&0xFFE00000==0x52800000 }
        need({2466,2467}<=imms,'vrotate On/Off value ids in cave code')
        row_at=rows-base+44*ids.index(0x315B)
        need(read(new,'<I',row_at)[0]==3225,'vrotate row title id 3225')
        need(read(new,'<I',row_at+16)[0]==0x20901005,'vrotate row class word')
        need(read(new,'<I',row_at+20)[0]==0x1327,'vrotate row value sub-widget')
        vrotate=dict(cave=hex(cave),unit_end=hex(unit_end),events_window='0x40a09000-0x40a09580 (fixed cave sub-window)',state_window='0xa0281a800-0xa0281a900 (boot-copied data mirror, EG 0x4b25800)',row='0x315b',title_id=3225,value_ids=[2466,2467],sentinel='0x5A armed at first boot, mirror byte ships 0')
        need(end>=0x40A10000,'copy boundary covers the vrotate cave')
    return dict(status='PASS',video_menu=video,language_tables=36,offsets_per_language=entries,
                exact_group_visibility=True,zero_state=True,loader_end=hex(end),vrotate=vrotate)


# ---- Build-time address-coupling guards (2026-11-09 vrotate-fix t3) ----

ORG_DIRECTIVE = re.compile(r'(?m)^[ \t]*(?:(?:[\w.$]+|\d+):[ \t]*)?\.org\b')


def assert_no_org_directives(sources):
    """D1: unit assembly sources must not pin their own layout.

    sources is the SPECS-declared unit source list (z8patch.compiled.
    unit_asm_sources, which also enforces that every *.S under a
    registered unit's source directory carries a declaration): scanning
    the declared set instead of a filesystem glob means an assembly
    source must be registered in SPECS to be built or scanned at all.
    Every source is refused on any .org directive: unit sources carry
    only code + literal pool, and placement is owned by patcher-constant
    windows (the AGENTS.md iron rule).  .balign/.space stay legal --
    in-unit padding and self-referenced data do not freeze external
    bytes.  Returns the number of sources scanned.
    """
    sources = sorted(sources)
    if not sources:
        raise ValueError('Address coupling: no unit assembly sources '
                         'declared by SPECS')
    for path in sources:
        text = path.read_text()
        hit = ORG_DIRECTIVE.search(text)
        if hit:
            line = text.count('\n', 0, hit.start()) + 1
            raise ValueError('Address coupling: %s line %d uses the banned .org '
                             'directive: unit sources stay pure code + pool, '
                             'placement belongs to patcher-constant windows'
                             % (path, line))
    return len(sources)


# Registered-entry contract for the C-compiled units.  The frozen Release
# symbol tables (resources/compiled.json) carry no ELF binding bit, so the
# asm .global scan cannot apply: this explicit table is the registration.
# Every name below is an external-linkage hook/interface function that the
# owning patcher writes into an emit-region qword (pre-capture callback
# slots; pixel shift menu/modal/browser callbacks); each was proven by the
# t3 existing-stock sweep (build/t3, reports/t3-report.md).
C_UNIT_ENTRY_CONTRACT = {
    'precapture': ('precapture_display_mode', 'precapture_ordinary_code',
                   'precapture_ordinary_star', 'precapture_quality_code',
                   'precapture_quality_star'),
    'pixelshift': ('ps8_browser_entry', 'ps8_browser_exit', 'ps8_browser_refresh',
                   'psm_menu_action', 'psm_menu_available', 'psm_modal_action',
                   'psm_modal_entry', 'psm_modal_exit', 'psm_modal_ok',
                   'psm_modal_refresh', 'psm_photo_entry', 'psm_photo_refresh'),
    'pixelshift-af': (),
}


def asm_global_declarations(paths):
    """Names declared .global in the given assembly sources.

    For asm units this is the registered-entry signal: link_elf exposes
    every named label (code and data alike), so the module author's .global
    directive is what marks an interface entry.
    """
    declared = set()
    for path in paths:
        declared.update(re.findall(r'^[ \t]*\.globa?l[ \t]+([\w.$]+)',
                                   path.read_text(), re.M))
    return declared


def registered_unit_entries(name, entries, sources):
    """Registered entry VAs of a loaded unit, as (symbol -> VA).

    entries is the loaded symbol table (symbol -> VA).  C units use the
    explicit C_UNIT_ENTRY_CONTRACT (stale names fail loudly); asm units
    use their .global declarations intersected with the symbol table.
    """
    if name in C_UNIT_ENTRY_CONTRACT:
        missing = [s for s in C_UNIT_ENTRY_CONTRACT[name] if s not in entries]
        if missing:
            raise ValueError('Address coupling: C unit entry contract stale '
                             'for %s, symbols missing from the unit: %s'
                             % (name, missing))
        return {s: entries[s] for s in C_UNIT_ENTRY_CONTRACT[name]}
    declared = asm_global_declarations(sources) & set(entries)
    return {s: entries[s] for s in declared}


def assert_no_cross_region_pointers(rows, placements, base=0x40160000):
    """D2: emit-region bytes may only name registered unit entries.

    rows are the composition edits (dicts with offset/end/new, EG offsets);
    placements are (name, start_va, end_va, registered_entries) for every
    unit the composition loaded.  Every 8-byte-aligned qword of the emit
    region OUTSIDE the unit spans (bytes inside a unit span are that
    unit's own business -- internal self-references) whose value falls
    inside a unit span must equal a registered entry symbol VA of that
    unit -- otherwise the frozen external bytes would couple to
    unit-internal addresses that any code growth moves.  Branch/word-sized
    hook edits are out of scope (they relocate with every refreeze by
    design).
    """
    spans = [(start, stop) for _, start, stop, _ in placements]
    for row in rows:
        at, end, raw = row['offset'], row['end'], row['new']
        pos = at + (-(base + at)) % 8
        while pos + 8 <= end:
            if not any(start - base <= pos < stop - base for start, stop in spans):
                value = struct.unpack_from('<Q', raw, pos - at)[0]
                for name, start, stop, registered in placements:
                    if start <= value < stop and value not in registered.values():
                        raise ValueError(
                            'Address coupling: emit-region qword at %s names %s '
                            'inside unit %s [%s,%s) but it is not a registered '
                            'entry symbol of that unit'
                            % (hex(base + pos), hex(value), name,
                               hex(start), hex(stop)))
            pos += 8


def assert_no_cave_store_targets(code, base, window, whitelist=None):
    """Guard A: a unit's data stores must resolve outside the cave window.

    Disassembles the assembled unit (capstone; literal-pool bytes surface
    as skipdata, not instructions) and checks every data-writing
    instruction -- the whole st* family plus the LSE atomic writes
    (swp*/cas*); unknown store shapes are never a silent pass class.  The
    store's base register is resolved inside its basic block:

    * adr / adrp / ldr =literal / movz(+movk) / add-immediate chains give
      an absolute address (32-bit writes keep the paired X view in sync:
      zero-extension makes the X view take the same value); window hits
      raise;
    * an immediate addressing offset folds into the resolved address;
    * the stack (sp/wsp/x29) and incoming argument registers (x0..x7)
      are pass-through classes (the hook never owns those targets; an
      argument register REDEFINED inside the block is resolved, not
      passed through);
    * anything else (base loaded from memory, register-offset addressing,
      live-in non-argument registers) is conservatively rejected: prefer
      a false alarm over a missed cave write.

    whitelist maps a store's absolute address to a documented reason and
    is the explicit escape hatch for proven-safe unresolvable shapes.
    The resolution window is the store's basic block -- the straight-line
    run since the last control transfer of ANY kind (b/b.cond,
    cbz/cbnz/tbz/tbnz, br/blr/bl, ret; calls also clobber caller-saved
    registers).  Divergent redefinitions across a conditional branch and
    its join therefore cannot produce a false pass: any def outside the
    window is unresolvable and lands in the whitelist path.
    """
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    whitelist = whitelist or {}
    code = bytes(code)
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    insns = list(md.disasm(code, base))
    argument = {'x%d' % r for r in range(8)} | {'w%d' % r for r in range(8)}
    stack = {'sp', 'wsp', 'x29', 'w29'}
    defs = {}                       # register -> ('abs', value) | None

    def is_store(mnemonic):
        # Every AArch64 memory write: the st* family (str/strb/strh/stp/
        # stnp/stur/sttr/stlr plus sturb/sttrb/stadd/... variants) and the
        # LSE atomic exchanges -- an unrecognized store mnemonic is still
        # a store, never a silent pass.
        return (mnemonic.startswith('st') or mnemonic.startswith('swp')
                or mnemonic.startswith('cas'))

    def is_transfer(mnemonic):
        # Any control transfer ends the basic block (conservative window).
        return (mnemonic in ('ret', 'br', 'blr', 'bl', 'cbz', 'cbnz',
                             'tbz', 'tbnz')
                or mnemonic == 'b' or mnemonic.startswith('b.'))

    def paired(reg):
        return ('x' if reg[0] == 'w' else 'w') + reg[1:] \
            if reg[:1] in ('x', 'w') else None

    def lookup(reg):
        # An explicit None entry is a tracked-unresolvable state and must
        # not resurrect through the paired register: after an X write of
        # a value >= 2^32 the W view is dead, not inheritable.
        if reg in defs:
            return defs[reg]
        pair = paired(reg)
        return defs.get(pair) if pair else None

    def clear(reg):
        defs[reg] = None
        if reg.startswith('w'):
            defs['x' + reg[1:]] = None
        elif reg.startswith('x'):
            defs['w' + reg[1:]] = None

    def define(reg, state):
        # A 32-bit write zero-extends into the paired X register, so the
        # X view takes the SAME tracked value (I-1: dropping the alias
        # back to an "untouched argument register" was a silent pass).
        # A 64-bit write destroys the paired W view: a value below 2^32
        # keeps it exact (reading Wn after writing Xn yields the same
        # value), anything larger leaves the W view stale by construction
        # and must drop to unresolvable (A3: the stale value was readable
        # back through a W-view copy and fed a store base).
        defs[reg] = state
        if reg.startswith('w'):
            defs['x' + reg[1:]] = state
        elif reg.startswith('x'):
            defs['w' + reg[1:]] = state if not state[1] >> 32 else None

    def fail(address, message):
        if address in whitelist or hex(address) in whitelist:
            return
        raise ValueError('Store census: ' + message)

    for ins in insns:
        mnemonic, operands = ins.mnemonic, ins.op_str
        if is_store(mnemonic):
            inner = operands[operands.index('[') + 1:operands.rindex(']')]
            parts = [p.strip() for p in inner.split(',')]
            base_reg, offset = parts[0], None
            register_offset = len(parts) > 1 and not parts[1].startswith('#')
            if len(parts) > 1 and parts[1].startswith('#'):
                offset = int(parts[1][1:], 0)
            if base_reg in stack:
                pass                        # stack frame store
            elif base_reg in argument and base_reg not in defs:
                pass                        # incoming parameter target
            elif register_offset:
                fail(ins.address, 'store at %s uses register-offset '
                     'addressing (base %s): effective address not statically '
                     'resolvable' % (hex(ins.address), base_reg))
            else:
                state = defs.get(base_reg, 'live-in')
                if state == 'live-in':
                    fail(ins.address, 'cannot resolve store base %s at %s: '
                         'register has no definition in its basic block '
                         '(not an argument register)' % (base_reg, hex(ins.address)))
                elif state is None:
                    fail(ins.address, 'cannot resolve store base %s at %s: '
                         'register source is not statically resolvable'
                         % (base_reg, hex(ins.address)))
                else:
                    target = state[1] + (offset or 0)
                    if window[0] <= target < window[1]:
                        fail(ins.address, 'store at %s (base %s) resolves into '
                             'the cave window %s-%s: %s -- the cave is '
                             'read-only at EL0, unit data belongs in a '
                             'writable window'
                             % (hex(ins.address), base_reg,
                                hex(window[0]), hex(window[1]), hex(target)))
        elif mnemonic in ('adr', 'adrp'):
            dest = operands.split(',')[0].strip()
            target = int(operands.split('#')[1], 0)
            define(dest, ('abs', target))
        elif mnemonic == 'ldr' and '[' not in operands and '#' in operands:
            dest = operands.split(',')[0].strip()
            slot = int(operands.split('#')[1], 0) - base
            width = 4 if dest.startswith('w') else 8
            fmt = '<I' if width == 4 else '<Q'
            if 0 <= slot <= len(code) - width:
                define(dest, ('abs', struct.unpack_from(fmt, code, slot)[0]))
            else:
                clear(dest)
        elif mnemonic in ('movz', 'mov') and '#' in operands and '[' not in operands:
            dest, rest = [p.strip() for p in operands.split(',', 1)]
            imm = int(rest.split('#')[1].split(',')[0].strip(), 0)
            shift = 0
            if 'lsl' in rest:
                shift = int(rest.split('lsl')[1].replace('#', '').strip(), 0)
            if dest.startswith(('x', 'w')):
                define(dest, ('abs', imm << shift))
        elif mnemonic == 'movk':
            dest, rest = [p.strip() for p in operands.split(',', 1)]
            imm = int(rest.split('#')[1].split(',')[0].strip(), 0)
            shift = int(rest.split('lsl')[1].replace('#', '').strip(), 0) \
                if 'lsl' in rest else 0
            prior = defs.get(dest)
            if isinstance(prior, tuple):
                merged = (prior[1] & ~(0xFFFF << shift)) | (imm << shift)
                define(dest, ('abs', merged))
            else:
                clear(dest)
        elif mnemonic in ('add', 'sub') and operands.count(',') == 2:
            dest, source, immediate = [p.strip() for p in operands.split(',')]
            if immediate.startswith('#'):
                prior = lookup(source)
                delta = int(immediate[1:], 0) * (1 if mnemonic == 'add' else -1)
                if isinstance(prior, tuple):
                    value = prior[1] + delta
                    if dest.startswith('w'):
                        value &= 0xFFFFFFFF     # 32-bit wrap, zero-extended
                    define(dest, ('abs', value))
                else:
                    clear(dest)
            else:
                clear(dest)
        elif mnemonic == 'mov' and '#' not in operands and '[' not in operands:
            dest, source = [p.strip() for p in operands.split(',', 1)]
            state = lookup(source)
            if isinstance(state, tuple) and dest.startswith('w') and state[1] >> 32:
                state = None      # 64-bit source truncated into a 32-bit view
            if isinstance(state, tuple):
                define(dest, state)     # keeps the paired X/W view in sync
            else:
                clear(dest)
        elif not is_transfer(mnemonic):
            first = operands.split(',')[0].strip() if operands else ''
            if first.startswith(('x', 'w')) or first in ('sp', 'wsp'):
                clear(first)
        if is_transfer(mnemonic):
            defs.clear()          # any control transfer ends the basic block
