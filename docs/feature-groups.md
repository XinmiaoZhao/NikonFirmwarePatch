# 四组安装选项 / Four feature groups

[简体中文](#简体中文) · [English](#english)

## 简体中文

| 构建选项 | 安装内容 | 相机中的主要入口 |
|---|---|---|
| `video-recording` | N-RAW 12位 3:2（8.3K 30／25／24p，4.1K 120p 至 24p）、N-RAW 四档画质、反挤压显示、ProRes 四档与 HQ 星标、H.265 五档码率 | 视频文件类型、画面尺寸／帧频、视频品质、变形镜头还原显示 |
| `log-colour` | N-Log、S-Log3、Log3G10 选择及相关显示与标签 | Log 设定 |
| `still-photo-tools` | SDR HEIF、4:3／2.39:1／65:24 照片裁切、像素位移合成 | 色调模式 › SDR文件格式、选择图像区域、像素变化合成 |
| `raw-precapture` | C15／C30 RAW 预拍（FX／DX，HE／HE★，画质沿用普通菜单）；释放模式随照片拍摄菜单库切换 | 释放模式、图像品质、RAW录制 |

每组都可以单独从原厂 C 3.11 构建，也可一次选择多组，共 15 种非空组合。构建选项决定安装哪些功能，机内菜单决定每项功能如何使用。先选好所需的组，再从原厂包一次构建完整固件；不要在已经修改的固件上继续叠加。

照片菜单、i 菜单和指定的 Fn 键均可选择七种画幅。2.39:1 在各画质使用同一套几何参数。C15 至 C120 会临时切到 JPEG 并禁用 HEIF，退出后恢复当前菜单库的偏好。选择无损 RAW 时，C15/C30 显示高效率★；C15/C30 支持 RAW 预拍。像素位移合成需要无损压缩的源文件。

### 与 v0.4.0 的对应

| v0.4.0 | v0.5.0 |
|---|---|
| `framing`、`video-quality` | 合并为 `video-recording`，并新增 4.1K 3:2 |
| `log-colour` | `log-colour`（不变） |
| `photo-tools` | 拆为 `still-photo-tools`（像素位移合成，新增 SDR HEIF 与照片裁切）和 `raw-precapture`（预拍） |

v0.4.0 及更早的组名不能用于 v0.5.0，当前 CLI 会拒绝，不会自动换成新组。复现旧包时使用对应版本的源码或工具包。

功能指南：[N-RAW 3:2](opengate-nraw.md)、[反挤压](anamorphic.md)、[ProRes](prores.md)、[H.265](h265.md)、[Log](log-colour.md)、[SDR HEIF](sdr-heif.md)、[照片裁切](photo-crop.md)、[像素位移](pixelshift.md)、[RAW 预拍](raw-precapture.md)、[释放模式随菜单库切换](release-mode-banks.md)。

## English

| Build option | Installs | Main camera entries |
|---|---|---|
| `video-recording` | N-RAW 12-bit 3:2 (8.3K 30/25/24p, 4.1K 120p to 24p), four N-RAW tiers, anamorphic desqueeze, four ProRes grades with an HQ star, five H.265 bitrates | Video file type, Frame size/frame rate, Video quality, Anamorphic desqueeze |
| `log-colour` | N-Log, S-Log3 and Log3G10 with matching display and labels | Log settings |
| `still-photo-tools` | SDR HEIF, 4:3 / 2.39:1 / 65:24 still crops, pixel-shift merge | Tone mode › SDR file format, Choose image area, Pixel shift merge |
| `raw-precapture` | C15/C30 RAW pre-capture (FX/DX, HE/HE★, ordinary quality menu); release mode per photo shooting menu bank | Release mode, Image quality, RAW recording |

Each group builds on its own from the original C 3.11 image, and several groups can be combined in one build: 15 nonempty combinations. Build options decide which features are installed; camera menus decide how each one is used. Choose the groups first and build the complete firmware once from the original package; do not layer patches onto modified firmware.

The photo menu, i menu and assigned Fn button offer the same seven image areas. The 2.39:1 crop uses the same geometry at every quality. C15 through C120 select JPEG and disable HEIF until an ordinary release mode restores the active bank’s preference. Lossless RAW is shown as HE★ at C15 and C30. C15 and C30 support RAW pre-capture. Pixel-shift merge requires losslessly compressed source groups.

### Mapping from v0.4.0

| v0.4.0 | v0.5.0 |
|---|---|
| `framing`, `video-quality` | merged into `video-recording`, with 4.1K 3:2 added |
| `log-colour` | `log-colour` (unchanged) |
| `photo-tools` | split into `still-photo-tools` (pixel-shift merge plus the new SDR HEIF and still crops) and `raw-precapture` |

Group names from v0.4.0 and earlier are not accepted by v0.5.0; the CLI rejects them rather than substituting new groups. Use the matching release's source or toolkit to reproduce an older package.

Guides: [N-RAW 3:2](opengate-nraw.md), [desqueeze](anamorphic.md), [ProRes](prores.md), [H.265](h265.md), [Log](log-colour.md), [SDR HEIF](sdr-heif.md), [still crops](photo-crop.md), [pixel shift](pixelshift.md), [RAW pre-capture](raw-precapture.md), [release mode per bank](release-mode-banks.md).
