# 更新日志 / Changelog

## 未发布 / Unreleased

### 新增 / Added

- **自定义快门声（叠加构建）。** 新增 `shutter_sound.py`：在四组功能任意非空组合或 `--shutter-sound-only` 版本戳基底之上叠加自定义快门声，产出模块 2 变长的完整更新包。原厂 A–E 声音保留；菜单快门音类型新增 Load WAV from card 行，选中显示 CUS，选择保存于卡内 `M2SND0.CFG`/`M2SND1.CFG`。移植自 PIPA12344/z8-card-wav（GPL-3.0-or-later，上游 s3lemming/z9-firmware-patch，见 NOTICE）。选择器标签 ID 使用 0xD00–0xD14，与四组功能字符串表不相交（`tests/test_shuttersound_ids.py` 守护）；双次读取确认、有限重试与暂存 IO 始终启用。零槽单元以源码提交，`resources/shuttersound.json` 钉配方，`--code-source source` 以 LLVM 19.1.7 逐字节复现钉定单元，预编译单元随 Release 工具包分发；四组基底始终用评审过的预编译单元，`patch.py`/`verify.py`/配方体系零改动。每次构建后独立核验：容器回读、从原厂输入全量重建、库存前缀窗口审计与身份字段。离线验证：16 种选择全矩阵 + 源码/预编译等价 + 7 项负控全部通过；上游 27+13 项 ARM 回归通过。全部功能（四组 + 自定义快门声）完整实机验证通过，见 `docs/custom-shutter-sound.md`。

English: `shutter_sound.py` layers a custom shutter sound on any combination of the four feature groups (or a version-stamped stock base via `--shutter-sound-only`) and repacks the container with the longer module 2. Ported from PIPA12344/z8-card-wav (GPL-3.0-or-later; Z9 ancestor s3lemming/z9-firmware-patch). Picker label IDs occupy 0xD00–0xD14, disjoint from the feature string tables, with unconditional confirmation, retry and staged IO. The zero-slot unit ships as source with the recipe pinned in `resources/shuttersound.json`; source builds byte-match the pinned unit under LLVM 19.1.7 and prebuilt units follow the Release toolkit policy. Every build is independently verified (container roundtrip, full rebuild from the stock input, window audit, identity checks). The 16-selection offline matrix, source/prebuilt parity and seven negative controls pass; upstream ARM suites pass. The full feature set passed complete on-camera verification; see `docs/custom-shutter-sound.md`.

## v0.4.0 — 四组补丁 / Four feature groups

当前预发布：[v0.4.0-rc.2](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.4.0-rc.2)。以下变化相对于上一公开功能系列 v0.3.0／v0.3.0-r1。RC2 补全 README 使用说明、致谢和模拟器截图；固件补丁与 RC1 相同。

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
