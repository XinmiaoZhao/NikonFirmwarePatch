# 已知问题与功能限制 / Known issues and feature limits

适用于基于官方 Nikon Z8 C 3.11 的 v0.3.0 四功能版本。以下列出当前实现中已确认的问题和明确的功能限制；操作方法见各功能指南，验证记录见[当前版本验证](validation.md)。

## Windows 工具包修订

原 v0.3.0 在 Windows 上构建预拍摄、像素位移或开放门时，可能报 `Compiled patch source does not match the reviewed recipe`，而 `--check` 仍通过。v0.3.0-r1 修复了路径分隔符比较。请重新解压完整修订工具包到新目录，使用原厂 C 3.11 输入和一个尚不存在的输出目录；无需修改配方或关闭哈希检查。`--check` 检查输入兼容性，不代表完整构建已验证。详见 [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12)。

## RAW 连拍与预拍摄

- **仅支持 FX/L、C15/C30、HE／HE★。** 选择“无损压缩”时，此路径仍记录 HE。DX RAW、C60/C120 RAW、HLG/HEIF 和副卡独立 JPEG 尺寸计划不受支持。
- **DX 下画质显示与文件不一致。** 界面可以显示 RAW，实际仍写原厂 JPEG；JPEG 品质由“画质（HSFC）”决定，QUAL 和 i 菜单修改的普通画质不控制该输出。RAW／RAW+JPEG 的剩余张数会多算没有写出的 NEF，HE★ 的可用缓冲帧数也会被低估。这些行为已通过源码和原指令核对；使用 RAW 预拍请选 FX/L。
- **近满卡处理仍按 JPEG 计划。** 剩余张数已计入 NEF 及普通 JPEG 品质，但拍摄准入、提交预留、自动溢出换卡和 r／缓冲显示仍沿用原厂高速 JPEG 计划；排队等待写入的 NEF 没有全部预留空间。显示张数不能作为可写 NEF 数量的保证。数据库拒绝登记时会尝试 JPEG 回退，包括 RAW-only 设置；每张目标卡都应留足空间。
- **RAW 写卡积压会缩短连拍和预拍窗口。** RAW 帧缓冲保留到 NEF 写完，比原厂 JPEG 更早积压；连续短间隔拍摄时，可用帧数会减少。HE★ 比 HE 占用更多缓冲与卡空间。
- **停止文件会持续阻止额外 NEF 写入。** NEF 写入失败、写后找不到文件或超出默认 1.5 秒处理预算时，会尝试创建 `Z8PRESTP.BIN`。该文件存在期间，后续帧尝试回退 JPEG；重启不会清除它，主卡的停止状态还会影响副卡共享的 RAW 缓冲。处理方法见[停止文件指南](stop-file.md)。
- **部分可选元数据缺失。** 生成的 NEF 缺少部分原厂镜头校正块、灰度子图及 XMP 校正数据。

详细设置与双卡规则见 [RAW／预拍摄指南](raw-precapture.md#简体中文)。

## ProRes

- **部分显示仍沿用原厂 HQ。** 取景图标没有区分 HQ／Standard／LT／Proxy，部分菜单图标和帮助文字仍写 HQ。所选档位以画质菜单为准，实际录像可用 MOV 编码标识确认。
- **重设视频拍摄菜单不会重设新增档位。** 重设后如需改变档位，应在画质菜单中重新选择。
- 新增档位沿用原 ProRes 422 路径的画幅和帧率范围；不增加 ProRes RAW 或 3:2。

档位、菜单库和文件编码标识见 [ProRes 指南](prores.md)。

## 像素位移合成

- **当前仅支持每组在新建文件夹中拍摄，文件编号从 `0001` 开始。** 拍摄前在起始存储文件夹设置中同时勾选“新建文件夹”和“重置文件编号”。
- **输入限完整的 4／8／16／32 张 FX/L、8256×5504、14-bit 无损压缩 NEF 组。** HE／HE★、DX、残缺或重复组不能合成，RAW 预拍生成的 HE／HE★ NEF 也不适用。
- **机内缩略图只显示首帧。** 合成输出为 NEFX，需在电脑上查看；机内回放不能用来查看最终合成结果。
- 4／8 张组输出 8256×5504，16／32 张组输出 16512×11008。重复合成另起文件名，不覆盖原片或旧输出。

组选择、输出与取消操作见[像素位移指南](pixelshift.md)。

## 开放门与 N-RAW 四档

- **开放门限 FX 3:2 N-RAW 8.3K 30／25／24p**，有效图像 8256×5504。不提供 50／60p 开放门，也不把 ProRes／H.265 改成 3:2。开放门与四档 N-RAW 是同一个构建选项。
- **两档画质的软件会合并档位名称。** 为兼容这类读取器，Fine 映射为 High、Basic 映射为 Normal；软件显示的两档名称不能用于区分实际的四档编码。
- **低码率档位有细节损失。** Basic 使用 1.0 bit/像素预算，实拍已观察到高频纹理减弱。开放门 High 为 2.5 bit/像素，低于普通 8.3K 30／25／24p High 的 3.0 bit/像素；不能把两者视为相同的单位像素压缩预算。

模式选择与各档码率预算见[开放门／N-RAW 指南](opengate-nraw.md)。

## English

### Windows toolkit revision

The original v0.3.0 can reject pre-capture, pixel-shift or open-gate builds on Windows with `Compiled patch source does not match the reviewed recipe`, even when `--check` passes. v0.3.0-r1 fixes path-separator comparison. Extract the complete revised toolkit into a fresh directory and build from official C 3.11 into a new output directory. Keep the recipes and hash checks intact. `--check` validates input compatibility; it is not a complete build check. See [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12).

Applies to the current four-feature version, built from official Nikon Z8 C 3.11.

### RAW capture and pre-capture

- Supports FX/L, C15/C30 and HE/HE★ only. Selecting lossless still records HE on this path. DX RAW, C60/C120 RAW, HLG/HEIF and separately sized secondary JPEG plans are unsupported.
- In DX, the UI can show RAW while the camera writes stock JPEG. The HSFC quality setting controls that JPEG; ordinary quality changes through QUAL or the i menu do not. RAW counts include an NEF that is not written, and HE★ understates available buffer frames. These behaviors are established by source and instruction checks. Use FX/L for RAW pre-capture.
- Admission, reservations, overflow switching and r/buffer display retain the stock JPEG plan, although the remaining-shot estimate includes NEF and ordinary JPEG quality. Queued NEFs are not all reserved. Database refusal attempts JPEG fallback even for RAW-only. Keep space on each destination card; the displayed count is not a guaranteed NEF capacity.
- RAW buffers remain occupied until NEF writing finishes. Write backlog reduces available burst/history frames; HE★ uses more memory and card space than HE.
- Failed, missing or over-budget NEF writes attempt to create `Z8PRESTP.BIN`. Its presence blocks further extra NEFs and prompts JPEG fallback; restarting does not clear it. A primary-card stop also affects the shared secondary RAW buffer. See the [stop-file guide](stop-file.md#english-summary).
- Some optional lens-correction blocks, a grayscale subimage and XMP correction metadata are absent.

### ProRes

- Live-view icons do not distinguish all four grades; some menu icons/help still say HQ. Check the quality menu and the recorded MOV codec.
- Resetting the movie menu does not reset the added grade; select the desired grade again.
- Dimensions and frame rates remain those of stock ProRes 422. ProRes RAW and 3:2 are not added.

### Pixel shift

- **Currently, each group must be captured in a new folder with file numbering starting at `0001`.** Before shooting, enable both **New folder** and **Reset file numbering** under **Starting storage folder**.
- Requires complete 4/8/16/32-frame FX/L 8256×5504 14-bit lossless NEF groups. HE/HE★, DX, incomplete and duplicate groups are unsupported.
- Thumbnails show the first frame. View the merged NEFX on a computer; camera playback does not display the merged result.
- Output is 8256×5504 for 4/8 frames and 16512×11008 for 16/32. Repeated merges use new filenames without overwriting inputs or earlier outputs.

### Open gate and N-RAW tiers

- Open gate is limited to FX 3:2 N-RAW 8.3K 30/25/24p, with 8256×5504 active pixels. It adds neither 50/60p open gate nor ProRes/H.265 3:2. Open gate and the four N-RAW tiers form one build option.
- Compatibility metadata maps Fine to High and Basic to Normal for two-tier readers. Those labels cannot distinguish all four actual encoding grades.
- Basic uses a 1.0-bit/pixel budget, with reduced fine texture observed in camera samples. Open-gate High uses 2.5 bits/pixel versus 3.0 for ordinary 8.3K 30/25/24p High.
