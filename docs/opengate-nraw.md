# 开放门与 N-RAW 四档 / Open gate and N-RAW tiers

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features framing` 同时增加 FX 3:2 开放门和 **High／Fine／Normal／Basic** 四档 N-RAW 画质。与反挤压显示一起安装；画幅组可以独立构建。

### 支持范围

开放门支持 **N-RAW、FX 3:2、8.3K 30／25／24p**，有效图像 **8256×5504**。普通 16:9 模式仍可选择，其 8.3K 有效图像为 8256×4644。不增加 50／60p 开放门，也不把 ProRes／H.265 改成 3:2。

### 使用步骤

1. 在视频文件类型中选择 N-RAW。
2. 打开“画面尺寸／帧频”，顶部三项为 `[FX 3:2]` 30p、25p、24p，按需选择。
3. 在视频画质中选择 High、Fine、Normal 或 Basic。
4. 按通常方式录制。普通视频与开放门可在菜单中切换，设置按视频拍摄菜单库保存。

### 输出与显示

输出为 NEV，取景和回放按所选画幅显示。档位名和回放信息用于区分设置；码率预算与剩余时间参考中英共用的下表。

下表的 8268×5512／8268×4652 是编码尺寸，不能当作有效画幅。

### 已知问题

- 为兼容只识别两档的软件，Fine 的兼容名称映射为 High，Basic 映射为 Normal；这些名称不能区分实际四档编码。
- Basic 的 1.0 bit/像素预算会损失高频细节。开放门 High 为 2.5 bit/像素，普通 8.3K 30／25／24p High 为 3.0，不能视为相同压缩预算。
- 开放门、N-RAW 四档和反挤压属于同一个画幅组。

## English

### Overview

`--features framing` adds FX 3:2 open gate and **High/Fine/Normal/Basic** N-RAW quality tiers. It is bundled with anamorphic desqueeze; the framing group can be built independently.

### Supported modes

Open gate supports **N-RAW, FX 3:2, 8.3K 30/25/24p**, with **8256×5504** active pixels. Ordinary 16:9 modes remain available; 8.3K 16:9 has 8256×4644 active pixels. It adds neither 50/60p open gate nor ProRes/H.265 3:2.

### Steps

1. Select N-RAW as the movie file type.
2. Open Frame size/frame rate. The first three entries are `[FX 3:2]` 30p, 25p and 24p; select one.
3. Choose High, Fine, Normal or Basic in movie quality.
4. Record normally. Switch between ordinary video and open gate in the menu; settings are stored per movie shooting bank.

### Files and display

Output is NEV. Live view and playback use the selected aspect ratio. Menu/playback grade labels identify settings. The shared tables below provide bitrate and remaining-time budgets.

8268×5512/8268×4652 in those tables are coded dimensions, not the active image sizes.

### Known issues

- For compatibility with two-tier readers, Fine maps to the High label and Basic to Normal; those labels cannot distinguish the four actual encoding tiers.
- Basic's 1.0-bit/pixel budget reduces fine texture. Open-gate High uses 2.5 bits/pixel versus 3.0 for ordinary 8.3K 30/25/24p High; the budgets are different.
- Open gate, four N-RAW tiers and desqueeze are one build group.

## 码率参考 / Bitrate reference

下表为固件码率预算和剩余时间估算，单位 **Mbps（十进制百万 bit/s）**，不是实拍平均码率或最低卡速。编码尺寸不同于有效画幅；文件大小还包含音频、代理及封装开销。MB/s 约为 Mbps÷8，GB/min 约为 Mbps×0.0075。

These are firmware bitrate/time-estimation budgets in **decimal Mbps**, not measured average output or minimum card speeds. Coded dimensions differ from active image dimensions. Audio, proxies and container overhead also affect file size. Approximate conversions: MB/s = Mbps÷8; GB/min = Mbps×0.0075.

Fine/Normal/Basic 分别采用 2.0／1.5／1.0 bit/像素，加估计开销；Fine/Basic 向上取整至 1 Mbps。普通 16:9 High 多为 3.0，8.3K 50/60p 与开放门 High 为 2.5 bit/像素。因此开放门 High 不能简单由普通 High 按高度放大。

Fine/Normal/Basic use 2.0/1.5/1.0 bits/pixel plus estimated overhead; Fine/Basic round up to 1 Mbps. Ordinary 16:9 High generally uses 3.0, while 8.3K 50/60p and open-gate High use 2.5 bits/pixel. Open-gate High cannot be calculated by simply scaling ordinary High by height.

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


### FX 3:2 开放门 / Open gate

| 编码尺寸 / Coded size | 帧率（菜单） / fps (menu) | High | Fine | Normal | Basic |
|---|---:|---:|---:|---:|---:|
| 8268×5512 | 29.970 (30p) | 3455 | 2773 | 2089 | 1407 |
| 8268×5512 | 25.000 (25p) | 2885 | 2316 | 1745 | 1177 |
| 8268×5512 | 23.976 (24p) | 2774 | 2228 | 1681 | 1136 |

原厂记录为零的 3852×2168 50/60p 项未列入，不表示新增支持。The stock zero-valued 3852×2168 50/60p entries are omitted and are not added modes.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
