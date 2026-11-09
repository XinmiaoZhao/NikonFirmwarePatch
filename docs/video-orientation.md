# 记录视频方向 / Record video orientation

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features video-orientation` 是开发分支新增的第五个构建组，尚未包含在 v0.4.0-rc.2 发布工具包中。它在视频拍摄菜单中新增一行**“记录视频方向”**（英文 Record video orientation，日文 動画の縦横位置情報の記録；标题覆盖相机全部 36 个语言槽位），插入在“图像区域”一行之前。取值为行内**开／关**切换，直接复用原厂的开／关文案。设置按视频拍摄菜单库 A–D 分别保存，**默认开**。

开启时，相机在**开始录像的一刻**锁定持机姿态（由姿态传感器的重力向量判定）：两个方向的竖拍与 180° 倒置会在录像容器中写入 QuickTime **tkhd 显示矩阵**（旋转元数据）；横拍不写入旋转矩阵，与原厂一致。写入经由相机唯一的视频封装路径，设计上覆盖相机录制的全部格式——MP4（H.264）、H.265、ProRes 422 HQ（MOV；视频品质组的其余 ProRes 档位走同一录制路径）、ProRes RAW 与 N-RAW。姿态只在录制开始时判定一次：录制中途改变握持不影响本次录像的标记，回放或传送时对文件的分析也不会复用过期姿态。

关闭（或横拍）时不写入矩阵，容器与原厂输出逐字节一致。不选择该组的构建中，视频拍摄菜单保持原厂行集不变。

### 使用步骤

1. 构建时选择 `video-orientation`，可与其他组任意组合（含该组共 31 种非空组合）。
2. 在视频拍摄菜单找到“记录视频方向”，位于视频画质各行之后、“图像区域”之前。
3. 按 OK 键、转动指令拨盘或触摸该行，即可在开／关之间切换；需要不同菜单库使用不同设置时，切换到相应菜单库分别设置。

### 断电与菜单库

- **默认开。** 安装后首次开机即为开；断电重启后各菜单库回到默认“开”。
- **会话内持久。** 手动关闭在本次开机期间一直有效，并按菜单库 A–D 分别记忆；切换菜单库时取值随库切换。
- 该取值字节与已发布的 H.265 码率档位字节同属一个相机设置记录的空位，断电后均不保留——本功能重启后回到默认“开”，与 H.265 档位的会话语义属同一类。
- “重设视频拍摄菜单”的行为已实机验证，与已发布的 H.265 档位一致（重设不重置该行取值）。

### 兼容性

ffmpeg（ffplay／ffprobe）、Adobe Premiere Pro、DaVinci Resolve、Final Cut Pro、VLC 与 QuickTime Player 均读取 tkhd 显示矩阵并按其旋转画面。N-RAW 是尼康自有封装：静态分析表明相机全部录像格式共用同一封装路径（矩阵写入点唯一），但**第三方 N-RAW 工具是否读取该矩阵未经验证**；NX Studio 列为实机测试项。

### 验证状态

- **离线检查通过**：全量单元测试（含状态窗口迁移与构建期护栏）；非空组合 31 种全部配方冻结（15 份无照片工具组合真实构建逐字节复验，16 份含照片工具组合经混合装配与结构审计冻结）；`verify.py` 对单选与“四视频组＋视频方向”产物独立核验通过。
- **仿真：菜单打开回归已通过（2026-11-09）。** 此前开发分支镜像打开任何菜单页都会触发 EL0 权限异常并终止 APPMENU——单元运行期状态字节（哨兵／锁存等）曾被置于只读代码洞。修复将全部状态迁入每次上电由 boot 按镜像重载、EL0 可写的独立数据窗口（行事件表改置洞内固定只读子窗），并配构建期护栏防回归。QEMU 全系统回归三腿全过：崩溃基线镜像作阳性对照逐字段复现异常横幅，修复镜像全程零横幅且哨兵／magic 字节符合设计，二次开页幂等（工件 `build/t14/vrfix-reg/`，z8-qemu 侧）。
- **仿真：行值渲染已验收（2026-11-09）。**首次仿真人工验收发现原设计（字符串 id 路径，取值子件存在高位 id 截断）渲染异常（未选中显示文字样式、选中显示沙漏图标）；已按既定回退改走原厂布尔控件路径（衰减器行同款，复用原厂本地化开／关文案，仅两处 movz 立即数与两处调用目标变化）。复验通过：取值为与原厂布尔行同款的 On／Off 开关样式，翻值即时切换且与存储字节同轨；开关与存储行为不变，五组合配方第五次再冻结（15 份不含本组组合零漂移）。
- **实机验收：菜单行为全部通过**：菜单项的保存、菜单库切换、断电回默认开与菜单重设，均与已发布的 H.265 档位功能完全一致。**唯一开问题：功能开启时录制的视频在电脑上播放不旋转，原因排查中**（此前“旋转方向正确性”待验表述作废——旋转本身未生效，方向无从谈起）。重力向量到姿态的轴向指派仍为文档化假设，是该开问题的候选成因之一，不作定论（若确证两竖拍方向镜像互换，仅需修改补丁常量字节即可修正，无需改代码）；菜单库随库切换的双向记忆亦经仿真实证。

### 已知问题

断电回到默认“开”、会话内持久、N-RAW 第三方工具兼容未知等限制见[已知问题](known-issues.md)。

## English

### Overview

`--features video-orientation` is a fifth build group on the development branch; it is not part of the v0.4.0-rc.2 release toolkit. It adds one row, **Record video orientation** (Japanese 動画の縦横位置情報の記録; the title ships in all 36 camera language slots), to the video shooting menu, directly before **Image area**. The row is an inline **On/Off** toggle reusing the camera's own localized On/Off texts. The setting is stored per movie shooting bank A–D and **defaults to On**.

When On, the camera locks its grip orientation **at the moment recording starts** (classified from the orientation sensor's gravity vector): both portrait directions and 180° upside-down write a QuickTime **tkhd display matrix** (rotation metadata) into the movie container; landscape writes no rotation matrix, exactly like stock. The write goes through the camera's single movie-muxing path, so by design it covers every format the camera records: MP4 (H.264), H.265, ProRes 422 HQ (MOV; the video-quality group's other ProRes grades use the same recording path), ProRes RAW and N-RAW. Orientation is decided once at recording start: changing grip mid-take does not alter the mark for that clip, and playback- or transfer-side analysis of the file cannot reuse a stale pose.

When Off (or when recording in landscape), no matrix is written and the container is byte-identical to the stock output. Builds that do not select this group keep the video shooting menu at its stock row set.

### Steps

1. Select `video-orientation` when building; it combines freely with the other groups (31 nonempty combinations with it included).
2. Find Record video orientation in the video shooting menu, after the video-quality rows and before Image area.
3. Press OK, turn the command dial or touch the row to switch between On and Off. To use different settings in different banks, select each bank and set its value.

### Power cycle and banks

- **Default On.** The feature is On from the first boot after installation; after a power cycle every bank returns to the default On.
- **Session persistence.** A manual Off stays in effect for the whole session and is remembered separately for banks A–D; switching banks switches the value with it.
- The value byte occupies a spare byte of the same camera-settings record as the shipped H.265 tier byte. Neither survives a power cycle, so this row shares the H.265 tier's session semantics: the default returns after a restart.
- The reset-menu behaviour is verified on the camera and matches the shipped H.265 tier (resetting the movie shooting menu does not reset this row).

### Compatibility

ffmpeg (ffplay/ffprobe), Adobe Premiere Pro, DaVinci Resolve, Final Cut Pro, VLC and QuickTime Player all read the tkhd display matrix and rotate accordingly. N-RAW is Nikon's own container: static analysis shows all recording formats share the one muxing path (a single matrix write site), but whether third-party N-RAW tools honour the matrix is unverified; NX Studio is on the camera-test list.

### Validation status

- **Offline checks pass**: the full unit-test suite (including the state-window migration and the build-time guards); all 31 five-group recipes are frozen (the 15 without photo-tools rebuilt byte-exactly; the 16 photo-tools combinations via hybrid assembly); `verify.py` independently passes the single-group and four-video-groups-plus-orientation outputs.
- **Emulation: menu-open regression passed (2026-11-09).** Earlier development-branch images aborted APPMENU with an EL0 permission fault the moment any menu page opened: the unit's runtime state bytes (sentinel, latch and friends) lived in the read-only code cave. The fix moves all state into a dedicated data window that boot reloads from the image on every power-up and that EL0 may write (the row-events table sits in a fixed read-only cave sub-window), with build-time guards against regression. The full-system QEMU regression passed all three legs: the crash-baseline image reproduced the exception banner field-for-field as a positive control, the fixed image ran with zero banners and the expected sentinel/magic bytes, and a second menu open was idempotent (artifacts: `build/t14/vrfix-reg/` on the z8-qemu side).
- **Emulation: value rendering verified (2026-11-09).** The first manual emulator check found the original design (the string-id path, whose value child truncates high string ids) rendering wrongly: a text-style value when unselected and an hourglass icon when highlighted. The documented fallback was adopted: the value now renders through the stock boolean widget path (the attenuator row's own path, reusing the camera's localized On/Off texts; two movz immediates and two call targets changed). Re-acceptance passed: the value shows the same On/Off switch style as stock boolean rows, toggles immediately in step with the stored byte, and the toggle and storage behaviour is unchanged. Recipes were refrozen a fifth time (the fifteen combinations without this group are byte-identical).
- **Camera acceptance: menu behaviour fully verified.** Saving the setting, switching between different menu banks, the power-cycle default and the reset-menu behaviour all behave exactly like the shipped H.265 tier feature. One issue is open: video recorded with the feature on does not play rotated on a computer; the cause is under investigation (the earlier "rotation direction" check is void — rotation itself is not taking effect, so direction does not arise). The gravity-vector-to-pose axis assignment remains a documented hypothesis and is one candidate cause of the open issue, not a confirmed one (if the two portrait directions turn out mirrored, the correction is patch constant bytes only, with no code change). The per-bank memory across menu-bank switches is also emulator-verified.

### Known issues

See [known issues](known-issues.md) for the power-cycle default, session persistence, the unverified N-RAW third-party compatibility and other limits.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
