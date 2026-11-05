# 四组安装选项 / Four feature groups

| 构建选项 | 安装内容 | 相机中的主要入口 |
|---|---|---|
| `framing` | 3:2 开放门、N-RAW 四档画质、反挤压显示 | 画面尺寸／帧频、N-RAW 画质、反挤压 |
| `video-quality` | ProRes 四档与 HQ 星标、H.265 五档码率及对应星标 | ProRes 画质、H.265 画质 |
| `log-colour` | N-Log、S-Log3、Log3G10 选择及相关显示／标签 | Log 设定 |
| `photo-tools` | C15/C30 RAW 预拍、像素偏移合成 | 普通画质、RAW 记录、像素变化合成 |

每组可以独立从原厂 C 3.11 构建，也可一次选择多组，共 15 种非空组合。N-RAW 画质与开放门共同使用码率及剩余时间逻辑，保留在同一组。反挤压可在菜单关闭；RAW 预拍与像素偏移使用各自入口。

构建选项决定安装哪些功能，机内菜单决定每项功能如何使用。先选择所需组，再从原厂包一次构建完整固件；不要向已经修改的固件继续叠加。

旧版选项 `prores / precapture / pixelshift / opengate-nraw` 仅用于对应的旧版源码。当前 CLI 会明确拒绝旧名称。复现旧包时使用该版本的源码或完整工具包。

功能指南：[开放门](opengate-nraw.md)、[反挤压](anamorphic.md)、[ProRes](prores.md)、[H.265](h265.md)、[Log](log-colour.md)、[RAW 预拍](raw-precapture.md)、[像素偏移](pixelshift.md)。

## English

The four installation choices are `framing`, `video-quality`, `log-colour` and `photo-tools`. Each builds independently from the original C 3.11 image; multiple groups are composed in one build. There are 15 nonempty combinations. Open gate stays paired with N-RAW quality, while desqueeze can be disabled in the camera. Pre-capture and pixel-shift keep separate controls.

Build-time choices install features; camera settings select their behavior. Legacy option names belong to older source/toolkit versions and are rejected by the current CLI.
