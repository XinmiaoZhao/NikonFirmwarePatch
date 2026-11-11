# 更新日志 / Changelog

## 未发布 / Unreleased

已在 Z8 机身上测试（`photo-tools`，C15／C30 预拍，机内“NEF（RAW）处理”与 RAW-only 回放）。`resources/compiled.json` 与 `resources/combinations.json` 中的预拍单元和组合配方已用 Apple clang 21.0.0（clang-2100.4.1.1）重新生成；构建方法：将本分支文件覆盖到解压后的 v0.4.0 完整工具包（其余八个预编译单元不变），运行 `python tools/build_precapture_unit.py` 生成并核对 `resources/precapture.bin`，再按默认预编译模式构建。

### 修改与修复

- **预拍 NEF 文件头。** 针对[问题 #23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)、[#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27)：机身自带的 NEF 读取器要求 IFD0 的 SubIFDs 恰好六项且后三项偏移非零，旧文件头只写三项（回退路径两项），因此“NEF（RAW）处理”提示“无法编辑照片”。现在始终写六个 SubIFD，SubIFD3–5 采用原厂无图像时的空占位。
- **与原厂 NEF 标签表对齐。** 新增 NEFInfo 块 0x05–0x07、0x0C、0x10–0x13（由原厂写入函数生成）和 MakerNote 0x0046、0x008C、0x00A4；不再从 JPEG 头带入 IFD0 0x013E／0x013F／0x0211、Exif 0xA500 与 MakerNote 0x0050。
- **RAW-only 预拍的连拍起始文件编号。** NEF 头由原厂为 JPEG 计划生成的文件头构建，因此 MakerNote 0x0056 的连拍起始编号为 JPG 类型，指向 RAW-only 下被取消的 JPEG。仅写 NEF 时，现将该编号的类型改为 NEF；原厂写入器完成时用于回放文件列表的 M+0x118／+0x11C 在写入期间同样给出 NEF 类型，写完后恢复。只修改通过原厂校验的编号；同卡 RAW+JPEG 不变。
- **RAW-only 连拍的回放连拍组图标。** RAW-only 时 NEF 写完后会取消该帧的 JPEG 成员，取消操作按数据库刷新回放列表中的条目，而数据库不含连拍字段，因此连拍组图标要到重新插卡后才显示（分组与翻组正常）。现在取消后按原厂写入器完成时的方式（0x406cd6bc–0x406cd75c）再次发送该 NEF 的“文件已写入”事件，带 NEF 类型的起始编号与连拍序号；只用于卡 1／2 上的连拍帧，不写卡。

### English

Tested on a Z8 (`photo-tools`, C15/C30 pre-capture, in-camera NEF (RAW) processing and RAW-only playback). The pre-capture unit and combination recipes in `resources/compiled.json` and `resources/combinations.json` were regenerated with Apple clang 21.0.0 (clang-2100.4.1.1). To build, copy this branch over an extracted v0.4.0 toolkit (the other eight prebuilt units are unchanged), run `python tools/build_precapture_unit.py` to compile and check `resources/precapture.bin`, then build in the default prebuilt mode.

- **Pre-capture NEF header.** For [issue #23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23) and [#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27): the camera's own NEF reader requires exactly six SubIFDs in IFD0 with non-zero offsets for the last three. The previous header wrote three (two on the fallback path), so Retouch › NEF (RAW) processing reported “Unable to edit picture”. Six are now always written; SubIFD3–5 are the empty placeholders stock firmware writes when a frame has no such image.
- **Stock NEF tag lists.** Adds NEFInfo blocks 0x05–0x07, 0x0C, 0x10–0x13 (produced by the stock writer functions) and MakerNote 0x0046, 0x008C, 0x00A4. IFD0 0x013E/0x013F/0x0211, Exif 0xA500 and MakerNote 0x0050 are no longer carried over from the JPEG header.
- **Burst-start file ID in RAW-only pre-capture.** The NEF header is built from the header the camera made for the JPEG plan, so MakerNote 0x0056 carried a JPG-typed burst-start ID pointing at a JPEG that RAW-only cancels. When a card gets only the NEF, the ID now has the NEF type. The stock writer's completion, which re-reads M+0x118/+0x11C for the playback file list, sees the same NEF-typed ID during the write, and the word is restored afterwards. Only IDs the stock validator accepts are changed; RAW+JPEG on one card is unchanged.
- **Series symbol in playback for RAW-only bursts.** In RAW-only, the frame's JPEG member is cancelled after the NEF is written. The cancel refreshes the playback-list entry from the database, which has no series fields, so the series symbol appeared only after the card was reloaded (grouping and group navigation already worked). After the cancel, the NEF's "file written" event is now sent again, built as the stock writer's completion builds it (0x406cd6bc–0x406cd75c), with the NEF-typed start ID and the shot number. This applies only to series frames on card 1 or 2 and writes nothing to the card.

## [v0.4.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.4.0) — 四组补丁 / Four feature groups

2026-11-10 发布。以下变化相对于上一公开功能系列 v0.3.0／v0.3.0-r1。v0.4.0 的源码、九份预编译补丁单元和固件补丁与预发布版 v0.4.0-rc.2 相同，只更新版本标注和下载链接；RC2 补全了 README 使用说明、致谢和模拟器截图，固件补丁与 RC1 相同。

### 新增

- **构建选项。** 可独立选择画幅、视频品质、Log 色彩和照片工具，或从原厂 C 3.11 一次构建任意非空组合，共 15 种。分别使用 `framing`、`video-quality`、`log-colour`、`photo-tools`；原来的四个 CLI 名称仅适用于对应旧工具包。
- **反挤压监看。** 画幅组新增关闭及 1.25× 至 2.00× 共七种校正倍率；按视频菜单库保存，用于取景、放大导航和回放，录像保留原始像素比例。开放门和 N-RAW 四档画质仍归同一组。
- **H.265 码率。** 视频品质组提供原厂标称码率的 100%、60%、45%、30%、20%，菜单可显示当前模式的目标 Mbps。100% 使用星标。ProRes 的 HQ／422／LT／Proxy 继续按菜单库保存，新增 HQ 星标。
- **Log 录像与监看。** 视频菜单可选 N-Log／BT.2020、S-Log3／S-Gamut3.Cine、Log3G10／REDWideGamutRGB。两种新增 Log 使用实拍标定的线性矩阵与色度补偿，具有对应的图标、片段名称和显示辅助。
- **DX RAW 预拍。** 照片工具扩展 C15/C30 的 DX 输出，保留完整 DX 预览，并按所选画质写出 RAW 或 RAW+JPEG。FX 和 DX 的无损选项在预拍时回退为 HE★。
- **后期与复核。** 增加中英文色彩报告、实拍／模拟色差图、两套机内监看表的来源、Resolve／Final Cut Pro 输入设置，以及供后期使用的 65³ F LUT。

### 修改与修复

- **像素位移组识别。** 修复[问题 #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)。扫描器按文件类型、卡槽、文件夹和起始编号分别读取组身份；过去从 0001、2049 等之外的编号起拍时，完整组可能在列表中消失。现在无需重置文件编号，同一文件夹连续多组、跨 DSC_9999 边界和副卡组也可识别。常规完整性、曝光及位移检查仍然生效。
- **N-RAW 代理回放。** 详情页名称与显示辅助根据片段自己的 Log 名称选择。机身实测覆盖旧录与新录素材；回取景时恢复录像菜单选择。保留 RAW 本体的原厂色调分类，便于后期按 RAW 解码。
- **显示几何。** 反挤压状态下同步调整 AF 框、亮起的 AF 点与触控映射。影片回放按当前反挤压倍率显示。
- **视频菜单与编码。** ProRes 和 H.265 的星标按格式分流；离开 H.265 模式时，码率行显示百分比。调整 H.265 保护计时，避免部分 4K50/60 模式选 60% 后意外变成全帧内编码。
- **组合与分发。** 四组共享菜单布局、语言资源及菜单库字段复制。完整 toolkit 提供九份与源码匹配的编译单元。Windows CI 使用经哈希验证的发行 ZIP 构建固件，并将全选输出与提供的参考哈希比较。

### English

Released 2026-11-10. Changes are relative to the previous public series, v0.3.0/v0.3.0-r1. The source, nine compiled patch units and firmware patches of v0.4.0 match pre-release v0.4.0-rc.2; only version labels and download links changed.

**Added**

- Choose any of four build groups from stock Z8 C 3.11. The CLI supports all 15 nonempty combinations and has an interactive selection mode.
- Framing adds seven anamorphic desqueeze factors (1.25× through 2.00×) plus Off. The factor follows the movie bank in live view and is selectable for playback. Open gate and the four N-RAW quality tiers stay together.
- Video quality adds five H.265 bitrate targets (100/60/45/30/20%) and a displayed target in Mbps. The highest H.265 setting and ProRes HQ have format-specific stars.
- Select N-Log, S-Log3 or Log3G10 in the recording menu. Both new Log modes have calibrated recording matrices, chroma compensation, clip labels, icons and dedicated monitoring transforms.
- C15/C30 RAW pre-capture supports DX geometry and previews as well as FX. Lossless selection produces HE★ in pre-capture.
- The bilingual colour report, measurements, control simulations, grading instructions and optional 65³ F LUT document the capture-to-post workflow.

**Changed and fixed**

- Pixel-shift group discovery now checks the fields in the burst-start word individually. Complete groups can start at any file number, share a folder, roll over DSC_9999 or reside on the secondary card. This fixes the empty-list symptom in [issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17).
- N-RAW proxy playback selects the label and assist transform from the clip’s own Log name. The tester confirmed both on existing and new recordings. Returning to live view restores the recording selection.
- Desqueeze adjusts lit AF points, AF overlays and touch mapping. ProRes and H.265 share icon resources while keeping format-specific indicators and independent saved settings.
- The H.265 row shows a percentage outside H.265 mode. A protection-timer correction prevents an unintended all-intra pattern in certain 4K50/60 modes at the 60% setting.
- The toolkit bundles nine reviewed compiled units. Windows CI downloads and verifies the release ZIP before building and checking the reference full-selection firmware. RC2 restores the bilingual setup and recovery guidance, contributor credits and emulator gallery; its firmware patches match RC1.

## [v0.3.0-r1](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.3.0-r1) — 2026-10-29

- v0.3.0 的第一次主机工具修订，修复 [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12)：Windows 的反斜杠路径被误判为源码不匹配。
- 源码身份键统一为 `/`；仍逐字节校验源码与预编译补丁，不改变哈希要求。
- 加入 Windows／POSIX 路径回归、缺失与损坏文件负控，以及 Windows 默认预编译构建检查。
- 四份补丁机器码、15 种组合配方、原厂 C 3.11 输入要求及机内功能均与 v0.3.0 相同。原 v0.3.0 标签与附件保持不变。

English: first host-tool revision of v0.3.0. Fixes Windows source-path comparison by using forward-slash manifest keys, while preserving exact byte/hash checks. Adds cross-platform path regression, integrity negative controls and Windows prebuilt CLI checks. Firmware code, all 15 recipes and the required C 3.11 input are unchanged; the original v0.3.0 tag and assets are retained.

## [v0.3.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.3.0) — 2026-10-29

- 新增机内像素位移组浏览、选择与 NEFX 合成，支持 4／8／16／32 张无损 NEF 组。
- 新增 FX 3:2 N-RAW 开放门，支持 8.3K 30／25／24p。
- 新增 N-RAW Fine／Basic，形成 High／Fine／Normal／Basic 四档，并提供相应菜单、文件标识与剩余录制时间估算。
- 四个功能选项可独立选择，共 15 种非空组合；ProRes 可与“开放门＋N-RAW”分别构建。
- 改进 RAW 预拍剩余张数：计入 NEF，并随 RAW 压缩、JPEG 档位及 ★ 设置刷新。
- 改进 RAW 预拍的登记拒绝处理：只尝试 JPEG 回退，不再绕过数据库直接写 NEF；后续帧可继续尝试正常 NEF 写入。停止文件机制仍保留。

English: adds in-camera pixel-shift merging, FX 3:2 N-RAW at 8.3K 30/25/24p, four N-RAW quality tiers, and independent selection of four features. Improves pre-capture remaining counts and database-refusal handling; the stop-file mechanism remains in use.

## [v0.2.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.2.0)

- RAW 连拍／预拍新增 HE★，可在机内“RAW 记录”选择 HE／HE★。
- 移除对 `Z8PRE.CFG` 的依赖，直接使用机内设置；旧配置文件不再读取。
- QUAL／f2、i 菜单和取景画质标识使用普通“画质”设置。
- 完善双卡备份及 RAW／JPEG 分卡规则，每帧使用提交时的主卡槽和副卡槽设置。
- 保留 ProRes 四档与菜单库分别保存功能。

English: adds HE★ RAW capture, removes the CFG dependency, aligns quality controls/displays with the ordinary menu, and extends dual-card routing using the settings stored when each frame is submitted.

## [v0.1.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.1.0)

- 首次公开面向官方 Nikon Z8 C 3.11 的补丁构建工具。
- 提供 ProRes HQ／Standard／LT／Proxy，支持按拍摄菜单库分别保存。
- 提供 C15／C30 HE RAW 连拍与预拍，使用普通画质菜单选择 RAW／RAW+JPEG／JPEG；NEF 带整幅预览并支持机内回放。
- ProRes 与 RAW 预拍可单独或组合构建。
- 提供源码、预编译补丁工具包和独立固件核验工具。

English: first public release for official Z8 C 3.11, with four ProRes grades, per-bank settings, C15/C30 HE RAW/pre-capture, selectable feature combinations, precompiled patch distribution and independent output verification.
