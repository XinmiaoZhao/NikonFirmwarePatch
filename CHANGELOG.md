# 更新日志 / Changelog

## 未发布 / Unreleased

以下为 Born2Ski 分支在 v0.5.0 之上的改动（供上游合并的版本）。部分解码由新的“Turbo RAW”菜单开关控制，默认关闭；开关两种状态均已在 Z8 机身上测试（固件 03.12.t1，此前关闭状态 03.12.u1）；部分解码代码另在固件 03.12.v9 上测试（`raw-precapture`：C15／C30／C60 预拍、机内“NEF（RAW）处理”与 RAW-only 回放）。预拍单元与 RAW 记录菜单单元及组合配方已用 Apple clang 21.0.0（clang-2100.4.1.1）重新生成。构建方法：将本分支文件覆盖到解压后的 v0.5.0 完整工具包（其余预编译单元不变），运行 `python tools/build_precapture_unit.py` 编译并核对这两个单元，再按默认预编译模式构建。（本条中文由 AI 根据英文原文翻译。）

### 新增

- **C60 RAW。** C60 现在与 C15／C30 相同：预拍历史帧和正式帧按普通“画质”（RAW、RAW+JPEG、JPEG）和“RAW 记录”（HE／HE★）输出，预拍最多 60 帧（每秒 60 帧下 1 秒）。C60 始终记录 DX 区域（5408×3608 NEF，与 C15／C30 的 DX 文件相同）。已在 Z8 机身上测试（固件 03.12.q1 与 03.12.v9，启用部分解码时每秒 60.0 帧，HE★ 每次连拍 214–266 张）；本构建每帧都解码（固件 03.12.u1）：HE★ 每秒 59.9 帧下一次连拍 201 张后缓存写满，每秒写入 20 个 NEF。C120 RAW 仍不支持。（本条中文由 AI 根据英文原文翻译。）

- **Turbo RAW（照片拍摄菜单）。** 新增开关行，位于“照片拍摄菜单”第三行（“扩展菜单库”之下，即原厂隐藏的条目 2CAAh），外观与“长时间曝光降噪”相同，默认关闭。开启后仅 RAW 连拍只解码部分帧：C15／C30 的 HE★（FX 每 5 帧、DX 每 3 帧）与 C60（HE★ 每 4 帧、HE 每 3 帧），另加首帧和最新一帧；其余帧写入生成的灰色预览，并跳过主 JPEG 编码与显像处理，因此连拍更长（同一代码在 Z8 机身上实测，固件 03.12.v9：C30 FX HE★ 每次连拍约 128 张、每秒 20.5 个 NEF；C60 HE★ 214–266 张）。关闭时每帧都解码（固件 03.12.u1 的行为）。设置保存在设置组 1Eh 中设置 1E50h（1 字节）之后的空闲字节中，随该组保存：0 = 从未设置（按关闭处理），1 = 关，2 = 开。菜单只有一行说明，因为全部功能组同时选择时共享文本区只剩约 3.9 KiB。新增字符串 3250–3251；`z8patch/contract.py` 相应调整：`raw-precapture` 现在总有语言表，复制边界覆盖它们。已在 Z8 机身上测试（固件 03.12.t1，仅 RAW HE★）：开关可切换，关机及取出电池后保持；开启时 C30 FX 每次连拍 129 张、每秒 20.4 个 NEF，C60 DX 267 张、每秒 31.3 个；关闭时 73 张与 203 张，所有预览均为真实图像。（本条中文由 AI 根据英文原文翻译。）

### 修改与修复

- **RAW 记录菜单单元移至预拍代码区末尾。** `raw-precapture` 的 RAW 记录菜单单元（312 字节）由 0x409F9000 移至 0x409FF000，预拍单元可使用 0x409F0000–0x409FF000；菜单行为不变，其 C 档判断另含 C60（C60 RAW 见下）。（本条中文由 AI 根据英文原文翻译。）
- **预拍 NEF 文件头。** 针对[问题 #23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23)、[#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27)：机身自带的 NEF 读取器要求 IFD0 的 SubIFDs 恰好六项且后三项偏移非零，旧文件头只写三项（回退路径两项），因此“NEF（RAW）处理”提示“无法编辑照片”。现在始终写六个 SubIFD，SubIFD3–5 采用原厂无图像时的空占位。
- **与原厂 NEF 标签表对齐。** 新增 NEFInfo 块 0x05–0x07、0x0C、0x10–0x13（由原厂写入函数生成）和 MakerNote 0x0046、0x008C、0x00A4；不再从 JPEG 头带入 IFD0 0x013E／0x013F／0x0211、Exif 0xA500 与 MakerNote 0x0050。
- **RAW-only 预拍的连拍起始文件编号。** NEF 头由原厂为 JPEG 计划生成的文件头构建，因此 MakerNote 0x0056 的连拍起始编号为 JPG 类型，指向 RAW-only 下被取消的 JPEG。仅写 NEF 时，现将该编号的类型改为 NEF；原厂写入器完成时用于回放文件列表的 M+0x118／+0x11C 在写入期间同样给出 NEF 类型，写完后恢复。只修改通过原厂校验的编号；同卡 RAW+JPEG 不变。
- **RAW-only 连拍的回放连拍组图标。** RAW-only 时 NEF 写完后会取消该帧的 JPEG 成员，取消操作按数据库刷新回放列表中的条目，而数据库不含连拍字段，因此连拍组图标要到重新插卡后才显示（分组与翻组正常）。现在取消后按原厂写入器完成时的方式（0x406cd6bc–0x406cd75c）再次发送该 NEF 的“文件已写入”事件，带 NEF 类型的起始编号与连拍序号；只用于卡 1／2 上的连拍帧，不写卡。
- **C15／C30 连拍的 NEF 写入加速（固件 03.12.f1 实测）。** 旧 NEF 把 VGA、FHD 和整幅预览紧接排列在未对齐的文件偏移上；约四分之三的 NEF 在原厂写入器中要多用约 0.13 秒，RAW 帧每秒只能写入 5–6 张，缓存很快写满。现在 NEF 各部分与原厂 NEF 一样从 512 字节边界开始（在 MakerNote 范围内及预览之间补零）；图像数据不变，文件大小不变或增加 4 KB（RAW 数据仍从 4 KB 边界开始）。Z8 机身配 CFexpress 卡、仅 RAW 实测：C30 HE 由 134 张增至 184 张（每秒 6.4 → 14.3 个 NEF），C30 HE★ 66 → 74 张，C15 HE★ 90 → 130 张；C15 HE 每秒写入 14.4 个 NEF（拍摄 15 张／秒），一次连拍 412 张。剩余的限制是相机对缓存中每帧的解码（每秒约 245 MB 压缩 RAW），见已知问题。（本条中文由 AI 根据英文原文翻译。）
- **预拍 NEF 可在机内执行 NEF（RAW）处理（已在 Z8 机身上测试，固件 03.12.v9）。** 预拍 NEF 的 MakerNote 0x0034（快门模式）沿用高速连拍 JPEG 文件头中的 0x60（电子快门，高速），原厂固件从不把该值写入 NEF；“润饰 › NEF（RAW）处理”遇到该值会使相机重启（只改该值的普通 Z8 NEF 同样如此）。现在写入普通 Z8 NEF 的 0x10（电子快门）。预拍 NEF 现可在机内处理。用早期构建拍摄的文件仍带 0x60。（本条中文由 AI 根据英文原文翻译。）

### English

Changes of the Born2Ski branch on top of v0.5.0 (the version offered for upstream). Partial decoding is switched by the new Turbo RAW menu row, Off by default; both states of the switch were tested on a Z8 (firmware 03.12.t1; Off earlier with 03.12.u1), and the partial-decoding code also with firmware 03.12.v9 (`raw-precapture`: C15/C30/C60 pre-capture, in-camera NEF (RAW) processing and RAW-only playback). The pre-capture and RAW recording menu units and the combination recipes were regenerated with Apple clang 21.0.0 (clang-2100.4.1.1). To build, copy this branch over an extracted v0.5.0 toolkit (the other prebuilt units are unchanged), run `python tools/build_precapture_unit.py` to compile and check both units, then build in the default prebuilt mode.

**Added**

- **C60 with RAW.** C60 now works like C15/C30: history and post-release frames follow ordinary Image quality (RAW, RAW+JPEG, JPEG) and RAW recording (HE/HE★), with up to 60 pre-release frames (1 s at 60 fps). C60 always records the DX area (5408×3608 NEFs, the same files as DX in C15/C30). Tested on a Z8 (firmware 03.12.q1 and 03.12.v9, with partial decoding on: 60.0 fps, HE★ 214–266 frames per burst); this build decodes every frame (firmware 03.12.u1): HE★ 201 frames at 59.9 fps until the buffer is full, 20 NEFs written per second. C120 RAW is still unsupported.

- **Turbo RAW (Photo shooting menu).** A new switch row, the third row of the Photo shooting menu (below Extended menu banks; the stock hidden item 2CAAh), drawn like Long exposure NR, Off by default. On, RAW-only bursts decode only some frames: HE★ in C15/C30 (FX every 5th, DX every 3rd frame) and C60 (HE★ every 4th, HE every 3rd), plus the first and the newest frame; the other frames get generated gray previews and skip the main JPEG encode and development, so bursts last longer (the same code measured on a Z8 with firmware 03.12.v9: C30 FX HE★ about 128 frames per burst at 20.5 NEFs per second; C60 HE★ 214–266 frames). Off, every frame is decoded (the behaviour of firmware 03.12.u1). The value is kept in the spare byte after setting 1E50h (one byte) in settings group 1Eh and saved with the group: 0 = never set (treated as Off), 1 = Off, 2 = On. The row has one line of help, because the shared text area has about 3.9 KiB left with every group selected. New strings 3250–3251; `z8patch/contract.py` follows: `raw-precapture` now always has language tables, and the copy boundary covers them. Tested on a Z8 (firmware 03.12.t1, RAW-only HE★): the switch toggles and is kept after power-off and battery removal; On, C30 FX ran 129 frames per burst at 20.4 NEFs per second and C60 DX 267 at 31.3; Off, 73 and 203 frames, every preview real.

**Changed and fixed**

- **RAW recording menu unit moved to the end of the pre-capture cave.** The `raw-precapture` RAW recording menu unit (312 bytes) moves from 0x409F9000 to 0x409FF000, so the pre-capture unit may use 0x409F0000–0x409FF000; the menu behaves as before, and its C-mode test also covers C60 (see C60 RAW below).
- **Pre-capture NEF header.** For [issue #23](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/23) and [#27](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/27): the camera's own NEF reader requires exactly six SubIFDs in IFD0 with non-zero offsets for the last three. The previous header wrote three (two on the fallback path), so Retouch › NEF (RAW) processing reported “Unable to edit picture”. Six are now always written; SubIFD3–5 are the empty placeholders stock firmware writes when a frame has no such image.
- **Stock NEF tag lists.** Adds NEFInfo blocks 0x05–0x07, 0x0C, 0x10–0x13 (produced by the stock writer functions) and MakerNote 0x0046, 0x008C, 0x00A4. IFD0 0x013E/0x013F/0x0211, Exif 0xA500 and MakerNote 0x0050 are no longer carried over from the JPEG header.
- **Burst-start file ID in RAW-only pre-capture.** The NEF header is built from the header the camera made for the JPEG plan, so MakerNote 0x0056 carried a JPG-typed burst-start ID pointing at a JPEG that RAW-only cancels. When a card gets only the NEF, the ID now has the NEF type. The stock writer's completion, which re-reads M+0x118/+0x11C for the playback file list, sees the same NEF-typed ID during the write, and the word is restored afterwards. Only IDs the stock validator accepts are changed; RAW+JPEG on one card is unchanged.
- **Series symbol in playback for RAW-only bursts.** In RAW-only, the frame's JPEG member is cancelled after the NEF is written. The cancel refreshes the playback-list entry from the database, which has no series fields, so the series symbol appeared only after the card was reloaded (grouping and group navigation already worked). After the cancel, the NEF's "file written" event is now sent again, built as the stock writer's completion builds it (0x406cd6bc–0x406cd75c), with the NEF-typed start ID and the shot number. This applies only to series frames on card 1 or 2 and writes nothing to the card.
- **Faster NEF writing in C15/C30 bursts (tested on a Z8, firmware 03.12.f1).** The NEF placed the VGA, FHD and full-size previews back to back at unaligned file offsets. For about three of every four NEFs the stock writer took about 0.13 s longer, so RAW frames reached the card at only 5–6 per second and the buffer filled quickly. Every part of the NEF now starts on a 512-byte boundary, as in stock NEFs (zero padding inside the MakerNote's range and between the previews); the image data is unchanged and a file is the same size or 4 KB larger (the RAW data still starts on a 4 KB boundary). Measured on a Z8 with a CFexpress card, RAW-only: C30 HE 134 → 184 frames (6.4 → 14.3 NEFs per second), C30 HE★ 66 → 74, C15 HE★ 90 → 130; C15 HE writes 14.4 NEFs per second against 15 frames per second and ran 412 frames in one burst. The remaining limit is the camera's decode of each buffered frame (about 245 MB of compressed RAW per second); see the known issues.
- **In-camera NEF (RAW) processing of pre-capture NEFs (tested on a Z8, firmware 03.12.v9).** Pre-capture NEFs carried MakerNote 0x0034 (ShutterMode) = 0x60 (electronic, high speed) from the high-speed frame capture's JPEG header, a value stock firmware never writes into a NEF; Retouch › NEF (RAW) processing restarts the camera when it meets it (a normal Z8 NEF with only this value changed does too). The NEF now carries 0x10 (electronic), as a normal Z8 NEF does. Pre-capture NEFs now process in camera. Files recorded with earlier builds still carry 0x60.

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
- **ProRes 文件类型名称。** 装入视频录制组后，ProRes 行显示“ProRes 422 10位(MOV)”，文件类型帮助的标题相应改为 ProRes 422。
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
- With video recording installed, the ProRes file type row reads "ProRes 422 10-bit (MOV)", and the file type help heading reads ProRes 422.
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
