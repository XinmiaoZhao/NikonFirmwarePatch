# 照片裁切比例 / Still crop ratios

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features still-photo-tools` 在照片的“选择图像区域”中增加 **4:3、2.39:1 和 65:24（XPan）** 三种画幅，照片拍摄菜单、i 菜单和指定的 Fn 键都可以选择。取景按所选比例显示，JPEG／HEIF 与 NEF 都按比例裁切。同一组还包含 [SDR HEIF](sdr-heif.md) 和[像素位移合成](pixelshift.md)。

### 支持范围

新画幅列在原厂 FX、DX、1:1、16:9 之间，顺序为 FX、DX、4:3、1:1、16:9、2.39:1、65:24。各画幅的图像尺寸如下：

| 菜单项 | L | M | S |
|---|---|---|---|
| 4:3 (32×24) | 7344×5504（40.4 M） | 5504×4128（22.7 M） | 3664×2752（10.1 M） |
| 2.39:1 (36×15) | 8256×3456（28.5 M） | 6192×2592（16.0 M） | 4128×1728（7.1 M） |
| 65:24 (36×13) | 8256×3048（25.2 M） | 6192×2280（14.1 M） | 4128×1520（6.3 M） |

2.39:1 和 65:24 使用 FX 全宽，4:3 使用全高。三个画幅只用于普通照片拍摄。

### 使用步骤

1. 在照片拍摄菜单打开“图像区域 › 选择图像区域”，选择 4:3、2.39:1 或 65:24 并按 OK。取景画面随即显示裁切后的范围。
2. 也可以使用 i 菜单中的“选择图像区域”。若把“选择图像区域”分配给 Fn 键，按住该键会出现原厂的横向画幅选择条，转动拨盘即可切换，松开后选择条收起。两种方式都列出同样的七项。
3. 在“图像尺寸设定”中按需选择 L／M／S，然后按通常方式拍摄。
4. 用完后改回 FX，尤其是在刷入其他固件之前（见下文）。

### 输出与显示

JPEG、HEIF 和 NEF 都写出裁切后的尺寸。NEF 与原厂 DX、1:1、16:9 一样做实际裁切，不是只记录裁切标记。菜单、取景和回放使用新增的画幅图标。

### 已知问题

- **刷入其他固件之前，先把图像区域改回 FX。** 原厂固件和不含本组的补丁包没有新画幅的参数，若相机保存的是新画幅，取景可能反复重试或保持黑屏。
- **高速画面捕捉中不能用新增画幅。** C15/C30 只能选 FX 和 DX；C60/C120 与原厂一样不能选择图像区域。
- **软件显示的裁切名称可能不对。** 文件的实际像素尺寸正确，但元数据的裁切代码借用了原厂已有的值：exiftool 把 4:3 显示为“5:4 Crop”，2.39:1 显示为“3:2 Crop”，65:24 显示为“2.8x Movie Crop”。请以图像尺寸为准。

## English

### Overview

`--features still-photo-tools` adds three photo image areas to Choose image area: **4:3, 2.39:1 and 65:24 (XPan)**, selectable from the photo shooting menu, the i menu and an assigned Fn button. Live view shows the selected crop, and JPEG/HEIF and NEF files are all cropped. The same group installs [SDR HEIF](sdr-heif.md) and [pixel-shift merge](pixelshift.md).

### Supported modes

The new areas are listed among the stock FX, DX, 1:1 and 16:9 in the order FX, DX, 4:3, 1:1, 16:9, 2.39:1, 65:24. Image sizes:

| Menu entry | L | M | S |
|---|---|---|---|
| 4:3 (32×24) | 7344×5504 (40.4 M) | 5504×4128 (22.7 M) | 3664×2752 (10.1 M) |
| 2.39:1 (36×15) | 8256×3456 (28.5 M) | 6192×2592 (16.0 M) | 4128×1728 (7.1 M) |
| 65:24 (36×13) | 8256×3048 (25.2 M) | 6192×2280 (14.1 M) | 4128×1520 (6.3 M) |

2.39:1 and 65:24 use the full FX width; 4:3 uses the full height. The three areas apply to ordinary photography only.

### Steps

1. In the photo shooting menu, open Image area › Choose image area, select 4:3, 2.39:1 or 65:24 and press OK. Live view then shows the cropped frame.
2. Choose image area in the i menu works too. If Choose image area is assigned to an Fn button, holding the button shows the stock image-area strip; turn the dial to change the area, and release the button to close the strip. Both list the same seven areas.
3. Choose L/M/S in Image size settings if needed, and shoot normally.
4. Return to FX afterwards, and always before installing other firmware (see below).

### Files and display

JPEG, HEIF and NEF files are written at the cropped size. Like the stock DX, 1:1 and 16:9 areas, NEFs are actually cropped rather than only tagged. The menus, live view and playback use added image-area icons.

### Known issues

- **Return the image area to FX before installing other firmware.** Stock firmware and packages without this group lack the parameters for the new areas. If the camera has a new area saved, live view can keep retrying or stay black.
- **The added areas are not available in high-speed frame capture.** C15/C30 offer only FX and DX; at C60/C120 Choose image area is unavailable, as on the stock camera.
- **Software may show the wrong crop name.** Pixel dimensions are correct, but the metadata crop code reuses an existing stock value: exiftool shows 4:3 as "5:4 Crop", 2.39:1 as "3:2 Crop" and 65:24 as "2.8x Movie Crop". Go by the image dimensions.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
