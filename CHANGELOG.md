# 更新日志 / Changelog

## [v0.5.1](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.5.1) — N-RAW 3:2 修复 / N-RAW 3:2 fixes

2026-11-23 发布。以下变化相对于 v0.5.0，只涉及视频录制组；不含视频录制的 7 种组合与 v0.5.0 逐字节相同。

### 修复

- **4.1K 3:2 待机取景冻结。** 修复[问题 #57](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/57)。N-RAW 3:2 选 4.1K 后，即使不开始录制，取景也可能在约十秒内卡死，开关机无响应，需取出电池；120p 下先变得极慢，重启后可能粉屏。原因是 AF 区域仍按 16:9 换算，算出的对焦矩形超出坐标范围。现在 4.1K 3:2 的 AF 区域按 3:2 换算。
- **4.1K 3:2 录制中触屏对焦卡顿。** 录制中在自动区域 AF 下触屏启动跟踪后，取景严重卡顿，按 REC 也不能恢复；120p 单点触屏会提示录制已终止。录制时的 AF 区域同样改为按 3:2 换算。
- **取景器回放 3:2 短片花屏。** 修复[问题 #34](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/34)。在取景器中播放 N-RAW 3:2 短片时出现绿色和品红色错块，因为每帧比原厂回放缓冲的一格多 240 KiB。缓冲格加大到能放下 1280×848 的 3:2 画面，取景器回放保持满宽；后屏回放和普通 16:9 短片的显示不变。
- **3:2 自动区域 AF 绿框。** N-RAW 3:2 下自动区域 AF 的合焦绿框被拉高，行距也比普通视频大。现在单框高度与普通视频相同，各行按原厂照片模式的网格排列；反挤压倍率照常生效。

### 已知问题

- N-RAW 3:2 下，自动区域 AF 和对象跟踪 AF 可能不会启用画面最上、最下各一行对焦点，见[已知问题](docs/known-issues.md)。

### English

Released 2026-11-23. Changes are relative to v0.5.0 and affect only the video recording group; the seven selections without video recording are byte-identical to v0.5.0.

**Fixed**

- 4.1K 3:2 live view no longer freezes before recording ([issue #57](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/57)). With N-RAW 3:2 at 4.1K, live view could lock up within about ten seconds even without recording, the power switch had no effect and the battery had to be removed; at 120p it first slowed to a crawl and could show a pink screen after a restart. The AF area was still converted as 16:9, so the focus rectangle fell outside its coordinate range. 4.1K 3:2 now converts the AF area as 3:2.
- Touch AF during 4.1K 3:2 recording no longer stalls live view. Starting tracking by touch in auto-area AF could slow live view severely, and REC did not recover it; a single-point touch at 120p could end the recording. Recording now uses the same 3:2 AF conversion.
- Playing an N-RAW 3:2 clip in the viewfinder no longer shows green and magenta blocks ([issue #34](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/34)). Each frame was 240 KiB larger than one slot of the stock playback buffer. The slots now hold a 1280×848 3:2 frame, so viewfinder playback keeps its full width; monitor playback and ordinary 16:9 clips look as before.
- Auto-area AF in-focus boxes in N-RAW 3:2 are no longer stretched or spread out. Each box now has the height of an ordinary video box, and the rows follow the stock photo-mode grid; desqueeze factors still apply.

**Known issue**

- In N-RAW 3:2, auto-area AF and subject-tracking AF may not use the top and bottom rows of focus points; see [known issues](docs/known-issues.md).

## [v0.5.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.5.0) — 四组补丁重新分组 / Regrouped feature set

2026-11-21 发布。以下变化相对于 v0.4.0。

### 新增

- **N-RAW 4.1K 3:2。** N-RAW 3:2 改为独立的视频文件类型“N-RAW 12位 3:2(NEV)”，带专用的 10 项画面尺寸列表和取景画幅标志。除原有 8.3K 30／25／24p 外，新增 4.1K（4128×2752）120／100／60／50／30／25／24p；4.1K 30／25／24p 由 8280×5520 全幅读出按 2:1 过采样。列表中的 `[FX 3:2]` 改为 `[FX]`。
- **SDR HEIF。** “色调模式”的 SDR 行可选 JPEG 或 HEIF，普通照片无需切换 HLG 即可保存 10 位 `.HIF`；照片菜单显示 SDR-J／SDR-H。颜色与同场 JPEG 一致，sRGB 与 Adobe RGB 均可用。
- **照片裁切比例。** “选择图像区域”新增 4:3、2.39:1 和 65:24（XPan），取景、JPEG／HEIF 与 NEF 均按比例裁切，L／M／S 各有对应尺寸。照片拍摄菜单、i 菜单和指定的 Fn 键（按住并转动拨盘）都可选择七种画幅。
- **Mac app。** 新增图形界面的 Z8 补丁构建器（Apple 芯片，macOS 14 或更高），内置同一版工具包，按顺序完成输入检查、构建、独立核验和读回校验，界面有简体中文、繁體中文和英文。见 [Mac app 说明](docs/macos-app.md)。

### 修改与修复

- **分组。** 构建选项改为 `video-recording`、`log-colour`、`still-photo-tools`、`raw-precapture`。原 `framing` 与 `video-quality` 合并为视频录制；原 `photo-tools` 拆为照片工具和 RAW 预拍，只装预拍时不再附带像素位移合成。v0.4.0 的组名会被拒绝。
- **像素位移页面。** 改用原厂菜单的按键、可点按底栏（MENU 取消／OK 确定）和字形宽度；左键与 MENU 一样返回，确认页取消回到列表，有损压缩的组提示“仅支持无损压缩”。合成引擎不变。
- **ProRes 文件类型帮助。** 装入视频录制组后，文件类型帮助页里的 ProRes 422 说明不再写 HQ，与菜单中的 ProRes 行一致。
- **高速画面捕捉的照片格式。** 在 C15、C30、C60、C120 中，压缩照片临时使用 JPEG，HEIF 禁用；C15/C30 中无损压缩选项禁用，保存的无损按高效率★记录。回到普通释放模式即恢复当前菜单库的偏好。
- **Adobe RGB JPEG。** 安装照片工具后，Adobe RGB 的 SDR JPEG 嵌入 Nikon Adobe RGB ICC，macOS 预览、小米相册等软件因此按 Adobe RGB 显示。
- **分发。** 工具包只收构建与核验所需的文件和文字说明，带十九份与源码匹配的编译单元。截图、色彩报告与数据和 macOS app 源码只留在仓库中。

### English

Released 2026-11-21. Changes are relative to v0.4.0.

**Added**

- N-RAW 3:2 is now its own movie file type, N-RAW 12-bit 3:2 (NEV), with a ten-entry frame size list and a separate live-view framing mark. Besides 8.3K 30/25/24p it adds 4.1K (4128×2752) at 120/100/60/50/30/25/24p; 4.1K 30/25/24p is oversampled 2:1 from the full 8280×5520 readout. `[FX 3:2]` in the list becomes `[FX]`.
- The SDR row of Tone mode chooses JPEG or HEIF, so ordinary photos can be saved as 10-bit `.HIF` without HLG; the photo menu shows SDR-J or SDR-H. Colours match a same-scene JPEG in sRGB and Adobe RGB.
- Choose image area adds 4:3, 2.39:1 and 65:24 (XPan). Live view, JPEG/HEIF and NEF are cropped, with matching L/M/S sizes. The photo shooting menu, the i menu and an assigned Fn button (hold and turn the dial) all offer the seven areas.
- Z8 Patch Builder, a Mac app for Apple silicon and macOS 14 or later, bundles the same toolkit and runs the input check, build, independent verification and read-back in one pass, in Simplified Chinese, Traditional Chinese and English. See the [Mac app guide](docs/macos-app.md).

**Changed and fixed**

- Build options are now `video-recording`, `log-colour`, `still-photo-tools` and `raw-precapture`. `framing` and `video-quality` merge into video recording; `photo-tools` splits into the still-photo tools and RAW pre-capture, so pre-capture alone no longer brings pixel-shift merge. v0.4.0 group names are rejected.
- The pixel-shift page uses the stock menu keys, a tappable footer (MENU Cancel / OK) and stock glyph widths. The left key goes back like MENU, Cancel on the confirmation page returns to the list, and lossy groups show "Use lossless". The merge engine is unchanged.
- With video recording installed, the file type help describes ProRes 422 without HQ, matching the ProRes row in the menu.
- In C15, C30, C60 and C120, compressed photos use JPEG and HEIF is disabled; C15/C30 disable the lossless option and record a saved lossless setting as HE★. An ordinary release mode restores the active bank’s preferences.
- With the still-photo tools installed, Adobe RGB SDR JPEGs embed the Nikon Adobe RGB ICC profile, so apps such as macOS Preview and the Xiaomi gallery display them as Adobe RGB.
- The toolkit now carries only the files that build and verify firmware, plus the text guides, with nineteen matching compiled units. Screenshots, the colour report and its data and the macOS app source stay in the repository.

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
