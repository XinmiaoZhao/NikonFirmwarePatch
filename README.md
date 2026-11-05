# NikonFirmwarePatch — Nikon Z8 功能扩展

Nikon Z8 C 3.11 实验补丁的离线构建工具。提供四组可独立选择的功能，并可一次构建任意组合。本版为 **v0.4.0-rc.1 预发布版**。[下载完整工具包与校验清单](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.4.0-rc.1)。使用本轮补丁构建的全选固件，已实机验证新录与旧录 N-RAW 的 Log 回放名称和辅助观感。

| 构建选项 | 功能 |
|---|---|
| `framing` | N-RAW 开放门 3:2、反挤压预览／回放、N-RAW 四档品质 |
| `video-quality` | ProRes HQ／422／LT／Proxy 及 HQ 星标；H.265 五档码率、星标与保护计时修正 |
| `log-colour` | Log 菜单选择 N-Log／BT.2020、S-Log3／S-Gamut3.Cine、Log3G10／REDWideGamutRGB，含标签、图标和显示辅助 |
| `photo-tools` | C15/C30 RAW 预拍（FX/DX，无损选择回退 HE★）与像素偏移合成（修复任意起始编号的组识别） |

N-RAW 四档始终与开放门在同一组；`video-quality` 指 ProRes＋H.265。反挤压可关闭，开放门只在选择相应画幅时启用。照片组的两项功能仍使用各自的机内入口；RAW 预拍输出不能用作像素偏移合成输入。

四组有 15 种非空组合。旧选项 `prores / precapture / pixelshift / opengate-nraw` 不再被当前 CLI 接受，也不会静默扩大为新组；需要复现旧包时使用对应旧发布源码与工具包。

## 构建

输入必须是用户自行取得的**完整原厂 Z8 C 3.11** `Z_8_0311.bin`，99,051,117 字节，SHA-256：

```text
d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96
```

不支持 C 3.12，不接受已经打补丁的固件。仓库不包含原厂固件、相机素材或运行库。工具只生成本地文件，不访问存储卡、不更新相机。

安装 Python 依赖：

```sh
python -m pip install -r requirements.txt
```

检查输入：

```sh
python patch.py Z_8_0311.bin --check
```

预编译模式需要与源码匹配的完整工具包。直接从 Git 源码构建须明确选择源码模式，并提供兼容的 Clang；源码和预编译路径都检查已审定的机器码及配方。

```sh
# 画幅组独立构建；这是示例身份，实际分配须避免与不同内容重名。
python patch.py Z_8_0311.bin --features framing --version 06.17 --tag p0 --output build/framing --code-source source

# 全选四组，版本号用于标识本次输出。
python patch.py Z_8_0311.bin --features framing video-quality log-colour photo-tools --version 04.06 --tag p0 --output build/all --code-source source

# 交互选择四组；预编译工具包默认不调用编译器。
python patch.py Z_8_0311.bin --interactive --version 06.31 --tag p0 --output build/chosen
```

构建输出为 `.bin`、`manifest.json` 和 `SHA256SUMS.txt`。输出目录必须不存在；输入原件不会被覆盖。不同内容使用不同版本／标签身份。`00.xx.t0` 仅用于离线测试，不能作为上机包。

独立核验示例：

```sh
python verify.py Z_8_0311.bin build/all/Z_8_0406.bin --features framing video-quality log-colour photo-tools --version 04.06 --tag p0
```

`verify.py` 不导入构建器，独立检查封装、输入身份、补丁窗口和未改字节，并检查共享菜单、分组可见性、字符串边界与初始化状态。它不能证明相机上的硬件行为。

## 功能说明与验证

- [四组结构与迁移](docs/feature-groups.md)
- [开放门／N-RAW](docs/opengate-nraw.md)、[反挤压](docs/anamorphic.md)
- [ProRes](docs/prores.md)、[H.265](docs/h265.md)
- [Log 设置与后期流程](docs/log-colour.md)、[色彩报告：中文](docs/log-colour-report.md)／[English](docs/log-colour-report.en.md)、[后期 F LUT](luts/README.md)
- [RAW 预拍](docs/raw-precapture.md)、[像素偏移](docs/pixelshift.md)
- [当前验证](docs/validation.md)、[已知问题](docs/known-issues.md)、[更新日志](CHANGELOG.md)

## 色彩测试与后期 LUT

[中文版色彩报告](docs/log-colour-report.md)与[英文版](docs/log-colour-report.en.md)分别展示当前录像与同场 N-RAW 的实拍色差，以及简化矩阵、原厂色相表和恒等 Cpxs 的模拟偏色。当前后期操作见 [Log 设置与 Resolve／FCP 流程](docs/log-colour.md)：明确指定输入色域与曲线，检查自动识别，并避免重复转换。

[65³ 后期 F LUT](luts/README.md)以 RWG／Log3G10 输入和输出，给当前无 F 素材近似补上 RED 解码 N-RAW 时引入的饱和度映射，再接显示变换。LUT、生成脚本和独立数值核验随仓库提供。

## 致谢与许可

感谢参与基础研究、功能实现、讨论与测试的贡献者。名单、依赖和许可证范围见 [NOTICE](NOTICE.md)。

## English

The [v0.4.0-rc.1 pre-release toolkit](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.4.0-rc.1) builds four independently selectable groups from the exact original Z8 C 3.11 firmware: `framing`, `video-quality`, `log-colour`, and `photo-tools`. N-RAW quality stays bundled with open gate. ProRes/H.265 share one icon dispatcher; video menus, bank settings and language resources are composed once. All 15 nonempty combinations use the same source modules.

The Log module currently offers three choices: S-Log3 clamping is unchanged from stock and Log3G10 does not include RED F. The camera-tested matrices and constant Cpxs are included. The all-feature firmware passed on-camera Log label and view-assist checks on existing and newly recorded N-RAW clips. Lossless selection in C15/C30 produces HE★ NEF, not lossless NEF. Pixel-shift merging still requires its own complete FX lossless groups.

Use `--code-source source` with a compatible Clang for a source checkout, or use matching reviewed prebuilt units from a complete toolkit. Builds require explicit groups or interactive selection. Legacy feature names are rejected. The tool performs offline file operations only; it never writes a card or updates a camera.

The [English colour report](docs/log-colour-report.en.md) ([中文](docs/log-colour-report.md)) compares recorded video with same-scene N-RAW and uses common-input simulations to isolate the effects of gamut conversion and chroma compensation. Follow the [Resolve and FCP instructions](docs/log-colour.md#english) for explicit input assignment, camera LUTs and conversion order. An optional [65³ post-production F LUT](luts/README.md) approximates the saturation mapping introduced by RED when decoding N-RAW. It maps RWG/Log3G10 to the same space before a display transform. See [NOTICE](NOTICE.md) for contributors and attribution.
