# 记录视频方向 / Record video orientation

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features video-orientation` 是开发分支新增的第五个构建组，尚未包含在 v0.4.0 发布工具包中。它在视频拍摄菜单中新增一行**“记录视频方向”**（英文 Record video orientation，日文 動画の縦横位置情報の記録；标题覆盖相机全部 36 个语言槽位），插入在“图像区域”一行之前。取值为行内**开／关**切换，直接复用原厂的开／关文案。设置按视频拍摄菜单库 A–D 分别保存，**默认开**。

开启时，相机锁定持机姿态（由姿态传感器的重力向量判定）：两个方向的竖拍与 180° 倒置会在录像容器中写入 QuickTime **tkhd 显示矩阵**（旋转元数据）；横拍不写入旋转矩阵，与原厂一致。写入经由相机唯一的视频封装路径，覆盖相机录制的全部格式——MP4（H.264）、H.265、ProRes 422 HQ（MOV；视频品质组的其余 ProRes 档位走同一录制路径）、ProRes RAW 与 N-RAW。姿态在同一段录像的全部容器构建（含断电恢复快照、同录代理、终稿）中保持一致：每个写者在自己的文件启动时采样一次姿态，终稿与恢复快照携带同一标记；锁存在录像收尾时清除，回放或传送时对文件的分析不会复用过期姿态。采样时刻随视频格式不同，与分辨率无关：H.265 10-bit、ProRes 422 HQ 与 RAW 家族（ProRes RAW、N-RAW）在开录时刻采样；H.264 档位与 H.265 8-bit 档位（不可切换色调模式的格式）由停录后启动的交付写者写入，在停录时刻采样（见[已知问题](known-issues.md)）。

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

- **离线检查全部通过**：全量单元测试；非空组合 31 种全部配方冻结（15 份无照片工具组合真实构建逐字节复验，16 份含照片工具组合经混合装配与结构审计冻结）；`verify.py` 对单选与“四视频组＋视频方向”产物独立核验通过。
- **仿真全部通过**：全系统引导零异常横幅，首次开页武装默认状态并具幂等性；行值以原厂布尔开关样式渲染，翻值即时生效且与存储字节同轨；菜单库切换时取值随库双向搬运。
- **实机（菜单）全部通过**：保存、菜单库切换、断电回默认开与菜单重设，与已发布的 H.265 档位功能完全一致。
- **实机（录制）全部通过**：相机录制的全部格式逐握持验证——H.265 10-bit 与 8-bit MOV、H.264 8-bit MP4/MOV、N-RAW（NEV 与同录代理 MP4）、ProRes RAW 10-bit 与 12-bit（含同录代理）；正拍不标记、倒置 180°、两向竖拍各得相反的 90°，全部文件在电脑上以 ffprobe 核验。

### 已知问题

断电回到默认“开”、会话内持久、N-RAW 第三方工具兼容未知等限制见[已知问题](known-issues.md)。

## English

### Overview

`--features video-orientation` is a fifth build group on the development branch; it is not part of the v0.4.0 release toolkit. It adds one row, **Record video orientation** (Japanese 動画の縦横位置情報の記録; the title ships in all 36 camera language slots), to the video shooting menu, directly before **Image area**. The row is an inline **On/Off** toggle reusing the camera's own localized On/Off texts. The setting is stored per movie shooting bank A–D and **defaults to On**.

When On, the camera locks its grip orientation (classified from the orientation sensor's gravity vector): both portrait directions and 180° upside-down write a QuickTime **tkhd display matrix** (rotation metadata) into the movie container; landscape writes no rotation matrix, exactly like stock. The write goes through the camera's single movie-muxing path and covers every format the camera records: MP4 (H.264), H.265, ProRes 422 HQ (MOV; the video-quality group's other ProRes grades use the same recording path), ProRes RAW and N-RAW. Every container build of one clip -- crash-recovery snapshots, a simultaneous proxy writer and the final build -- carries the same mark, because each writer samples the pose once when its own file starts; the latch clears when the clip ends, so playback- or transfer-side analysis can never reuse a stale pose. The sampling moment depends on the video format, not the resolution: H.265 10-bit, ProRes 422 HQ and the RAW family (ProRes RAW, N-RAW) sample at recording start; the H.264 modes and the H.265 8-bit modes (the formats without tone-mode switching) are written by a delivery writer that starts right after the recording stops and sample at that moment (see [known issues](known-issues.md)).

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

- **Offline checks pass**: the full unit-test suite; all 31 five-group recipes frozen (the 15 without photo-tools rebuilt byte-exactly; the 16 photo-tools combinations via hybrid assembly with a structural audit); `verify.py` independently passes the single-group and four-video-groups-plus-orientation outputs.
- **Emulation passes**: full-system boot with zero exception banners; the first menu open arms the default state and a second open changes nothing; the value renders in the stock On/Off switch style and toggles immediately in step with the stored byte; the value follows menu-bank switches in both directions.
- **Camera (menu) passes**: saving, menu-bank switching, the power-cycle default and the reset-menu behaviour all match the shipped H.265 tier feature exactly.
- **Camera (recording) passes**: every format the camera records is verified per grip -- H.265 10-bit and 8-bit MOV, H.264 8-bit MP4/MOV, N-RAW (the NEV file and its simultaneous proxy MP4) and ProRes RAW in both 10-bit and 12-bit with proxies; landscape stays unmarked, upside-down gets 180 degrees and the two portrait grips get opposite 90-degree marks, with every file checked on a computer through ffprobe.

### Known issues

See [known issues](known-issues.md) for the power-cycle default, session persistence, the unverified N-RAW third-party compatibility and other limits.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
