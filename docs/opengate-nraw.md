# N-RAW 3:2 与 N-RAW 四档 / N-RAW 3:2 and N-RAW tiers

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features video-recording` 增加独立的视频文件类型 **N-RAW 12位 3:2(NEV)**，以及 N-RAW 的 **High／Fine／Normal／Basic** 四档画质。同一组还包含[反挤压显示](anamorphic.md)、[ProRes 档位](prores.md)和 [H.265 码率](h265.md)。

### 支持范围

N-RAW 3:2 有自己的“画面尺寸／帧频”列表，共 10 项，均为 FX 画幅：

| 菜单项 | 有效图像 | 编码尺寸 | 读出方式 |
|---|---|---|---|
| `[FX] 8256x5504` 30p／25p／24p | 8256×5504 | 8268×5512 | 全幅读出 |
| `[FX] 4128x2752` 120p／100p／60p／50p | 4128×2752 | 4140×2756 | 直接以 4.1K 读出 |
| `[FX] 4128x2752` 30p／25p／24p | 4128×2752 | 4140×2756 | 8280×5520 全幅读出后按 2:1 过采样 |

4.1K 3:2 的 120p 到 24p 是 v0.5.0 新增的。8.3K 3:2 最高 30p。ProRes、H.265 等其他文件类型保持 16:9，普通 N-RAW 12位(NEV) 的 16:9 列表不变。

### 使用步骤

1. 在视频拍摄菜单打开“视频文件类型”，选择 **N-RAW 12位 3:2(NEV)**。i 菜单没有文件类型项，这一步须在菜单中完成。
2. 打开“画面尺寸／帧频”，从 10 项中选择 8.3K 或 4.1K 及帧频。i 菜单的画面尺寸项也只列出这 10 项。
3. 在“视频品质(N-RAW)”中选择 High、Fine、Normal 或 Basic。
4. 按通常方式录制。改回“N-RAW 12位(NEV)”即回到普通 16:9。设置按视频拍摄菜单库保存；两种 N-RAW 各自记住画面尺寸和色调。

### 输出与显示

输出为 NEV。选择 N-RAW 3:2 时，取景画面使用 3:2 专用的画幅标志，取景、对焦区域和回放均按 3:2 显示。REDline 解出的 4.1K 3:2 为 4128×2752，视野与 8.3K 3:2 相同。

同时安装 [Log 色彩](log-colour.md)时，两条 N-RAW 文件类型行都显示所选 Log 名称。

### 已知问题

- 离开 3:2 后，对焦点可能停在 16:9 网格之外多出的一行。按一次多重选择器即可回到网格内。
- 自动区域 AF 和对象跟踪 AF 可能不会启用画面最上、最下各一行对焦点：自动区域 AF 的合焦绿框可能最多只亮到从上数第二行和从下数第二行；对象跟踪 AF 把对焦框放在最外一行后按 OK，框可能向内移动一行。
- 为兼容只识别两档的软件，Fine 的兼容名称映射为 High，Basic 映射为 Normal；这些名称不能区分实际四档编码。
- Basic 的 1.0 bit/像素预算会损失高频细节。8.3K 3:2 High 为 2.5 bit/像素，普通 8.3K 30／25／24p High 为 3.0；4.1K 3:2 与普通 4.1K 相同。

## English

### Overview

`--features video-recording` adds a separate movie file type, **N-RAW 12-bit 3:2 (NEV)**, and four N-RAW quality tiers: **High/Fine/Normal/Basic**. The same group also installs [anamorphic desqueeze](anamorphic.md), [ProRes grades](prores.md) and [H.265 bitrates](h265.md).

### Supported modes

N-RAW 3:2 has its own Frame size/frame rate list with ten FX entries:

| Menu entry | Active image | Coded size | Readout |
|---|---|---|---|
| `[FX] 8256×5504` 30p/25p/24p | 8256×5504 | 8268×5512 | Full readout |
| `[FX] 4128×2752` 120p/100p/60p/50p | 4128×2752 | 4140×2756 | Read out directly at 4.1K |
| `[FX] 4128×2752` 30p/25p/24p | 4128×2752 | 4140×2756 | Full 8280×5520 readout oversampled 2:1 |

4.1K 3:2 at 120p to 24p is new in v0.5.0. 8.3K 3:2 stops at 30p. ProRes, H.265 and the other file types stay 16:9, and the 16:9 list of ordinary N-RAW 12-bit (NEV) is unchanged.

### Steps

1. In the video recording menu, open Video file type and select **N-RAW 12-bit 3:2 (NEV)**. The i menu has no file type item, so use the menu.
2. Open Frame size/frame rate and pick 8.3K or 4.1K and a frame rate from the ten entries. The i menu frame size item lists the same ten entries.
3. Choose High, Fine, Normal or Basic in Video quality (N-RAW).
4. Record normally. Select N-RAW 12-bit (NEV) again to return to ordinary 16:9. Settings are stored per movie shooting bank, and each N-RAW type keeps its own frame size and tone.

### Files and display

Output is NEV. With N-RAW 3:2 selected, live view shows a separate 3:2 framing mark, and live view, the focus area and playback use the 3:2 frame. REDline decodes 4.1K 3:2 as 4128×2752 with the same field of view as 8.3K 3:2.

With [Log colour](log-colour.md) installed, both N-RAW file type rows show the selected Log name.

### Known issues

- After leaving 3:2, the focus point can remain on an extra row outside the 16:9 grid. Press the multi selector once to bring it back.
- Auto-area AF and subject-tracking AF may not use the top and bottom rows of focus points. Auto-area AF may light its in-focus boxes only as far as the second row from the top and bottom, and a subject-tracking AF frame placed on the outermost row may move one row inward when OK is pressed.
- For compatibility with two-tier readers, Fine maps to the High label and Basic to Normal; those labels cannot distinguish the four actual encoding tiers.
- Basic's 1.0-bit/pixel budget reduces fine texture. 8.3K 3:2 High uses 2.5 bits/pixel versus 3.0 for ordinary 8.3K 30/25/24p High; 4.1K 3:2 uses the same budget as ordinary 4.1K.

## 码率参考 / Bitrate reference

下表为固件码率预算和剩余时间估算，单位 **Mbps（十进制百万 bit/s）**，不是实拍平均码率或最低卡速。编码尺寸不同于有效画幅；文件大小还包含音频、代理及封装开销。MB/s 约为 Mbps÷8，GB/min 约为 Mbps×0.0075。

These are firmware bitrate/time-estimation budgets in **decimal Mbps**, not measured average output or minimum card speeds. Coded dimensions differ from active image dimensions. Audio, proxies and container overhead also affect file size. Approximate conversions: MB/s = Mbps÷8; GB/min = Mbps×0.0075.

Fine/Normal/Basic 分别采用 2.0／1.5／1.0 bit/像素，加估计开销；Fine/Basic 向上取整至 1 Mbps。普通 16:9 High 多为 3.0，8.3K 50/60p 与 8.3K 3:2 High 为 2.5 bit/像素，因此 8.3K 3:2 High 不能简单由普通 High 按高度放大。4.1K 3:2 四档按普通 4.1K 的同帧率项乘以 2756/2330 计算，再向上取整至 1 Mbps。

Fine/Normal/Basic use 2.0/1.5/1.0 bits/pixel plus estimated overhead; Fine/Basic round up to 1 Mbps. Ordinary 16:9 High generally uses 3.0, while 8.3K 50/60p and 8.3K 3:2 High use 2.5 bits/pixel, so 8.3K 3:2 High cannot be calculated by simply scaling ordinary High by height. The four 4.1K 3:2 tiers are the ordinary 4.1K entries at the same rate multiplied by 2756/2330 and rounded up to 1 Mbps.

### 普通画幅 / Standard formats

| 编码尺寸 / Coded size | 帧率 / fps | High | Fine | Normal | Basic |
|---|---:|---:|---:|---:|---:|
| 8268×4652 | 59.94 | 5836 | 4684 | 3526 | 2378 |
| 8268×4652 | 50 | 4866 | 3908 | 2946 | 1985 |
| 8268×4652 | 29.97 | 3498 | 2346 | 1768 | 1193 |
| 8268×4652 | 25 | 2918 | 1959 | 1478 | 998 |
| 8268×4652 | 23.976 | 2808 | 1886 | 1418 | 964 |
| 4140×2330 | 119.88 | 3600 | 2449 | 1870 | 1292 |
| 4140×2330 | 100 | 3020 | 2063 | 1580 | 1098 |
| 4140×2330 | 59.94 | 1796 | 1226 | 936 | 647 |
| 4140×2330 | 50 | 1506 | 1028 | 786 | 545 |
| 4140×2330 | 29.97 | 898 | 613 | 468 | 324 |
| 4140×2330 | 25 | 758 | 519 | 398 | 278 |
| 4140×2330 | 23.976 | 728 | 497 | 378 | 266 |
| 5404×3040 | 59.94 | 3016 | 2039 | 1546 | 1054 |
| 5404×3040 | 50 | 2526 | 1707 | 1296 | 886 |
| 5404×3040 | 29.97 | 1508 | 1025 | 778 | 532 |
| 5404×3040 | 25 | 1268 | 858 | 648 | 447 |
| 5404×3040 | 23.976 | 1218 | 825 | 628 | 432 |
| 3852×2168 | 119.88 | 3140 | 2139 | 1630 | 1138 |
| 3852×2168 | 100 | 2630 | 1798 | 1380 | 963 |


### N-RAW 3:2

| 编码尺寸 / Coded size | 帧率（菜单） / fps (menu) | High | Fine | Normal | Basic |
|---|---:|---:|---:|---:|---:|
| 8268×5512 | 29.970 (30p) | 3455 | 2773 | 2089 | 1407 |
| 8268×5512 | 25.000 (25p) | 2885 | 2316 | 1745 | 1177 |
| 8268×5512 | 23.976 (24p) | 2774 | 2228 | 1681 | 1136 |
| 4140×2756 | 119.88 (120p) | 4259 | 2897 | 2212 | 1529 |
| 4140×2756 | 100 (100p) | 3573 | 2441 | 1869 | 1299 |
| 4140×2756 | 59.94 (60p) | 2125 | 1451 | 1108 | 766 |
| 4140×2756 | 50 (50p) | 1782 | 1216 | 930 | 645 |
| 4140×2756 | 29.97 (30p) | 1063 | 726 | 554 | 384 |
| 4140×2756 | 25 (25p) | 897 | 614 | 471 | 329 |
| 4140×2756 | 23.976 (24p) | 862 | 588 | 448 | 315 |

原厂记录为零的 3852×2168 50/60p 项未列入，不表示新增支持。The stock zero-valued 3852×2168 50/60p entries are omitted and are not added modes.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
