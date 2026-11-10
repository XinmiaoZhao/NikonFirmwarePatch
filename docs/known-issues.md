> 当前四组版本 v0.4.0 的机身测试范围见[验证记录](validation.md)。本文按功能列出实际限制。

# 已知问题与功能限制 / Known issues and feature limits

适用于基于官方 Nikon Z8 C 3.11 的当前四组版本 v0.4.0；历史公开版本限制保留具体版本号。以下列出当前实现中已确认的问题和明确的功能限制；操作方法见各功能指南，验证记录见[当前版本验证](validation.md)。

## Windows 工具包修订

原 v0.3.0 在 Windows 上构建预拍摄、像素位移或开放门时，可能报 `Compiled patch source does not match the reviewed recipe`，而 `--check` 仍通过。v0.3.0-r1 修复了路径分隔符比较。请重新解压完整修订工具包到新目录，使用原厂 C 3.11 输入和一个尚不存在的输出目录；无需修改配方或关闭哈希检查。`--check` 检查输入兼容性，不代表完整构建已验证。详见 [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12)。

## RAW 连拍与预拍摄

- **预拍支持 FX/DX、L、C15/C30、HE／HE★。** 选择“无损压缩”回退 HE★，不是无损。C60/C120 RAW、HLG/HEIF 和副卡独立 JPEG 尺寸计划仍不支持。
- 组合包实拍确认 DX 与 FX 选择无损后写出 HE★；DX C30、仅 RAW、直接选择 HE★ 的组合仍待补测。
- **近满卡处理仍按 JPEG 计划。** 剩余张数已计入 NEF 及普通 JPEG 品质，但拍摄准入、提交预留、自动溢出换卡和 r／缓冲显示仍沿用原厂高速 JPEG 计划；排队等待写入的 NEF 没有全部预留空间。显示张数不能作为可写 NEF 数量的保证。数据库拒绝登记时会尝试 JPEG 回退，包括 RAW-only 设置；每张目标卡都应留足空间。
- **RAW 写卡积压会缩短连拍和预拍窗口。** RAW 帧缓冲保留到 NEF 写完，比原厂 JPEG 更早积压；连续短间隔拍摄时，可用帧数会减少。HE★ 比 HE 占用更多缓冲与卡空间。
- **停止文件会持续阻止额外 NEF 写入。** NEF 写入失败、写后找不到文件或超出默认 1.5 秒处理预算时，会尝试创建 `Z8PRESTP.BIN`。该文件存在期间，后续帧尝试回退 JPEG；重启不会清除它，主卡的停止状态还会影响副卡共享的 RAW 缓冲。处理方法见[停止文件指南](stop-file.md)。
- **部分可选元数据缺失。** 生成的 NEF 缺少部分原厂镜头校正块、灰度子图及 XMP 校正数据。

详细设置与双卡规则见 [RAW／预拍摄指南](raw-precapture.md#简体中文)。

## Log 与反挤压

- Log 回放名称与辅助按片段选择。新录和旧录 N-RAW 已上机确认；跨菜单库和断电重开后的交互仍值得补测。
- 当前默认 S-Log3 保留非负截断；高饱和青蓝、暗部及不同曝光的表现继续按[色彩报告](log-colour-report.md)更新。
- 反挤压只改变显示几何，录像保持原始像素比例；影片回放使用当前倍率。
- 机身试用未报告反挤压绿点异常；全高画幅边缘覆盖、小尺寸取景器和主体检测框仍缺逐项实测。

## ProRes

- **HQ 星标不能区分其余三档。** 本版用星标区分 HQ 与 422／LT／Proxy，部分帮助文字仍写 HQ。所选档位以画质菜单为准，实际录像可用 MOV 编码标识确认。
- **重设视频拍摄菜单不会重设新增档位。** 重设后如需改变档位，应在画质菜单中重新选择。
- 新增档位沿用原 ProRes 422 路径的画幅和帧率范围；不增加 ProRes RAW 或 3:2。

档位、菜单库和文件编码标识见 [ProRes 指南](prores.md)。

## 像素位移合成

- **v0.3.0／v0.3.0-r1 只识别起始文件编号为 `0001`、`2049`、`4097`、`6145`、`8193` 的组**，其他组列表为空（[issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)）。本版已修复；机身上从 4660 和 4664 起拍的 4 张与 16 张组均合成成功。
- **列表不显示被拒帧的数量或原因。** 已识别为像素位移、但因格式或完整性检查被拒的帧不会出现在列表中；空列表不一定表示卡上没有像素位移照片。若相机拍出的完整组仍不出现，请保留原片并报告。
- **输入限完整的 4／8／16／32 张 FX/L、8256×5504、14-bit 无损压缩 NEF 组。** HE／HE★、DX、残缺或重复组不能合成，RAW 预拍生成的 HE／HE★ NEF 也不适用。
- **机内缩略图只显示首帧。** 合成输出为 NEFX，需在电脑上查看；机内回放不能用来查看最终合成结果。
- 4／8 张组输出 8256×5504，16／32 张组输出 16512×11008。重复合成另起文件名，不覆盖原片或旧输出。

组选择、输出与取消操作见[像素位移指南](pixelshift.md)。

## 开放门与 N-RAW 四档

- **开放门限 FX 3:2 N-RAW 8.3K 30／25／24p**，有效图像 8256×5504。不提供 50／60p 开放门，也不把 ProRes／H.265 改成 3:2。开放门与四档 N-RAW 是同一个构建选项。
- **两档画质的软件会合并档位名称。** 为兼容这类读取器，Fine 映射为 High、Basic 映射为 Normal；软件显示的两档名称不能用于区分实际的四档编码。
- **低码率档位有细节损失。** Basic 使用 1.0 bit/像素预算，实拍已观察到高频纹理减弱。开放门 High 为 2.5 bit/像素，低于普通 8.3K 30／25／24p High 的 3.0 bit/像素；不能把两者视为相同的单位像素压缩预算。

模式选择与各档码率预算见[开放门／N-RAW 指南](opengate-nraw.md)。

## 记录视频方向（开发组）

以下适用于开发分支的第五组 `video-orientation`，尚未随 v0.4.0 发布；功能说明见[记录视频方向指南](video-orientation.md)。

- **断电后回到默认“开”。** 取值按视频拍摄菜单库 A–D 分别记忆，会话内切换菜单库时随库切换，手动关闭在本次开机期间保持；断电重启后各库重新初始化为“开”。该字节与已发布的 H.265 档位字节同属一个相机设置记录的空位，断电语义一致。菜单项的保存、菜单库切换、断电重启与菜单重设行为均已实机验证，与已发布的 H.265 档位功能完全一致；唯一开问题：功能开启时录制的视频在电脑上播放不旋转，原因排查中。
- **双格式同时录制时第二个文件不带方向标记。** 一次性锁存只标记同一次竖拍录制中最先收尾的文件；双格式同时记录（如 N-RAW/ProRes RAW 主文件 + MP4 第二文件）中后收尾的文件保持原厂恒等矩阵、不写入旋转标记。单格式录制不受影响；在代码修复发布前保持此现状。实机取证见验收清单 M9 腿。
- **N-RAW 第三方工具兼容未知。** 旋转元数据的写入路径覆盖相机全部录像格式（含 N-RAW），但第三方 N-RAW 工具是否读取显示矩阵未经验证；NX Studio 列为实机测试项。
- **轴向指派为文档化假设。** 重力向量到姿态的对应关系未经实机标定，是“输出视频不旋转”开问题的候选成因之一，不作定论；若确证两竖拍方向镜像互换，仅改补丁常量字节即可修正，无需改代码。
- **维护者事项。** 16 个含 `photo-tools` 的组合配方经混合装配与结构审计冻结，待具备完整工具包的机器跑全量 31 腿验证；`resources/compiled.json` 中 shared/vrotate 单元的编译器出处记为 LLVM 19.1.7，待发布机重建确认字节一致后更新。

## English

### Windows toolkit revision

The original v0.3.0 can reject pre-capture, pixel-shift or open-gate builds on Windows with `Compiled patch source does not match the reviewed recipe`, even when `--check` passes. v0.3.0-r1 fixes path-separator comparison. Extract the complete revised toolkit into a fresh directory and build from official C 3.11 into a new output directory. Keep the recipes and hash checks intact. `--check` validates input compatibility; it is not a complete build check. See [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12).

Applies to the current four-group release, v0.4.0, built from official Nikon Z8 C 3.11. Historical limitations name their affected releases.

### RAW capture and pre-capture

- Pre-capture supports FX/DX, L, C15/C30 and HE/HE★. Lossless selection falls back to HE★, not lossless. C60/C120 RAW, HLG/HEIF and separately sized secondary JPEG plans remain unsupported.
- Camera files confirm lossless-to-HE★ fallback in DX and FX. Direct HE★ selection in DX, C30, RAW-only remains a separate test.
- Admission, reservations, overflow switching and r/buffer display retain the stock JPEG plan, although the remaining-shot estimate includes NEF and ordinary JPEG quality. Queued NEFs are not all reserved. Database refusal attempts JPEG fallback even for RAW-only. Keep space on each destination card; the displayed count is not a guaranteed NEF capacity.
- RAW buffers remain occupied until NEF writing finishes. Write backlog reduces available burst/history frames; HE★ uses more memory and card space than HE.
- Failed, missing or over-budget NEF writes attempt to create `Z8PRESTP.BIN`. Its presence blocks further extra NEFs and prompts JPEG fallback; restarting does not clear it. A primary-card stop also affects the shared secondary RAW buffer. See the [stop-file guide](stop-file.md#english-summary).
- Some optional lens-correction blocks, a grayscale subimage and XMP correction metadata are absent.

### Log and desqueeze

The camera tester confirmed per-clip labels and view assist on previously recorded and new N-RAW clips. Cross-bank and power-cycle transitions remain separate tests. Desqueeze uses the current magnification on playback.

### ProRes

- HQ has a star; 422/LT/Proxy share the plain icon. Some help text still says HQ. Check the quality menu and the recorded MOV codec.
- Resetting the movie menu does not reset the added grade; select the desired grade again.
- Dimensions and frame rates remain those of stock ProRes 422. ProRes RAW and 3:2 are not added.

### Pixel shift

- **v0.3.0/v0.3.0-r1 recognize only groups whose first file number is `0001`, `2049`, `4097`, `6145` or `8193`**; other groups give an empty list ([issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)). This release fixes group recognition. On camera, 4- and 16-frame groups starting at 4660 and 4664 merged successfully.
- The list does not show how many frames were refused or why. Frames recognized as pixel shift but refused by the format or completeness checks are omitted, so an empty list does not prove that the card has no pixel-shift shots. If a complete camera group is still missing, keep the originals and report it.
- Requires complete 4/8/16/32-frame FX/L 8256×5504 14-bit lossless NEF groups. HE/HE★, DX, incomplete and duplicate groups are unsupported.
- Thumbnails show the first frame. View the merged NEFX on a computer; camera playback does not display the merged result.
- Output is 8256×5504 for 4/8 frames and 16512×11008 for 16/32. Repeated merges use new filenames without overwriting inputs or earlier outputs.

### Open gate and N-RAW tiers

- Open gate is limited to FX 3:2 N-RAW 8.3K 30/25/24p, with 8256×5504 active pixels. It adds neither 50/60p open gate nor ProRes/H.265 3:2. Open gate and the four N-RAW tiers form one build option.
- Compatibility metadata maps Fine to High and Basic to Normal for two-tier readers. Those labels cannot distinguish all four actual encoding grades.
- Basic uses a 1.0-bit/pixel budget, with reduced fine texture observed in camera samples. Open-gate High uses 2.5 bits/pixel versus 3.0 for ordinary 8.3K 30/25/24p High.

### Record video orientation (development group)

Applies to the development-branch fifth group `video-orientation`, which is not part of the v0.4.0 release. See the [video-orientation guide](video-orientation.md).

- **A power cycle returns every bank to the default On.** The value is remembered per movie shooting bank, follows bank switches within the session and a manual Off persists until power-off; after a restart each bank is re-initialized to On. The byte occupies a spare byte of the same camera-settings record as the shipped H.265 tier byte, with identical restart semantics. The row's save, menu-bank switching, power-cycle and reset-menu behaviour is verified on the camera and matches the shipped H.265 tier feature exactly. One issue is open: video recorded with the feature on does not play rotated on a computer; the cause is under investigation.
- **In simultaneous dual-format recording the second file carries no orientation mark.** The one-shot latch marks only the first file of a portrait take to finalize; in simultaneous dual-format recording (an N-RAW/ProRes RAW main file plus an MP4 second file) the later file keeps the stock identity matrix and is not marked. Single-format recording is unaffected; this stands until a code fix ships. See camera leg M9 in the acceptance checklist.
- **N-RAW third-party compatibility is unverified.** The rotation-metadata write path covers every recording format including N-RAW, but whether third-party N-RAW tools read the display matrix is untested; NX Studio is on the camera-test list.
- **The axis assignment is a documented hypothesis.** The gravity-vector-to-pose mapping is not yet calibrated on a camera; it is one candidate cause of the open "output video does not rotate" issue, not a confirmed one. If the two portrait directions turn out mirrored, the correction is patch constant bytes only, with no code change.
- **Maintainer notes.** The 16 photo-tools combinations were frozen via hybrid assembly with a structural audit, pending the full 31-leg validator run on a complete-toolkit machine; the compiler provenance of the shared/vrotate units in `resources/compiled.json` records LLVM 19.1.7, to be confirmed against the release machine's bytes.
