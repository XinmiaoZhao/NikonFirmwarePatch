# RAW 连拍与预拍摄 / RAW capture and pre-capture

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features photo-tools` 让 C15／C30 的预拍历史帧和正式帧按普通“画质”设置输出 RAW／RAW+JPEG／JPEG，使用“RAW 记录”选择 HE／HE★。QUAL／f2、i 菜单和取景画质标识使用相同的普通画质设置。

### 支持范围

支持**照片模式、FX/DX、全尺寸 L、C15／C30、HE 或 HE★**。JPEG 支持精细／标准／基本及 ★。不支持真正无损 RAW、C60/C120 RAW、HLG/HEIF 或副卡独立 JPEG 尺寸计划。

缓存完整时，预拍 0.3／1 秒在 C15 最多保存 5／15 帧，在 C30 最多保存 9／30 帧。30 帧是历史窗口上限，不是整次连拍上限；关闭预拍时，正式帧仍使用所选格式。

### 使用步骤

1. 选择 FX/L 或 DX/L 和 C15 或 C30。
2. 在普通“画质”中选择文件类型、JPEG 档位和 ★；在“RAW 记录”中选择 HE／HE★。
3. 设置预拍时长、后拍上限、主卡槽及副卡槽功能。无需 `Z8PRE.CFG`，旧配置文件不再读取。
4. 半按填充预拍缓存，再全按拍摄。等写入结束后再更换卡或调整文件格式。

### 输出与显示

NEF 使用原厂照片数据库与写入器，写完可直接回放，FX 输出通常带 **8256×5504** 整幅预览。RAW+JPEG Basic（不带 ★）复用主 JPEG 作为整幅预览，其余配对档位单独编码预览；独立 JPEG 使用所选品质。公开构建不附加诊断尾标。

主卡槽和副卡槽功能在每帧提交时记下，已排队帧继续使用提交时的设置：

| 副卡槽功能 | RAW | RAW+JPEG |
|---|---|---|
| 额外空间／单一目标卡 | 原厂选择的目标卡写 NEF | 同一目标卡写 NEF＋JPEG |
| 备份 | 两卡各写 NEF | 两卡各写 NEF＋JPEG |
| RAW 主卡－JPEG 副卡 | 两卡各写 NEF | 主卡 NEF，副卡 JPEG |
| JPEG 主卡－JPEG 副卡（单 JPEG 帧计划） | 两卡各写 NEF | 两卡各写 NEF＋JPEG |

剩余张数计入 NEF 大小，并随文件类型、RAW 压缩、JPEG 档位和 ★ 刷新。JPEG-only 保持原厂文件路径。

### 已知问题

- 选择“无损压缩”记录 HE★，并非无损。实拍 SD 文件确认 DX 预拍使用 5392×3592 有效区，DX／FX 菜单选择无损时均写出 HE★。
- 实际拍摄准入、空间预留、自动溢出和 r／缓冲显示仍按高速 JPEG 计划。数据库拒绝登记或锁失败时尝试 JPEG 回退，包括 RAW-only；该拒绝不创建停止文件。
- RAW 帧保留到 NEF 写完，写卡积压会减少连拍／预拍可用帧数；HE★ 占用更多。每张目标卡应保留充足空间。
- 实际 NEF 写入失败、写后找不到文件或达到默认 1.5 秒预算时，仍会尝试创建 `Z8PRESTP.BIN`。重启不清除停止文件；保留两卡文件并按[停止文件指南](stop-file.md)处理。停止额外 RAW 拍摄可选择 JPEG-only 或退出 C15／C30。
- NEF 头按原厂 NEF 标签表写出：六个 SubIFD、镜头校正等 NEFInfo 块（0x05–0x07、0x0C、0x10–0x13）以及 MakerNote 0x0046／0x008C／0x00A4，不再带入仅属于 JPEG 的标签。SubIFD3–5 是空占位，仍没有原厂的 384×256 灰度子图；XMP 校正数据和 MakerNote 0x0093 仍缺失；使用自定义色调曲线的优化校准时不写 ContrastCurve。这项改动（[问题 #23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)、[#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27) 的机内“NEF（RAW）处理”与元数据差异）已在 Z8 机身上测试。

## English

### Overview

`--features photo-tools` makes C15/C30 history and post-release frames follow ordinary Image quality: RAW/RAW+JPEG/JPEG. RAW recording selects HE/HE★. QUAL/f2, the i menu and shooting-screen indicators use the same ordinary quality setting.

### Supported modes

Supports **photo mode, FX/DX, full-size L, C15/C30 and HE or HE★**. JPEG supports Fine/Normal/Basic with or without ★. True lossless RAW, C60/C120 RAW, HLG/HEIF and separately sized secondary JPEG plans are unsupported.

With a full buffer, 0.3/1-second history saves up to 5/15 frames at C15 or 9/30 at C30. The 30-frame ceiling applies to history, not the entire burst. With pre-capture off, current frames still use the selected format.

### Steps

1. Select FX/L or DX/L and C15 or C30.
2. Select file type, JPEG grade and ★ in ordinary Image quality; select HE/HE★ in RAW recording.
3. Set history duration, post-release limit, primary slot and secondary-slot role. No `Z8PRE.CFG` is required; old configuration files are ignored.
4. Half-press to fill history, then fully press to shoot. Let writing finish before changing cards or file format.

### Files and display

NEFs use the stock photo database/writer and support direct playback. FX output normally contains an **8256×5504** preview. RAW+JPEG Basic without ★ reuses its main JPEG for that preview; other paired grades encode a separate preview. Standalone JPEGs use the selected quality. Public builds do not append diagnostic footers.

Each submitted frame stores the primary slot and secondary role, so queued frames retain those settings:

| Secondary-slot role | RAW | RAW+JPEG |
|---|---|---|
| Overflow / one destination | NEF on the stock-selected destination | NEF + JPEG on that destination |
| Backup | NEF on each card | NEF + JPEG on each card |
| RAW primary – JPEG secondary | NEF on each card | NEF on primary, JPEG on secondary |
| JPEG primary – JPEG secondary (single-JPEG frame plan) | NEF on each card | NEF + JPEG on each card |

Remaining counts include NEF size and refresh with file type, RAW compression, JPEG grade and ★. JPEG-only retains the stock file path.

### Known issues

- Selecting lossless records HE★, not lossless. SD recordings confirm a 5392×3592 active DX area and HE★ files after lossless selection in DX and FX.
- Admission, reservations, overflow switching and r/buffer display retain the stock high-speed JPEG plan. Database/lock refusal attempts JPEG fallback, even for RAW-only; that refusal does not create a stop marker.
- RAW buffers remain occupied until NEF writing finishes. Backlog reduces burst/history capacity; HE★ uses more space. Leave ample space on each destination card.
- Failed/missing NEF writes or reaching the default 1.5-second budget still attempt to create `Z8PRESTP.BIN`. Restarting does not clear it. Preserve both cards and follow the [stop-file guide](stop-file.md#english-summary). Select JPEG-only or leave C15/C30 to stop extra RAW capture.
- NEF headers follow the stock NEF tag lists: six SubIFDs, the lens-correction and other NEFInfo blocks (0x05–0x07, 0x0C, 0x10–0x13) and MakerNote 0x0046/0x008C/0x00A4, without the JPEG-only tags. SubIFD3–5 are empty placeholders, so the stock 384×256 grayscale subimage is still absent, as are XMP correction metadata and MakerNote 0x0093. A Picture Control with a custom tone curve omits ContrastCurve. This change, made for the in-camera NEF (RAW) processing failure and metadata differences in [issue #23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23) and [#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27), has been tested on a Z8.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
