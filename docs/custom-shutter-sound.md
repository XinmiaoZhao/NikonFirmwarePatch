# 自定义快门声 / Custom Shutter Sound

简体中文 · [English](#english)

## 功能

在四组功能（画幅、视频品质、Log 色彩、照片工具）任意组合之上叠加**自定义快门声**。保留原厂 A–E 快门声音；在设定菜单 → 照相机声音 → 快门音类型中出现 **Load WAV from card** 行，选中后外层类型显示 **CUS**，选择保存在卡内 `M2SND0.CFG` / `M2SND1.CFG`。

移植自 [PIPA12344/z8-card-wav](https://github.com/PIPA12344/z8-card-wav)（GPL-3.0-or-later，Z9 祖先 s3lemming/z9-firmware-patch，出处见 `z8shuttersound/NOTICE`、根 `NOTICE.md` 与 `z8shuttersound/source-provenance.json`）。选择器标签 ID 使用 **0xD00–0xD14**，与四组功能的字符串表 3137–3224 不相交（`tests/test_shuttersound_ids.py` 守护）；双次读取确认、有限重试与暂存 IO 始终启用。

## 构建与核验

```sh
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
# 任意非空功能组合 + 快门声（或 --shutter-sound-only 仅快门声；--interactive 交互选择）
python shutter_sound.py "/path/to/Z_8_0311.bin" --features framing video-quality log-colour photo-tools \
  --version 04.07 --tag w0 --output build/all-wav
```

- 版本 `NN.NN`、标签小写字母+数字（叠加版建议 `w` 族，如 `w0`）；基底与最终固件共享同一身份。
- `--code-source` 只作用于快门声单元：默认 `prebuilt` 使用仓库内 `resources/shuttersound.bin`（十个原厂指令槽清零，构建时从你的输入回填，无需编译器）；`source` 需 `--llvm-bin`（或 `Z8_LLVM_BIN`），且必须逐字节复现钉定单元（记录编译器为 LLVM 19.1.7）。
- 四组功能基底始终使用发行版评审过的预编译单元，与 `patch.py` 默认一致。
- 输出：`Z_8_<NNNN>.bin`、`manifest.json`、`SHA256SUMS.txt`；构建后自动独立核验（容器回读、从原厂输入全量重建、库存前缀窗口审计、身份字段）。

固件矩阵回归（16 种选择 × 预构建 + 源码等价 + 负控）：

```sh
python -B tests/validate_shuttersound.py --stock /path/to/Z_8_0311.bin --report build/shuttersound-matrix.json
```

ARM 级回归（27 项集成 + 13 项暂存/IO，需 `requirements-test.txt` 的 unicorn）：

```sh
python -B -m z8shuttersound.verify_integration <shutter-sound-build-dir>
python -B -m z8shuttersound.verify_staged <shutter-sound-build-dir>
```

## WAV 文件要求

| 项目 | 要求 |
|---|---|
| 编码 | RIFF WAV，未压缩 16-bit little-endian PCM |
| 采样率/声道 | 48 kHz，立体声 |
| 时长 | 大于 0，最长 1.5 秒；PCM 最多 288,000 字节 |
| 容器 | 最多 524,288 字节；解析最多 512 个 chunk |
| 文件名 | 可打印 ASCII，含 `.wav` 扩展名最多 111 字符 |
| 存放 | 存储卡根目录 `CUSTOM_SOUND` 文件夹，最多 20 个文件 |

转换示例：`ffmpeg -i input.wav -ar 48000 -ac 2 -c:a pcm_s16le my_shutter.wav`（超长请先剪辑）。

行为：单拍每张从头播放、可打断；C15 用开头最多 50ms，其他 Cxx 最多 40ms；连拍停止后余段播放一次。每次开机最多缓存 20 种不同内容（每项预留 288,000 字节）。读取差异、复制校验失败或音频 BUSY 时不发布新 PCM、不消耗永久缓存槽。修改同名 WAV 后应重新选择。

## 验证范围

- 离线：16 种选择全矩阵构建+独立核验通过；ARM 27+13 回归通过；源码/预构建等价（LLVM 19.1.7）。
- **实机验证**：四组功能与自定义快门声的全部功能组合完整实机验证通过。本工具不写卡、不操作相机；实验固件风险见 `NOTICE.md`。

## English

Stacks the **custom shutter sound** on top of any combination of the four feature groups. Stock A–E sounds remain; *Load WAV from card* appears under Setup menu → Camera sounds → Type, a custom selection shows **CUS**, and choices persist in `M2SND0.CFG`/`M2SND1.CFG` on the card.

Ported from [PIPA12344/z8-card-wav](https://github.com/PIPA12344/z8-card-wav) (GPL-3.0-or-later; Z9 ancestor s3lemming/z9-firmware-patch). Picker label IDs occupy **0xD00–0xD14**, disjoint from the feature string IDs 3137–3224 (guarded by `tests/test_shuttersound_ids.py`); confirmation, retry and staged IO are unconditional.

Build with `python shutter_sound.py <stock> --features ... --version NN.NN --tag w0 --output DIR` (or `--shutter-sound-only` / `--interactive`). The tag convention for shutter-sound builds is the `w` family. `--code-source` selects only the shutter-sound unit: the reviewed prebuilt zero-slot unit ships with the Release toolkit (git checkouts carry source only); `source` mode must byte-match the pinned recipe (LLVM 19.1.7). The feature base always uses the reviewed prebuilt units. Every build is followed by an independent audit: container roundtrip, full rebuild from the stock input, stock-prefix window audit and identity checks.

WAV requirements: RIFF WAV, uncompressed 16-bit LE PCM, 48 kHz stereo, longer than 0 and at most 1.5 s (PCM ≤ 288,000 bytes), container ≤ 524,288 bytes, ≤ 512 chunks, printable-ASCII filename ≤ 111 characters including `.wav`, placed in `CUSTOM_SOUND` at the card root (max 20 files). Playback restarts each frame and can be interrupted; C15 leads with up to 50 ms of audio, other Cxx up to 40 ms, and the remainder plays once after a burst stops. Up to 20 distinct contents are cached per power-on (288,000 bytes reserved each); read differences, copy-verification failures or audio BUSY never publish PCM or consume a permanent cache slot. Re-select after replacing a same-named WAV.

Validation scope: the full 16-selection offline matrix, 27+13 ARM regressions and source/prebuilt parity pass locally. **Camera verification: the four-group-plus-shutter-sound package passed full on-camera verification with every feature enabled.** The tool never writes a card or operates a camera; see `NOTICE.md` for the experimental-firmware risks.
