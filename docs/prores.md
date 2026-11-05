# ProRes 画质 / ProRes quality

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features video-quality` 提供 **HQ／422（Standard）／LT／Proxy** 四档 ProRes 画质，并按视频拍摄菜单库分别保存。与 H.265 品质同组安装，也可与其他组组合。HQ 的尺寸／帧频图标带星，422／LT／Proxy 无星；组合包实拍核对了 HQ 和 LT 的 MOV 编码；各菜单及回放页的星标刷新仍需逐项观察。

### 支持范围

沿用原 ProRes 422 路径的画幅和帧率范围；不新增 ProRes RAW 或 3:2。

### 使用步骤

1. 在视频文件类型中选择 ProRes 422。
2. 在视频画质菜单选择 HQ、422、LT 或 Proxy。
3. 如需不同菜单库使用不同档位，切换到相应菜单库后分别设置。

### 输出与显示

输出为 MOV，四档的编码标识依次是 `apch`、`apcn`、`apcs`、`apco`。回放档名和剩余录制时间随所选档位对应；剩余时间是估算，实际文件大小随场景变化。

### 已知问题

- HQ 使用星标，422／LT／Proxy 共用无星图标；部分帮助文字仍显示 HQ。确认档位应看画质菜单或 MOV 编码标识。
- 重设视频拍摄菜单不会重设新增档位，重设后可在画质菜单重新选择。

## English

### Overview

`--features video-quality` adds **HQ/Standard/LT/Proxy** ProRes grades, stored separately for each movie shooting bank. It is bundled with H.265 quality. HQ now carries a frame-size star; 422/LT/Proxy do not. Camera recordings confirm HQ and LT encoding. Individual menu and playback star transitions still need direct observation.

### Supported modes

Uses the stock ProRes 422 dimensions and frame rates. It does not add ProRes RAW or 3:2.

### Steps

1. Select ProRes 422 as the movie file type.
2. Choose HQ, 422 (Standard), LT or Proxy in movie quality.
3. To use different grades in different banks, select each bank and set its grade.

### Files and display

Output is MOV. The four codec identifiers are `apch`, `apcn`, `apcs` and `apco`, respectively. Playback labels and remaining-time estimates correspond to the grade. Remaining time is an estimate; file sizes vary with scene content.

### Known issues

- HQ uses the star; 422/LT/Proxy share the plain icon. Some help text still says HQ. Check the quality menu or MOV codec identifier.
- Resetting the movie menu does not reset the added grade. Select the desired grade again in movie quality.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
