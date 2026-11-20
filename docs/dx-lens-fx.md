# DX 镜头使用 FX 影像区域 / FX image area with DX lenses

[简体中文](#简体中文) · [English](#english)

## 简体中文

> 本节中文由 AI 根据英文原文翻译。

### 功能

使用 `--features photo-tools` 时，Z8 安装电子 DX 镜头（Z 卡口 DX 镜头，或经 FTZ／FTZ II 转接的 F 卡口 DX 镜头）后也可以使用 FX（36×24）影像区域，相当于 D850 的“自动 DX 裁切：关闭”。对应[问题 #45](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/45)。

**状态：已在 Z8 机身上测试（固件 03.12.d2，包含全部 36 处修改）。**

### 行为

- 相机使用您选择的影像区域。安装 DX 镜头时不再自动切换到 DX；需要 DX 时请手动选择。没有开关选项。
- 安装 DX 镜头时，以下项目不再变灰：
  - 照片拍摄菜单 › 影像区域 › 选择影像区域（FX、DX；1:1 和 16:9 仍按各自的规则）
  - 照片拍摄菜单 › 延时视频 › 选择影像区域
  - 视频拍摄菜单 › 影像区域 › 选择影像区域
  - 视频拍摄菜单 › 画面尺寸／帧频：8K UHD（H.265）、FX N-RAW 和 FX ProRes RAW HQ 尺寸
  - “选择影像区域”按键功能（自定义控制、i 菜单），以及按住按键并转动拨盘的操作
  - PTP：联机拍摄时可设置照片影像区域、视频影像区域和视频画面尺寸
- 不变：安装 DX 镜头时“图像除尘参照照片”仍不可用；EXIF 和 PTP LensType 属性中镜头仍报告为 DX。
- FX 下的预期现象：四角变暗。机内暗角控制和失真控制使用镜头的 DX 数据，因此 JPEG／HEIF 的四角和实时取景可能异常；RAW 数据不受影响。

### 实现（C3.11 EG 地址）

- 镜头状态为两个值：镜头类型 `0x04002d0c`（1 为 Z 卡口，3 为经 FTZ 的 F 卡口）和镜头覆盖 FX `0x04002d13`（0 表示 DX）。PTP LensType 生成函数 `0x4083b1f0` 根据 `0x04002d13 == 0` 设置 DX 位。
- 用户设置（照片 `0x07000603`、视频 `0x07001201`、延时视频 `0x0600052b`）从不被改写。实际影像区域由共用的解析函数 `0x40ed90d0`（24 处调用）计算，安装 DX 镜头时在 `0x40ed91b4..c4` 返回 DX，其视频分支（非 RAW 的 120p／100p 及慢动作）在 `0x40ed9168..74` 另有一处同样的判断，返回 DX 型区域 7；视频画面尺寸辅助函数 `0x40ed8f74`（26 处调用）在 `0x40ed8f9c` 做同样的判断。
- 菜单：表 `0x42dedf78` 按界面项目列出使其变灰的条件；条件 #38（`0x403a3ac4`）为“已安装 DX 镜头”。

| 修改 | 内容 |
|---|---|
| `0x40ed91c0` | `cbnz w9` → `b 0x40ed91cc`：解析函数保留所选区域 |
| `0x40ed9174` | `cbnz w9` → `b 0x40ed9140`：解析函数的视频分支（120p／100p 及慢动作）不再因 DX 镜头使用 DX |
| `0x40ed8f9c` | `and w8,w9,w8` → `mov w8,wzr`：视频辅助函数按 FX 镜头处理 |
| `0x4067c478`、`0x405e0560` | 条件跳转改为无条件跳转：影像区域按键操作 |
| `0x4081c728`、`0x4081cde4`、`0x4083ffd4` | `cbz` → `nop`：PTP 照片影像区域、视频影像区域、视频画面尺寸 |
| 界面项目 25、430、107、459 | 将条件 38 替换为同一列表中已有的条件（7 或 97） |
| 界面项目 82、109–131 | 列表计数 1 → 0（其唯一条件为 38） |

条件 #38 本身未修改，因此项目 181（图像除尘参照照片）仍受其限制。共 36 处固定字节修改，见 `z8dxlens/patcher.py`，无新增代码。

### 构建

与本分支其余部分相同：将本分支文件覆盖到解压后的 v0.4.0 工具包，运行 `python tools/build_precapture_unit.py`，再以默认预编译模式使用 `--features photo-tools`（或包含它的任意组合）构建。

## English

### Overview

With `--features photo-tools`, a Z8 with an electronic DX lens attached (Z-mount DX, or F-mount DX on the FTZ / FTZ II) can use the FX (36×24) image area, as with "Auto DX crop: Off" on the D850. Requested in [issue #45](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/45).

**Status: tested on a Z8 (firmware 03.12.d2, all 36 edits).**

### Behaviour

- The camera uses the image area you choose. It no longer switches to DX by itself when a DX lens is mounted; select DX when you want it. There is no on/off option.
- With a DX lens, these are no longer greyed out:
  - Photo shooting menu › Image area › Choose image area (FX, DX; 1:1 and 16:9 keep their own rules)
  - Photo shooting menu › Time-lapse movie › Choose image area
  - Video recording menu › Image area › Choose image area
  - Video recording menu › Frame size/frame rate: 8K UHD (H.265), FX N-RAW and FX ProRes RAW HQ sizes
  - The "Choose image area" button function (custom controls, i menu) and the hold-button-and-turn-dial route
  - PTP: photo image area, video image area and movie frame size can be set while tethered
- Unchanged: Image Dust Off ref photo stays unavailable with a DX lens, and the lens is still reported as DX in EXIF and in the PTP LensType property.
- Expected at FX: dark corners. In-camera vignette control and distortion control use the lens's DX data, so JPEG/HEIF corners and live view may look odd; RAW data is unaffected.

### How it works (C3.11 EG addresses)

- The lens state is two values: lens kind `0x04002d0c` (1 Z-mount, 3 F-mount on the FTZ) and lens covers FX `0x04002d13` (0 = DX). The PTP LensType builder `0x4083b1f0` sets its DX bit from `0x04002d13 == 0`.
- Your settings (`0x07000603` photo, `0x07001201` video, `0x0600052b` time-lapse) are never overwritten. The effective area comes from the shared resolver `0x40ed90d0` (24 callers), which returns DX at `0x40ed91b4..c4` for a DX lens, and whose video branch (non-RAW 120p/100p and slow motion) has a second copy of the test at `0x40ed9168..74` that returns the DX-type area 7; the video frame-size helper `0x40ed8f74` (26 callers) applies the same test at `0x40ed8f9c`.
- Menus: table `0x42dedf78` lists, for each UI item, the predicates that grey it out; predicate #38 (`0x403a3ac4`) is "DX lens attached".

| Edit | Change |
|---|---|
| `0x40ed91c0` | `cbnz w9` → `b 0x40ed91cc`: the resolver keeps the chosen area |
| `0x40ed9174` | `cbnz w9` → `b 0x40ed9140`: the resolver's video branch (120p/100p and slow motion) no longer uses DX for a DX lens |
| `0x40ed8f9c` | `and w8,w9,w8` → `mov w8,wzr`: the video helper treats the lens as FX |
| `0x4067c478`, `0x405e0560` | conditional → unconditional branch: image-area button route |
| `0x4081c728`, `0x4081cde4`, `0x4083ffd4` | `cbz` → `nop`: PTP photo image area, video image area, movie frame size |
| UI items 25, 430, 107, 459 | predicate 38 replaced by one already in the same list (7 or 97) |
| UI items 82, 109–131 | list count 1 → 0 (their only predicate is 38) |

Predicate #38 itself is unchanged, so item 181 (Image Dust Off ref photo) keeps it. 36 fixed byte edits in total, in `z8dxlens/patcher.py`; no new code.

### Build

Same as the rest of this branch: copy the branch over an extracted v0.4.0 toolkit, run `python tools/build_precapture_unit.py`, then build with `--features photo-tools` (or any combination that includes it) in the default prebuilt mode.
