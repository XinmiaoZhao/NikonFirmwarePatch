# 后期 F 色彩映射 / Post-production F colour mapping

[下载 65³ LUT](RWG_Log3G10_F_v1_65.cube) · [文件身份](RWG_Log3G10_F_v1_65.json) · [数值核验](verification.json) · [中文报告](../docs/log-colour-report.md)／[English report](../docs/log-colour-report.en.md)

`RWG_Log3G10_F_v1_65.cube` 为本项目提供的 **F 饱和度映射模型**，用于给当前不含 F 的 Log3G10 录像，近似补上 **RED 解码 Nikon N-RAW 时引入的饱和度映射**。本项目参照使用的 REDline 65.2.1 会在解码链中加入 F；它与 RWG 色域、Log3G10 曲线是独立的处理环节。输入、输出都是 **REDWideGamutRGB / Log3G10**，归一化范围 0—1。它不包含 Rec.709、HDR 或胶片风格的显示变换。

| 项目 | 值 |
|---|---|
| 网格 | 65 × 65 × 65，共 274,625 点 |
| 建议插值 | 四面体（tetrahedral） |
| 文件大小 | 7,415,148 字节，约 7.42 MB |
| SHA-256 | `2862a0c6ee17f73d9e83fcee04a706413742b00d53bc538d224a6a70bb3f93da` |
| 许可 | 本项目 GPL-3.0-only；生成源码随仓库提供 |

## 使用顺序

Resolve／FCP 的具体设置与处理顺序见 [Log 后期流程](../docs/log-colour.md)。当前机内色彩矩阵仍未定稿；本 LUT 的数值核验不等于机内颜色已通过验收，也不能补偿未知的矩阵误差。

**正确解码素材 → 白平衡／曝光调整 → 本 F LUT → 显示变换或还原 LUT → 输出。**

1. 确认进入该节点的是 RWG / Log3G10 RGB 数据。源文件的 YCbCr 解码矩阵和视频电平应正确；不要用变更电平的方式补偿颜色。
2. 在支持 `.cube` 的后期软件中导入本文件。可以选择插值方式时，使用四面体。
3. 在 LUT 之前完成白平衡。整体线性曝光缩放与解析模型相容；通道之间不同的增益会改变饱和度，所以白平衡的先后顺序有意义。
4. LUT 之后按 RWG / Log3G10 解释输出，再接相应的 Rec.709、HDR 或其他显示变换。套用本 LUT 后，画面仍是 Log。

若项目已经自动把素材转到其他工作空间，应在本节点前转换回 RWG / Log3G10，并在节点后转换回项目工作空间。S-Log3 素材也需要先做相应色域／曲线转换。已经由上述 RED 路径解码的 N-RAW 含有 F，不应再叠加一次；本项目的当前 Log3G10 录像按无 F 目标标定，适合将这一步留在后期选择。

## 模型的作用

在线性 RWG 中，令最大通道为 `m`，最小通道与最大通道之比为 `s`。模型保持最大通道及线性 RGB 的 HSV 色相，抬高过低的其他通道，从而降低饱和度。蓝通道占主导时的处理范围较宽；红或绿占主导时主要处理更极端的饱和颜色。由于通道比例发生变化，XYZ 亮度也可能改变。

模型具有整体曝光缩放不变性：正比例缩放输入后，解析输出也按同比例缩放。LUT 按下式生成：

`Log3G10 → 线性 RWG → F 模型 → Log3G10`

网格中两个最大通道完全相等的位置，取相邻分支的 Log 码值平均，避免单独的并列值被插值扩大成格点条纹。中性轴保持不变。模型不加入与绝对码值相关的近黑激活阈值。

## 精度与适用范围

独立检查器逐项验证了 `.cube` 的尺寸、顺序、输入范围及全部 274,625 个格点。文本保留六位小数，格点与解析模型的最大归一化差小于 `5.01×10⁻⁷`，中性轴核对通过。

在色彩报告的 **288 个参照色片输入**上，四面体 LUT 相对解析模型的 RGB 误差为：

| 指标 | 10-bit 等效码值 |
|---|---:|
| RMS | 0.040 |
| 99% 分位 | 0.179 |
| 最大值 | 0.372 |

模型在蓝色主导通道切换处具有不同分支，格点插值会平滑该边界。因此上述色片结果不代表整个 RGB 立方体的误差上限。固定种子的 10,000 个均匀立方体压力样本，99% 分位为 0.283 码、最大为 104.67 码；这些极端边界值保留在核验记录中。最终观感还取决于素材的压缩、噪声、白平衡和后续显示变换。

## 重建与核验

只需要 Python 标准库，命令不访问固件或设备：

```sh
python tools/build_f_lut.py --size 65 --output build/luts/RWG_Log3G10_F_v1_65.cube
python tests/validate_f_lut.py --lut build/luts/RWG_Log3G10_F_v1_65.cube
```

输出目录中的同名文件必须不存在。生成器另支持 17³ 和 33³，供容量或软件兼容性需要；本仓库交付文件使用 65³。完整文件及生成参数由相邻 JSON 绑定。

## English

See the [Resolve/FCP workflow](../docs/log-colour.md#english) for application settings and ordering. The camera colour matrices are not final; numerical validation of this LUT neither establishes camera-colour accuracy nor repairs unknown matrix errors.

The supplied 65³ CUBE approximates the F saturation mapping introduced by RED when decoding Nikon N-RAW. The reference path used in this project, REDline 65.2.1, applies F in addition to the RWG gamut conversion and Log3G10 encoding. Both input and output are **REDWideGamutRGB / Log3G10**, normalized to 0–1. Place it after white-balance adjustment and before a display/output transform. It is not a Rec.709 LUT, and its output remains Log. N-RAW decoded through that RED path already contains F and should not receive it again.

The scale-free linear-RWG model preserves the maximum channel and HSV hue while reducing saturation; blue-dominant colours use a broader threshold. At tied-dominant grid nodes, adjacent branch limits are averaged in Log code space to avoid interpolation stripes. The neutral axis is preserved. An absolute near-black activation threshold is not included.

All 274,625 grid nodes and the CUBE ordering were independently checked. On the report's 288 reference-patch inputs, tetrahedral interpolation differs from the analytic model by **0.040 code RMS**, **0.179 at the 99th percentile**, and **0.372 maximum**, expressed as 10-bit RGB codes. This is not a full-cube error bound: a deterministic uniform-cube stress sample reaches **104.67 codes** at extreme branch boundaries. Full numerical results, file hashes and the standard-library generator are included. No editing-application UI test is claimed.
