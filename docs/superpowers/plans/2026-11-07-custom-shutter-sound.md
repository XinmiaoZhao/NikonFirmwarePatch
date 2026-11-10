# Card WAV Shutter-Sound Stacker Implementation Plan

> Naming note: the feature was later renamed to **custom shutter sound** (branch `feature/custom-shutter-sound`, package `z8shuttersound/`, CLI `shutter_sound.py`). The historical text below keeps the original "card WAV" wording and commit subjects.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the PIPA12344 card WAV custom shutter-sound port to NikonFirmwarePatch as a post-build stacker (Approach A): four feature groups build an equal-length base, the WAV unit stacks on top, and the package is repacked with a longer module 2.

**Architecture:** Vendor the `z8shuttersound/` package from the PIPA12344/NikonFirmwarePatch-04.18 fork (superset: prebuilt zero-slot unit mode + source mode). A new top-level CLI `shutter_sound.py` composes `features.build()` → `z8shuttersound.stack.stack()` → `z8shuttersound.stack.pack()` and runs an independent stacked audit. `features.py`, recipes and `patch.py` stay untouched. The WAV picker label IDs are renumbered from 0xC54–0xC68 to 0xD00–0xD14 to clear the collision with main's `STRING_IDS` (anamorphic 3153–3160, h265 3161–3216).

**Tech Stack:** Python 3.10+ stdlib build path; LLVM 19.1.7 (`/home/gjk/git-repos/Nikon_Z8_RE/tools/llvm-19.1.7/bin`) for unit regeneration; Unicorn 2.1.4 (dev-only) for the vendored ARM suites; existing repo venv conventions.

**Spec:** This plan (design was approved in conversation 2026-11-07). Provenance references: `PIPA12344/z8-card-wav` docs/INTEGRATION.md, fork CHANGELOG v04.18/v04.23.

## Global Constraints

- Work ONLY in worktree `/home/gjk/git-repos/nfp-shuttersound-wt`, branch `feature/custom-shutter-sound`. Never modify the main checkout or `main` branch; other agents share the parent tree.
- Firmware input: exact official Z8 C3.11, 99,051,117 bytes, SHA-256 `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`; main checkout has it at `firmware/Z_8_0311.bin` (read-only use; never commit).
- No firmware bytes in git: the pinned `resources/shuttersound.bin` must carry all 10 displaced-instruction slots zeroed (`displaced_*` symbols, 4 zero bytes each); `.gitignore` needs an explicit `!` exception.
- Version `NN.NN`, tag `[a-z][0-9]`, module name `eg2070_\d{4}[a-z]\d\.bi`. Stacked identity flows from the base tail; `shutter_sound.py` must audit all three version fields plus the trailer.
- Confirmation hardening (M2_CONFIRM_IMPORT / M2_CONFIRM_RETRY / M2_STAGED_CONFIRM) is unconditional — port the standalone z8-card-wav behaviour, NOT the fork's version-gated logic (a main version like 04.07 must not disable it).
- WAV label IDs: base `0xD00` (3328), 21 IDs, end-exclusive `0xD15` (3349), must stay ≤ 4095 (AArch64 12-bit CMP immediate) and disjoint from main `STRING_IDS` range [3137, 3225).
- Code comments in English (repo convention); user-facing docs bilingual (README/CHANGELOG style).
- Vendored `z8shuttersound/` stays GPL-3.0-or-later with its LICENSE/NOTICE/source-provenance.json intact; root NOTICE.md gains the attribution chain (s3lemming/z9-firmware-patch → PIPA12344 fork 04.23 → z8-card-wav → this port).
- Builds and `--keep` artifacts stay inside the worktree (gitignored `build/`).

## Review Focus

1. **Upstream grows STRING_IDS past 3225 later** — semantic text-resolution collision with no build-time assert; the ID-disjointness test must fail loudly in CI (Task 3).
2. **Identity mix-ups** — stacked firmware must carry the requested version in all three fields + trailer; audit re-derives from the stock input, never trusts the candidate manifest (Task 4).
3. **Compiler drift** — the pinned unit records `clang 19.1.7`; source-mode byte-parity only holds under that compiler; parity tests must use `tools/llvm-19.1.7` and the unit JSON must record the compiler (Tasks 3, 5).
4. **Base growth regression** — if upstream features ever grow the EG beyond stock length, stacking must refuse (length + CRC asserts already in builder; add explicit test) (Task 5).
5. **Patched/stacked output fed back as input** — `shutter_sound.py` must accept only the exact stock input; negative control required (Task 5).

---

### Task 1: Baseline regression in the worktree

**Files:**
- Create: none (environment only; `.venv/` inside worktree, untracked)

**Interfaces:**
- Produces: a working venv + confirmed-green baseline (15-combo suite) that later tasks must not break.

- [x] **Step 1: Create isolated venv with uv**

```sh
cd /home/gjk/git-repos/nfp-shuttersound-wt
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

- [x] **Step 2: Run the existing 15-combo baseline against the stock input**

```sh
mkdir -p build
.venv/bin/python -B tests/validate_combinations.py --stock /home/gjk/git-repos/Nikon_Z8_RE/NikonFirmwarePatch/firmware/Z_8_0311.bin --report build/baseline-combos.json
```
Expected: all 15 rows PASS, negative controls REJECTED, report written.

- [x] **Step 3: Commit nothing yet; record baseline output hash for later comparison**
Run `sha256sum build/baseline-combos.json` and keep the value in the task notes.

### Task 2: Vendor the z8shuttersound package (fork superset, adapted)

**Files:**
- Create: `z8shuttersound/` (LICENSE, NOTICE, `__init__.py`, `builder.py`, `stack.py`, `firmware/*.c|h`, `source-provenance.json`, `verify_integration.py`, `verify_staged.py`) — copied from `/tmp/nfp-0418/z8shuttersound/` then adapted
- Modify: none yet

**Interfaces:**
- Produces: `z8shuttersound.builder.build(module, output, base_module=None, llvm=None, tail=..., code_source='prebuilt')`, `z8shuttersound.stack.stack(stock_eg, base_eg, llvm=..., keep=None, code_source='prebuilt') -> (eg_bytes, report)`, `z8shuttersound.stack.pack(package, eg, name) -> packet`, `z8shuttersound.stack.unpack(package, packet, name) -> eg`. Adaptations: unconditional confirm flags; single pinned unit `resources/shuttersound.json` (drop fork's version-suffix unit selection); `stack.py` keeps `from z8prores.package import ...`.

- [x] **Step 1: Copy the package from the fork checkout**
`cp -r /tmp/nfp-0418/z8shuttersound .` inside the worktree.

- [x] **Step 2: Adapt builder.py confirmation gating**
Replace the identity-gated block (`identity=re.fullmatch(...)` through `UNIT = ROOT.parent/'resources'/('shuttersound'+suffix+'.json')`) with unconditional `confirmed_import=confirmation_retry=staged_confirmation=True`, `flags.extend(['-DM2_CONFIRM_IMPORT=1','-DM2_CONFIRM_RETRY=1','-DM2_STAGED_CONFIRM=1'])`, `UNIT=ROOT.parent/'resources'/'shuttersound.json'`. Keep the source-mode unit emission/comparison and prebuilt fill logic unchanged.

- [x] **Step 3: Smoke-import and wav-on-stock-source build**
`Z8_LLVM_BIN=/home/gjk/git-repos/Nikon_Z8_RE/tools/llvm-19.1.7/bin .venv/bin/python -B -c "from z8shuttersound import stack, builder; print('ok')"`.
Then a source-mode stack on a version-stamped stock base must succeed (see Task 4's `version_base`; until then call `builder.build` directly with a hand-made base, keep dir `build/t2-src`).

- [x] **Step 4: Commit**
`git add z8shuttersound && git commit -m "Vendor z8shuttersound card WAV port from PIPA12344 fork 04.23 (GPL-3.0-or-later, unconditional confirmation)"`

### Task 3: Renumber WAV label IDs and pin the reviewed unit

**Files:**
- Modify: `z8shuttersound/builder.py` (row id `0xc54`→`0xD00`; hooks `cmp w1,#0xc54/c69`→`#0xD00/#0xD15`; expose constants `WAV_LABEL_BASE=0xD00`, `WAV_LABEL_COUNT=21`), `z8shuttersound/firmware/picker.c:354,426` (`0xc54`→`0xD00`, `0xc55+r-6`→`0xD01+r-6`), `z8shuttersound/verify_integration.py:292,299` (test ids → `0xD00`)
- Create: `resources/shuttersound.bin`, `resources/shuttersound.json` (pinned, zero-slot unit from LLVM 19.1.7), `tests/test_shuttersound_ids.py`
- Modify: `.gitignore` (add `!resources/shuttersound.bin`)

**Interfaces:**
- Produces: `z8shuttersound.builder.WAV_LABEL_BASE/COUNT` consumed by the disjointness test; pinned unit consumed by `code_source='prebuilt'`.

- [x] **Step 1: Write the failing guard test** `tests/test_shuttersound_ids.py` (stdlib only, CI-safe): parse `z8patch/shared.py` `STRING_IDS`/`STRING_END` via import; import `z8shuttersound.builder`; assert `range(WAV_LABEL_BASE, WAV_LABEL_BASE+WAV_LABEL_COUNT)` ∩ `range(3137, STRING_END)` is empty, `WAV_LABEL_BASE+WAV_LABEL_COUNT <= 4095`, and that `resources/shuttersound.bin` exists with SHA-256 matching `resources/shuttersound.json` (skip unit-file assertions if absent, so the test can drive the renumber first).
- [x] **Step 2: Run it, confirm FAIL** (IDs still 0xC54 overlap anamorphic/h265).
- [x] **Step 3: Apply the renumber** to builder.py, picker.c, verify_integration.py; grep `0xc5` in `z8shuttersound/` to catch stragglers.
- [x] **Step 4: Regenerate the unit in source mode with LLVM 19.1.7** via a stack build with `--keep build/t3-unit` (or direct builder call); the keep dir's `shuttersound.bin`/`shuttersound.json` become the pinned `resources/` files. Verify the 10 `displaced_*` slots are zero in the pinned .bin.
- [x] **Step 5: Run the ARM suites against the regenerated unit** (dev-only): `uv pip install --python .venv/bin/python unicorn==2.1.4`; run `z8shuttersound.verify_integration` + `z8shuttersound.verify_staged` against the keep dir. Expected: 27 + 13 PASS.
- [x] **Step 6: Guard test green, `.gitignore` exception added; commit** `git add -f resources/shuttersound.bin` plus json/test/ignore; message "Renumber WAV labels to 0xD00 family; pin zero-slot shuttersound unit (clang 19.1.7)".

### Task 4: Stacker CLI `shutter_sound.py` with independent stacked audit

**Files:**
- Create: `shutter_sound.py` (top level, mirrors patch.py UX)
- Modify: none (features.py, patch.py, verify.py untouched)

**Interfaces:**
- Consumes: `features.build(eg, version, tag, features, compiler, code_source) -> (eg, report)`; `z8shuttersound.stack.{stack,pack,unpack}`; `z8prores.package.{Package, require_official_input, sha}`.
- Produces: CLI `shutter_sound.py <firmware> (--features F... | --interactive | --shutter-sound-only) --version NN.NN --tag [a-z][0-9] [--code-source prebuilt|source] [--llvm-bin DIR] [--keep DIR] --output DIR` plus `--check`. Internals reused by Task 5: `build_stacked(raw, features, version, tag, code_source, llvm, keep) -> (packet, meta)` and `verify_stacked(original, candidate, features, version, tag, code_source, llvm) -> report`.

- [x] **Step 1: Write the failing test script** `tests/validate_shuttersound.py` (mirrors `validate_combinations.py`: `--stock`/`--report`, external fixture). Cases: (a) one combo (photo-tools) + wav builds, audits, round-trips; (b) negative controls: patched input reject, wrong version/tag reject, tampered append byte reject, non-stock EG length in base reject. It fails now (`shutter_sound` import missing).
- [x] **Step 2: Implement `shutter_sound.py`**: stock input check → base build (`features.build`; for `--shutter-sound-only` stamp a version base in-code: three version fields + CRC on stock, mirroring z8-card-wav cli.version_base) → `stack.stack(stock, base, llvm, keep, code_source)` → module name `eg2070_<ver><tag>.bi` → `stack.pack` → write `Z_8_<ver>.bin`, `manifest.json`, `SHA256SUMS.txt` (patch.py conventions: fsync, exclusive create, provenance).
- [x] **Step 3: Implement `verify_stacked`**: `stack.unpack` (container + other modules byte-identical + module name) → extract EG → re-derive base via `features.build` from the same stock → re-run the WAV builder on that base in a temp dir → EG audit: allowed windows = {0xEB29FC:12, 0x14EAA90:8, stock_end-11:8} ∪ feature edits ∪ WAV report patches; every other byte in the stock prefix equal; appended tail (from base end to module end) byte-equal to the re-derived payload; CRC==0; three version fields + trailer equal requested identity.
- [x] **Step 4: Run `tests/validate_shuttersound.py`** against the stock input → all PASS.
- [x] **Step 5: Commit** "Add shutter_sound.py stacker CLI with independent stacked verification".

### Task 5: Full matrix validation and repo wiring

**Files:**
- Modify: `tests/validate_shuttersound.py` (extend to the full matrix), `tools/check_repository.py`, `tools/check_release.py` (CODE_FILES + SOURCE_FILES), `tools/build_release.py` (SOURCE_FILES), `.github/workflows/host-checks.yml` (add `tests/test_shuttersound_ids.py`), `requirements-test.txt` (new: `unicorn==2.1.4`)
- Create: `docs/custom-shutter-sound.md` (user-facing usage, bilingual)

**Interfaces:**
- Produces: `tests/validate_shuttersound.py --stock ... --report ...` covering 16 selections (15 combos + wav-only) × prebuilt, plus all-features+wav source parity; CI-facing `tests/test_shuttersound_ids.py` green without unicorn/firmware.

- [x] **Step 1: Extend the matrix**: loop all 15 nonempty combos + `--shutter-sound-only`; each: build → `verify_stacked` → also `verify_pair`-style feature detection on the pre-stack base inside `build_stacked` (recipe check stays active); assert other modules unchanged; append one tamper negative per class (window byte, append byte, other-module byte).
- [x] **Step 2: Source/prebuilt parity**: all-features+wav with `--code-source source` under `tools/llvm-19.1.7` must byte-equal prebuilt output.
- [x] **Step 3: Run the full matrix** → 16 PASS rows + parity + negatives; save `build/shuttersound-matrix.json`.
- [x] **Step 4: Re-run the Task 1 baseline** `validate_combinations.py` → identical results (proves zero impact on the four-feature path).
- [x] **Step 5: Allowlists + CI + requirements-test.txt + docs/custom-shutter-sound.md**; run `tools/check_repository.py --all` green.
- [x] **Step 6: Commit** "Full-matrix card WAV validation, allowlists, CI wiring and usage doc".

### Task 6: Documentation and changelog

**Files:**
- Modify: `README.md` (bilingual section: what it adds, CUSTOM_SOUND card prep, 48 kHz/16-bit/stereo/≤1.5 s WAV rules, CUS behaviour, M2SND0/1.CFG persistence, build commands, w-tag convention), `CHANGELOG.md` (Unreleased section), `NOTICE.md` (provenance chain + GPL-3.0-or-later scope for vendored code)

- [x] **Step 1: Write the three doc updates** following existing bilingual structure.
- [x] **Step 2: Verify examples in README actually run** (copy-paste commands with the stock fixture in a temp output).
- [x] **Step 3: Commit** "Document the card WAV stacker (README, CHANGELOG, NOTICE)".

### Out of scope (follow-ups, do not implement now)

- QEMU full-system boot comparison of the stacked firmware (parent repo `z8-qemu` lab) — separate session.
- Approach B promotion (fifth first-class feature, 31 recipes).
- Upstream PRs to XinmiaoZhao/NikonFirmwarePatch or PIPA12344/z8-card-wav.
