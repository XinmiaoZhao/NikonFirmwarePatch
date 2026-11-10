# Attribution and license scope

Copyright (C) 2026 NikonFirmwarePatch contributors.

The original tool source and the precompiled patch built from it are licensed under **GPL-3.0-only**; see [LICENSE](LICENSE). This license does not grant rights to user-supplied Nikon firmware. Output licensing depends on its contents, including any generated code; the complete output firmware is not represented as a GPL-licensed distribution. See [GNU's explanation of program output](https://www.gnu.org/licenses/gpl-faq.en.html#WhatCaseIsOutputGPL).

## References and dependencies

- The Nikon package XOR indexing format was studied with reference to [Nikon Hacker's Package.cs](https://github.com/simeonpilgrim/nikon-firmware-tools/blob/main/Nikon-Patch/LocalUI/Package.cs). This repository includes neither that C# source nor its lookup tables. The implementation recovers equivalent parameters from the user-supplied package.
- [Capstone 5.0.7](https://github.com/capstone-engine/capstone/tree/5.0.7) is installed separately to inspect generated ARM64 instructions. Its code and runtime are not bundled here; its license is available in [LICENSE.TXT](https://github.com/capstone-engine/capstone/blob/5.0.7/LICENSE.TXT).
- [Clang/LLVM](https://clang.llvm.org/) is an optional external dependency for explicit native-patch source builds and release preparation. The default Release toolkit uses the reviewed precompiled patch. No compiler or runtime is bundled.

The compatibility profile contains hashes and layout parameters, not firmware contents. The Release toolkit includes nine patch units (pre-capture, pixel-shift main/AF, open-gate, desqueeze, H.265, Log colour, quality icons and shared menus) compiled from the corresponding published C/assembly source, plus the custom shutter-sound addition as source (z8shuttersound/, byte-reproducible from the pinned LLVM recipe; its prebuilt unit follows the same toolkit policy). No Nikon input image or complete patched output is included. Other patch instructions are generated from source; menu structures and text are read from the user's input. The release manifest binds the source commit, compiler recipe and individual files.

The screenshots document the firmware interface running in an emulator. The tool's source-code license does not relicense the depicted firmware interface.

## Colour-report data and LUT

The report's spectral locus uses [CIE 2019 standard-observer data](https://doi.org/10.25039/CIE.DS.xvudnb9b), licensed CC BY-SA 4.0. The original source, conversion and the derived figure families (Chinese and English) are identified in [docs/data/README.md](docs/data/README.md); those figures remain CC BY-SA 4.0. The original report code, numerical samples, other original charts and the project's generated F-model LUT use this repository's GPL-3.0-only license. No Sony or RED PDF is redistributed. The F LUT is a project-generated post-production colour transform; it contains neither firmware nor camera media.

The colour-space figure also includes a calibration-matrix reference derived from the [Nikon Z 8 entry in LibRaw](https://github.com/LibRaw/LibRaw/blob/2caab57e269cc7fce17c3189e4d4d7e3e5861875/src/tables/colordata.cpp#L1044-L1045), which attributes the matrix to Adobe DNG Converter. The numerical entry and source identity are retained in [adobe-z8-matrix.json](docs/data/adobe-z8-matrix.json). No LibRaw source code is bundled for this illustration; the reference is not a measured sensor-gamut boundary.

## Custom shutter-sound port

The `z8shuttersound/` package is ported from [PIPA12344/z8-card-wav](https://github.com/PIPA12344/z8-card-wav) (GPL-3.0-or-later), the standalone extraction of the Z8 card WAV implementation in the [PIPA12344/NikonFirmwarePatch-04.18](https://github.com/PIPA12344/NikonFirmwarePatch-04.18) fork; its Z9 ancestor is [s3lemming/z9-firmware-patch](https://github.com/s3lemming/z9-firmware-patch) at commit 88a6f3e5195d7f38792dc8eddeb1526fde4096dc. Per-file provenance is retained in `z8shuttersound/source-provenance.json`; the original attribution and licences remain in `z8shuttersound/NOTICE` and `z8shuttersound/LICENSE`.

Local modifications: the picker label identifiers occupy 0xD00–0xD14, disjoint from this repository's feature string identifiers (guarded by `tests/test_shuttersound_ids.py`), and the confirmation/retry/staged-IO hardening is unconditional. The unit ships with all ten displaced-instruction slots zeroed; the slots are filled from the user's own firmware input at build time, so no original instruction words are distributed here. The unit recipe is pinned in `resources/shuttersound.json` and the reviewed prebuilt unit follows the Release toolkit policy.

The upstream authors have not reviewed or endorsed this port. This repository's four-group-plus-shutter-sound combinations passed complete on-camera verification with every feature enabled.

## Contributor acknowledgements

We thank the following contributors, **in no particular order**:

- [@Mei-MingLe (日月)](https://github.com/Mei-MingLe) for research ideas and analysis.
- [@heavensabove (pai)](https://github.com/heavensabove) for the foundational pixel-shift merge work and base code.
- [@y-g-jiang (Jiang Yaogeng)](https://github.com/y-g-jiang) and “地上相机AAA” for research ideas, suggestions and technical discussions that helped refine the approach.
- [@YouKakou (时雨)](https://github.com/YouKakou) for foundational exploration of Log3G10 colour. 感谢其对 Log3G10 色彩的基础探索。
- [@ShiSheng233 (锂化溴)](https://github.com/ShiSheng233) for open-gate ideas and the implementation framework, and for sharing the related reference implementation.
- [@aoyukkk (傲宇)](https://github.com/aoyukkk), [@South-Bridge (琴岛唯一指定哥布林)](https://github.com/South-Bridge), and “追晚霞的流浪汉” for development assistance, camera testing and feedback.

## Emulator acknowledgements

- [RdWing/z8-qemu](https://github.com/RdWing/z8-qemu): Z8 adaptation used as the basis of the offline camera-model environment.
- [WonderLantern/z9-qemu](https://github.com/WonderLantern/z9-qemu): upstream camera model and supporting tools on which the Z8 adaptation builds.
- [WonderLantern/z7-qemu](https://github.com/WonderLantern/z7-qemu): emulator and protocol-reference work consulted during development.
- [QEMU](https://www.qemu.org/) ([source repository](https://gitlab.com/qemu-project/qemu)): underlying emulation infrastructure.

These are external development tools and references. This repository does not redistribute their source or binaries, claim authorship of their work, or imply that their maintainers endorse this patch. Their respective notices and licenses remain applicable.

## Experimental use and responsibility

The generated firmware is experimental. Building, installing or using it can cause data loss, camera malfunction or permanent damage. Users must assess the risks and decide for themselves whether to install it. To the extent permitted by applicable law, the authors and contributors provide no warranty and accept no liability for data loss, camera damage or other losses arising from this project or its outputs. The limitations and disclaimer supplement the warranty and liability provisions in LICENSE; they do not alter third-party rights.

本项目生成的是测试版固件。构建、安装或使用可能造成数据丢失、相机故障或永久损坏。使用者须自行衡量风险并决定是否上机。在适用法律允许的范围内，作者及贡献者不提供担保，不对由此造成的数据损失、相机损失或其他损失承担责任。以上说明补充 LICENSE 中的无担保与责任限制条款，不改变第三方权利。
