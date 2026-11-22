> 当前四组版本 v0.5.1 的机身测试范围见[验证记录](validation.md)。本文按功能列出实际限制。

# 已知问题与功能限制 / Known issues and feature limits

适用于基于官方 Nikon Z8 C 3.11 的当前四组版本 v0.5.1；历史公开版本限制保留具体版本号。以下列出当前实现中已确认的问题和明确的功能限制；操作方法见各功能指南，验证记录见[当前版本验证](validation.md)。

## Windows 工具包修订

原 v0.3.0 在 Windows 上构建预拍摄、像素位移或开放门时，可能报 `Compiled patch source does not match the reviewed recipe`，而 `--check` 仍通过。v0.3.0-r1 修复了路径分隔符比较。请重新解压完整修订工具包到新目录，使用原厂 C 3.11 输入和一个尚不存在的输出目录；无需修改配方或关闭哈希检查。`--check` 检查输入兼容性，不代表完整构建已验证。详见 [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12)。

## RAW 连拍与预拍摄

- **预拍支持 FX/DX、L、C15/C30、HE／HE★，不支持无损压缩。** C15/C30 中无损压缩选项禁用，普通拍照保存的无损按高效率★记录，回到普通拍照即恢复。C60/C120 RAW、HLG/HEIF 和副卡独立 JPEG 尺寸计划不支持。
- **近满卡处理仍按 JPEG 计划。** 剩余张数已计入 NEF 及普通 JPEG 品质，但拍摄准入、提交预留、自动溢出换卡和 r／缓冲显示仍沿用原厂高速 JPEG 计划；排队等待写入的 NEF 没有全部预留空间。显示张数不能作为可写 NEF 数量的保证。数据库拒绝登记时会尝试 JPEG 回退，包括 RAW-only 设置；每张目标卡都应留足空间。
- **RAW 写卡积压会缩短连拍和预拍窗口。** RAW 帧缓冲保留到 NEF 写完，比原厂 JPEG 更早积压；连续短间隔拍摄时，可用帧数会减少。HE★ 比 HE 占用更多缓冲与卡空间。贡献者在 C30 FX 仅 RAW 下测得写卡约每秒 5–6 张，缓冲在 HE★ 约 66 张、HE 约 134 张后写满（[PR #50](https://github.com/XinmiaoZhao/NikonFirmwarePatch/pull/50)）。
- **停止文件会持续阻止额外 NEF 写入。** NEF 写入失败、写后找不到文件或超出默认 1.5 秒处理预算时，会尝试创建 `Z8PRESTP.BIN`。该文件存在期间，后续帧尝试回退 JPEG；重启不会清除它，主卡的停止状态还会影响副卡共享的 RAW 缓冲。处理方法见[停止文件指南](stop-file.md)。
- **部分元数据缺失。** 生成的 NEF 缺少部分原厂镜头校正块（畸变与暗角）、灰度子图及 XMP 校正数据，Lightroom 等软件不能自动套用机内镜头校正（[#23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)）。
- **机内不能润饰预拍 NEF。** “润饰 › NEF (RAW) 处理”会提示无法编辑：生成的 NEF 头只有 3 个子 IFD，相机的读取器要求 6 个（[#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27)）。
- **系列回放显示异常。** 预拍连拍在回放中不能按系列正常显示；仅 RAW 时，元数据里的连拍起始文件类型写成 JPG（[#23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)）。
- **预拍沿用自己的格式与画幅。** 同时安装照片工具时，C15／C30 仍按 FX 或 DX 写 NEF／JPEG。C15 至 C120 中压缩照片使用 JPEG，HEIF 与新增画幅禁用。

详细设置与双卡规则见 [RAW／预拍摄指南](raw-precapture.md#简体中文)。

## Log 与反挤压

- **剪辑软件可能误识别 Log。** Resolve 把 S-Log3／Log3G10 片段识别为 Rec709 (Scene)，需要在媒体池手动指定输入色域与曲线，见 [Log 后期流程](log-colour.md)。
- **S-Log3 与 Log3G10 的色彩为拟合结果。** 两种 Log 的录像矩阵按同场景 N-RAW 的解码结果拟合，部分场景或暗光下可能出现偏色，见[色彩报告](log-colour-report.md)。
- S-Log3 保留原厂的非负截断；高饱和青蓝、暗部及不同曝光的表现见[色彩报告](log-colour-report.md)。
- Log3G10 录像不含 RED 解码 N-RAW 时引入的 F 映射，需要时在后期使用 [F LUT](../luts/README.md)。
- 反挤压只改变显示几何，录像保持原始像素比例。影片回放使用当前倍率，回放其他镜头拍摄的片段时请切换到对应倍率或关闭。

## ProRes

- **重设视频拍摄菜单不会重设新增档位。** 重设后如需改变档位，应在画质菜单中重新选择。
- 新增档位沿用原 ProRes 422 路径的画幅和帧率范围；不增加 ProRes RAW 或 3:2。

档位、菜单库和文件编码标识见 [ProRes 指南](prores.md)。

## 像素位移合成

- **v0.3.0／v0.3.0-r1 只识别起始文件编号为 `0001`、`2049`、`4097`、`6145`、`8193` 的组**，其他组列表为空（[issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)）。v0.4.0 起已修复；机身上从 4660 和 4664 起拍的 4 张与 16 张组均合成成功。
- **列表不显示被拒帧的数量或原因。** 已识别为像素位移、但因格式或完整性检查被拒的帧不会出现在列表中；空列表不一定表示卡上没有像素位移照片。若相机拍出的完整组仍不出现，请保留原片并报告。
- **输入限完整的 4／8／16／32 张 FX/L、8256×5504、14-bit 无损压缩 NEF 组。** HE／HE★、DX、残缺或重复组不能合成，RAW 预拍生成的 HE／HE★ NEF 也不适用。
- **机内缩略图只显示首帧。** 合成输出为 NEFX，需在电脑上查看；机内回放不能用来查看最终合成结果。
- 4／8 张组输出 8256×5504，16／32 张组输出 16512×11008。重复合成另起文件名，不覆盖原片或旧输出。

组选择、输出与取消操作见[像素位移指南](pixelshift.md)。

## SDR HEIF

- **选择 SDR HEIF 后，部分选项会变化。** 与原厂 HLG 一样，HDR 叠加和多重曝光禁用，照片菜单的延时视频固定为 H.265 10 位。改回 JPEG 即恢复。
- **C15 至 C120 不能拍 HEIF。** 进入这些档位后，压缩照片临时改用 JPEG，HEIF 禁用；回到普通释放模式会恢复当前菜单库保存的偏好。
- **HEIF 兼容性因软件而异。** 已在 macOS 预览、iPhone 照片、Windows 11 照片和小米 13 Ultra 相册中确认能打开、颜色正确；其他软件、设备和系统版本不保证能正常识别。各平台的适配做法见 [SDR HEIF 指南](sdr-heif.md#兼容性)。

设置与兼容软件见 [SDR HEIF 指南](sdr-heif.md)。

## 照片裁切比例

- **刷入其他固件之前，先把图像区域改回 FX。** 原厂固件和不含照片工具的包没有新画幅的参数，取景可能反复重试或保持黑屏。
- **高速画面捕捉中不能用新增画幅。** C15/C30 只能选 FX 和 DX；C60/C120 与原厂一样不能选择图像区域。
- **软件显示的裁切名称可能不对。** 实际像素尺寸正确，但元数据借用了原厂已有的裁切代码：exiftool 把 4:3 显示为“5:4 Crop”，2.39:1 显示为“3:2 Crop”，65:24 显示为“2.8x Movie Crop”。

画幅尺寸见[照片裁切指南](photo-crop.md)。

## N-RAW 3:2 与 N-RAW 四档

- **3:2 只限 N-RAW 文件类型。** “N-RAW 12位 3:2(NEV)”提供 8.3K 30／25／24p（8256×5504）和 4.1K 120p 至 24p（4128×2752）。8.3K 3:2 最高 30p，ProRes／H.265 仍为 16:9。i 菜单没有文件类型项，需在视频拍摄菜单切换。
- **离开 3:2 后对焦点可能停在多出的一行。** 按一次多重选择器即可回到 16:9 网格。
- **3:2 画面最上、最下各一行对焦点可能不会启用。** N-RAW 3:2 下，自动区域 AF 的合焦绿框可能最多只亮到从上数第二行和从下数第二行；对象跟踪 AF 把对焦框放在最外一行后按 OK，框可能向内移动一行。
- **两档画质的软件会合并档位名称。** 为兼容这类读取器，Fine 映射为 High、Basic 映射为 Normal；软件显示的两档名称不能用于区分实际的四档编码。
- **低码率档位有细节损失。** Basic 使用 1.0 bit/像素预算，实拍已观察到高频纹理减弱。8.3K 3:2 High 为 2.5 bit/像素，低于普通 8.3K 30／25／24p High 的 3.0 bit/像素；不能把两者视为相同的单位像素压缩预算。

模式选择与各档码率预算见 [N-RAW 3:2 指南](opengate-nraw.md)。

## English

### Windows toolkit revision

The original v0.3.0 can reject pre-capture, pixel-shift or open-gate builds on Windows with `Compiled patch source does not match the reviewed recipe`, even when `--check` passes. v0.3.0-r1 fixes path-separator comparison. Extract the complete revised toolkit into a fresh directory and build from official C 3.11 into a new output directory. Keep the recipes and hash checks intact. `--check` validates input compatibility; it is not a complete build check. See [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12).

Applies to the current four-group release, v0.5.1, built from official Nikon Z8 C 3.11. Historical limitations name their affected releases.

### RAW capture and pre-capture

- Pre-capture supports FX/DX, L, C15/C30 and HE/HE★, not lossless compression. C15/C30 disable the lossless option; a lossless setting saved for ordinary shooting is recorded as HE★ there and restored afterwards. C60/C120 RAW, HLG/HEIF and separately sized secondary JPEG plans are not supported.
- Admission, reservations, overflow switching and r/buffer display retain the stock JPEG plan, although the remaining-shot estimate includes NEF and ordinary JPEG quality. Queued NEFs are not all reserved. Database refusal attempts JPEG fallback even for RAW-only. Keep space on each destination card; the displayed count is not a guaranteed NEF capacity.
- RAW buffers remain occupied until NEF writing finishes. Write backlog reduces available burst/history frames; HE★ uses more memory and card space than HE. A contributor measured about 5–6 NEFs written per second at C30 FX RAW only, with the buffer full after about 66 (HE★) or 134 (HE) frames ([PR #50](https://github.com/XinmiaoZhao/NikonFirmwarePatch/pull/50)).
- Failed, missing or over-budget NEF writes attempt to create `Z8PRESTP.BIN`. Its presence blocks further extra NEFs and prompts JPEG fallback; restarting does not clear it. A primary-card stop also affects the shared secondary RAW buffer. See the [stop-file guide](stop-file.md#english-summary).
- Some lens-correction blocks (distortion and vignetting), a grayscale subimage and XMP correction metadata are absent, so applications such as Lightroom cannot apply the in-camera lens corrections ([#23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)).
- Retouch › NEF (RAW) processing refuses pre-capture NEFs: their header has three sub-IFDs and the camera's reader requires six ([#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27)).
- Series playback does not group pre-capture bursts correctly; with RAW only, the burst-start file type in the metadata reads JPG ([#23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)).
- With the still-photo tools installed, C15/C30 still writes NEF/JPEG in FX or DX. C15 through C120 use JPEG for compressed photos and disable HEIF and the added image areas.

### Log and desqueeze

- Editing software can misread Log. Resolve identifies S-Log3/Log3G10 clips as Rec709 (Scene); assign the input gamut and curve in the media pool. See [Log settings and grading](log-colour.md#english).
- S-Log3 and Log3G10 colour is fitted: their recording matrices are fitted to the decoded same-scene N-RAW, so some scenes or low light can show a colour cast. See the [colour report](log-colour-report.en.md).
- S-Log3 keeps the stock non-negative clamp. See the [colour report](log-colour-report.en.md) for saturated cyan-blue, shadows and other exposures.
- Log3G10 recordings omit the F mapping that RED applies when decoding N-RAW; apply the [F LUT](../luts/README.md) in post if needed.
- Desqueeze changes the display geometry only; recordings keep their pixel aspect. Playback uses the current factor, so switch it or turn it off when reviewing clips from other lenses.

### ProRes

- Resetting the movie menu does not reset the added grade; select the desired grade again.
- Dimensions and frame rates remain those of stock ProRes 422. ProRes RAW and 3:2 are not added.

### Pixel shift

- **v0.3.0/v0.3.0-r1 recognize only groups whose first file number is `0001`, `2049`, `4097`, `6145` or `8193`**; other groups give an empty list ([issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)). v0.4.0 fixed group recognition. On camera, 4- and 16-frame groups starting at 4660 and 4664 merged successfully.
- The list does not show how many frames were refused or why. Frames recognized as pixel shift but refused by the format or completeness checks are omitted, so an empty list does not prove that the card has no pixel-shift shots. If a complete camera group is still missing, keep the originals and report it.
- Requires complete 4/8/16/32-frame FX/L 8256×5504 14-bit lossless NEF groups. HE/HE★, DX, incomplete and duplicate groups are unsupported.
- Thumbnails show the first frame. View the merged NEFX on a computer; camera playback does not display the merged result.
- Output is 8256×5504 for 4/8 frames and 16512×11008 for 16/32. Repeated merges use new filenames without overwriting inputs or earlier outputs.

### SDR HEIF

- With SDR HEIF selected, HDR overlay and multiple exposure are disabled and the photo menu's time-lapse movie is fixed to H.265 10-bit, as with stock HLG. Selecting JPEG restores them.
- C15 through C120 cannot shoot HEIF. These modes use JPEG for compressed photos and disable HEIF; an ordinary release mode restores the active bank’s saved preference.
- HEIF support varies by application. The files are confirmed to open with correct colour in macOS Preview, iPhone Photos, Windows 11 Photos and the Xiaomi 13 Ultra gallery; other applications, devices and system versions may not read them correctly. See the [SDR HEIF guide](sdr-heif.md#compatibility) for how each platform is handled.

See the [SDR HEIF guide](sdr-heif.md).

### Still crop ratios

- Return the image area to FX before installing other firmware. Stock firmware and packages without the still-photo tools lack the parameters for the new areas; live view can keep retrying or stay black.
- The added areas are not available in high-speed frame capture. C15/C30 offer only FX and DX; at C60/C120 Choose image area is unavailable, as on the stock camera.
- Pixel dimensions are correct, but the metadata reuses existing stock crop codes: exiftool shows 4:3 as "5:4 Crop", 2.39:1 as "3:2 Crop" and 65:24 as "2.8x Movie Crop".

See the [still crop guide](photo-crop.md).

### N-RAW 3:2 and N-RAW tiers

- 3:2 is limited to the N-RAW 12-bit 3:2 (NEV) file type: 8.3K 30/25/24p (8256×5504) and 4.1K 120p to 24p (4128×2752). 8.3K 3:2 stops at 30p, and ProRes/H.265 stay 16:9. The i menu has no file type item; switch in the video recording menu.
- After leaving 3:2, the focus point can remain on an extra row; press the multi selector once to return to the 16:9 grid.
- In N-RAW 3:2, auto-area AF and subject-tracking AF may not use the top and bottom rows of focus points: auto-area AF may light its in-focus boxes only as far as the second row from the top and bottom, and a subject-tracking AF frame placed on the outermost row may move one row inward when OK is pressed.
- Compatibility metadata maps Fine to High and Basic to Normal for two-tier readers. Those labels cannot distinguish all four actual encoding grades.
- Basic uses a 1.0-bit/pixel budget, with reduced fine texture observed in camera samples. 8.3K 3:2 High uses 2.5 bits/pixel versus 3.0 for ordinary 8.3K 30/25/24p High.
