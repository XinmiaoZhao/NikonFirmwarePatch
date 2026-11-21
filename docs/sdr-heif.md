# SDR HEIF / SDR HEIF

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features still-photo-tools` 让普通照片在 SDR 色调下也能保存为 10 位 HEIF。原厂只有选择 HLG 才能拍 HEIF；本功能为“色调模式”的 SDR 行增加文件格式选择 **JPEG／HEIF**。同一组还包含[照片裁切比例](photo-crop.md)和[像素位移合成](pixelshift.md)。

### 支持范围

- 普通单张拍摄与连拍。画质与尺寸选项和原厂 HLG 的 HEIF 相同，包括 RAW+HEIF；色彩空间可选 sRGB 或 Adobe RGB。
- 间隔拍摄和照片拍摄菜单的延时视频可以在 SDR HEIF 下使用。
- 在 C15、C30、C60、C120 中，SDR 压缩照片显示为 JPEG，HEIF 禁用。回到普通释放模式会恢复当前库保存的偏好。C15/C30 的 RAW 输出见[预拍指南](raw-precapture.md)。

### 使用步骤

1. 在照片拍摄菜单打开“色调模式”。
2. 光标停在 SDR 行，按右键，或点按画面底部的“文件格式”，打开“SDR文件格式”。
3. 选择 **HEIF** 并按 OK。照片拍摄菜单的“色调模式”随即显示 **SDR-H**；选择 JPEG 时显示 **SDR-J**。
4. 按通常方式拍摄。改回 JPEG 即恢复原厂 SDR JPEG。

### 输出与显示

- 文件扩展名为 `.HIF`，主图为 10 位 HEVC（Main 10），L 尺寸为 8256×5504。显影与同场 SDR JPEG 相同，像素按 BT.601 矩阵编码并如实标注。
- 色彩空间沿用相机的 sRGB／Adobe RGB 设置，并写入对应标签。
- 实拍的 sRGB 与 Adobe RGB HIF 均能在 macOS 预览、Windows 11 照片、iPhone 照片和小米相册中打开，颜色与同场 JPEG 一致，见下文“兼容性”。
- 安装本组后，Adobe RGB 的 SDR JPEG（含 RAW+JPEG）嵌入 Nikon Adobe RGB ICC。原厂 JPEG 只写色彩空间标记，macOS 预览、小米相册等软件会把它当作 sRGB 显示；嵌入 ICC 后按 Adobe RGB 显示。sRGB JPEG 不变。
- SDR HEIF 下的延时视频固定为 H.265 10 位，色调为 SDR。

### 兼容性

已确认能打开、颜色与同场 JPEG 一致的软件：macOS 预览、iPhone 照片、Windows 11 照片和小米 13 Ultra 相册（澎湃 OS 3）。小米相册可以直接打开 `.HIF` 扩展名。其他软件、设备和系统版本不保证能正常识别，遇到问题可以改用 JPEG。

各平台读取 HEIF 的方式不同：有的读颜色标签，有的忽略标签；有的对文件内条目的顺序或缩略图有要求。为了让同一个文件在这几个平台上都正确显示，SDR HEIF 的写法相对原厂 HLG 做了以下调整，供其他开发者参考：

| 调整 | 原因 |
|---|---|
| 像素按 BT.601 矩阵编码（与 JPEG 相同），`nclx` 与 HEVC VUI 如实标 601。原厂 HLG 的写入路径按 BT.2020 编码 | 小米相册不读矩阵标签，一律按 BT.601 解码。按 601 编码后，读标签的 macOS、iPhone、Windows 与不读标签的小米得到相同结果 |
| `ipma` 的条目顺序改为“瓦片、主图网格、缩略图”。原厂顺序是缩略图、主图、瓦片 | 小米相册要求 `ipma` 从瓦片开始、主图紧随其后，否则提示格式不支持。`iinf`、`iloc` 的顺序没有影响 |
| Adobe RGB 的 HIF 使用原厂的 Nikon Adobe RGB ICC（`colr` 类型 `rICC`）。160×120 的 JPEG 小图条目保留但设为隐藏，并去掉它的 `thmb` 引用；相机回放时改按条目编号读取这张小图 | Windows 11 照片遇到带 ICC 的 HIF，只要主图还有 JPEG 的 `thmb` 小图，就只显示小图、打不开主图 |
| Adobe RGB 的 SDR JPEG 嵌入同一份 Nikon ICC | 原厂 JPEG 只在 Exif 中标注色彩空间，macOS 预览、小米相册会按 sRGB 显示 |
| 间隔拍摄和延时视频的帧使用原厂 SDR 视频的 601→709 转换，与视频的 709 标签一致 | 避免播放器按错误矩阵解码而偏色 |

这些调整只用于 SDR HEIF；选择 HLG 时，HIF 保持原厂写法。

### 已知问题

- **选择 SDR HEIF 后，部分选项会变化。** 与原厂 HLG 一样，HDR 叠加和多重曝光禁用，延时视频固定为 H.265 10 位。改回 JPEG 即恢复。
- **C15 至 C120 不能拍 HEIF。** 进入这些档位后压缩照片临时改用 JPEG，HEIF 禁用；回到普通释放模式会恢复当前菜单库保存的偏好。
- **HEIF 兼容性因软件而异。** 上文“兼容性”列出的平台已确认；其他软件、设备和系统版本不保证能正常识别。

## English

### Overview

`--features still-photo-tools` lets ordinary photos be saved as 10-bit HEIF in the SDR tone mode. Stock firmware records HEIF only with HLG. This feature adds a **JPEG/HEIF** file format choice to the SDR row of Tone mode. The same group installs the [still crop ratios](photo-crop.md) and [pixel-shift merge](pixelshift.md).

### Supported modes

- Ordinary single shots and continuous shooting. Quality and size choices are those of stock HLG HEIF, including RAW+HEIF; the colour space can be sRGB or Adobe RGB.
- Interval timer shooting and the photo menu's time-lapse movie work with SDR HEIF.
- C15, C30, C60 and C120 show JPEG for compressed SDR photos and disable HEIF. Returning to ordinary shooting restores the active bank’s saved preference. See [RAW pre-capture](raw-precapture.md) for C15/C30 NEF output.

### Steps

1. In the photo shooting menu, open Tone mode.
2. With the cursor on SDR, press right or tap File format at the bottom of the screen to open SDR file format.
3. Select **HEIF** and press OK. Tone mode in the photo shooting menu then reads **SDR-H**; with JPEG it reads **SDR-J**.
4. Shoot normally. Select JPEG again for stock SDR JPEG.

### Files and display

- Files use the `.HIF` extension. The main image is 10-bit HEVC (Main 10), 8256×5504 at size L. Development matches a same-scene SDR JPEG; pixels are coded with the BT.601 matrix and labelled accordingly.
- The colour space follows the camera's sRGB/Adobe RGB setting and is tagged accordingly.
- sRGB and Adobe RGB HIFs shot on the camera open in macOS Preview, Windows 11 Photos, iPhone Photos and the Xiaomi gallery, with colours matching the same-scene JPEG; see Compatibility below.
- With this group installed, Adobe RGB SDR JPEGs (including RAW+JPEG) embed the Nikon Adobe RGB ICC profile. Stock JPEGs carry only a colour-space tag, which apps such as macOS Preview and the Xiaomi gallery display as sRGB; with the profile they display Adobe RGB. sRGB JPEGs are unchanged.
- Time-lapse movies under SDR HEIF are fixed to H.265 10-bit with SDR tone.

### Compatibility

Confirmed to open with colours matching the same-scene JPEG: macOS Preview, iPhone Photos, Windows 11 Photos and the Xiaomi 13 Ultra gallery (HyperOS 3). The Xiaomi gallery opens the `.HIF` extension directly. Other applications, devices and system versions may not read the files correctly; use JPEG if needed.

These platforms read HEIF differently: some follow the colour labels and some ignore them, and some depend on the order of items or on the thumbnails. So that one file displays correctly on all of them, SDR HEIF is written with the following changes from the stock HLG writer, listed here for other developers:

| Change | Reason |
|---|---|
| Pixels are coded with the BT.601 matrix, as in JPEG, and `nclx` and the HEVC VUI say 601. The stock HLG path codes BT.2020 | The Xiaomi gallery ignores matrix labels and always decodes BT.601. With 601 coding, label-reading macOS, iPhone and Windows and the label-ignoring Xiaomi gallery agree |
| `ipma` entries are ordered tiles, primary grid, thumbnails. The stock order is thumbnails, primary, tiles | The Xiaomi gallery requires `ipma` to start with the tiles followed by the primary item and otherwise reports an unsupported format. The `iinf` and `iloc` order does not matter |
| Adobe RGB HIFs use the factory Nikon Adobe RGB ICC (`colr` type `rICC`). The 160×120 JPEG thumbnail item stays but is hidden and loses its `thmb` reference; camera playback finds it by item number | Windows 11 Photos shows only the thumbnail, not the primary image, of an ICC-tagged HIF whose primary still has a JPEG `thmb` |
| Adobe RGB SDR JPEGs embed the same Nikon ICC | Stock JPEGs mark the colour space only in Exif, which macOS Preview and the Xiaomi gallery display as sRGB |
| Interval and time-lapse movie frames use the stock SDR movie 601→709 conversion, matching the movies' 709 labels | Players then decode them with the matching matrix |

These changes apply to SDR HEIF only; with HLG selected, HIFs keep the stock layout.

### Known issues

- **Some options change with SDR HEIF.** As with stock HLG, HDR overlay and multiple exposure are disabled, and time-lapse movies are fixed to H.265 10-bit. Selecting JPEG restores them.
- **C15 through C120 cannot shoot HEIF.** These modes use JPEG for compressed photos and disable HEIF; an ordinary release mode restores the active bank’s saved preference.
- **HEIF support varies by application.** The platforms under Compatibility are confirmed; other applications, devices and system versions may not read the files correctly.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
