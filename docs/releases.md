# 工具包、源码与验证 / Toolkit, source and verification

当前四组工具包为 [v0.5.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.5.0)。已经发布的版本、附件与对应提交见 [GitHub Releases](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases)；功能变化见[更新日志](../CHANGELOG.md)。工具包版本与用户选择的固件版本相互独立。

## 发布附件

| 附件 | 内容 |
|---|---|
| `NikonFirmwarePatch-VERSION-toolkit.zip` | 命令行工具包，见下节 |
| `NikonFirmwarePatch-VERSION-F-LUT.zip` | 后期 F LUT：`.cube`、文件身份、数值核验、[LUT 说明](../luts/README.md)、许可证 |
| `NikonFirmwarePatch-VERSION-macOS.dmg` | [Mac app](macos-app.md)，内置同一版工具包的运行文件，已签名并经 Apple 公证 |
| `SHA256SUMS.txt` | 以上三个附件的 SHA-256 |

## 工具包内容

toolkit ZIP 只收构建和核验固件需要的文件：`patch.py`、`verify.py` 与各功能的源码、配方和图标，测试与检查脚本，许可证、更新日志和文字说明（功能指南、已知问题、当前验证），以及十九份由公开 C／汇编源码编译的补丁单元：

`precapture.bin`、`pixelshift.bin`、`pixelshift-af.bin`、`opengate.bin`、`anamorphic.bin`、`h265.bin`、`log.bin`、`quality.bin`、`shared.bin`、`heif-format.bin`、`heif-capture.bin`、`heif-srgb.bin`、`area-sizes.bin`、`area-formula.bin`、`area-quick.bin`、`area-thumbnail.bin`、`heif-drive.bin`、`heif-icc.bin`、`precapture-menu.bin`。

仓库中的其他文件不进工具包，包括：README 和指南中的截图；色彩报告及其图表、数据和绘图脚本；后期 F LUT（另作附件提供）；旧版本的验证页；仓库配置与发布者工具；macOS app 源码（app 另以 DMG 发布）。这些文件可以在 GitHub 上查看，或从同一版本的 Source code 归档取得。`tools/check_release.py` 用两张清单把每个已跟踪文件归入“工具包”或“仅仓库”，发布工具拒绝未归类的文件。

不分发原厂或修改后的完整固件、实拍原片、运行库或编译器。Git 克隆与自动 Source code 归档不带补丁机器码；从源码构建时显式使用 `--code-source source`，或使用同一版本的 toolkit。默认预编译模式不调用编译器，也不自动下载缺失文件。

## 构建身份与独立核验

输入为完整原厂 C 3.11，99,051,117 字节，SHA-256 `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`。

`resources/compiled.json` 绑定代码长度、哈希、符号、编译参数及源文件哈希；`resources/combinations.json` 记录 15 种组合的修改范围。manifest 保存来源提交、功能选择、输出身份与文件哈希。

`verify.py` 独立解封装，检查原始输入、声明窗口、未修改字节、其他模块、身份和校验值。传入 `--features --version --tag` 可同时核对期望的组合与身份。不同组合或不同内容使用不同固件身份。Z8 支持降级与同版本重刷。

## 发布者复现

从最终审阅的干净提交生成源码、文档与附件。下面的 `VERSION` 和 `COMMIT_SHA` 使用本次实际版本和提交：

```sh
python -B tests/test_compiled_paths.py
python tools/build_release.py --tag VERSION --compiler clang --output /path/to/new-assets
python tools/check_release.py /path/to/new-assets/NikonFirmwarePatch-VERSION-toolkit.zip --commit COMMIT_SHA
python tools/check_release.py /path/to/new-assets/NikonFirmwarePatch-VERSION-F-LUT.zip
python tests/validate_distribution.py --archive /path/to/new-assets/NikonFirmwarePatch-VERSION-toolkit.zip --lut /path/to/new-assets/NikonFirmwarePatch-VERSION-F-LUT.zip --archive-only --report /path/to/archive-report.json
python tests/validate_combinations.py --stock /path/to/Z_8_0311.bin --report /path/to/combinations-report.json
python tests/validate_prebuilt_cli.py --stock /path/to/Z_8_0311.bin --report /path/to/prebuilt-cli-report.json
python tests/validate_f_lut.py
python tools/check_repository.py --all
```

`build_release.py` 同时生成工具包和 F LUT 两个 ZIP 及 `SHA256SUMS.txt`。Mac app 按 [macos/README.md](../macos/README.md) 从这个工具包 ZIP 构建，签名公证后把它输出的 DMG 校验行并入同一份 `SHA256SUMS.txt`。发布工具只纳入明确列出的已提交文件。独立检查器核对成员、源码字节、代码及来源，额外固件、缺失文件和错误身份会被拒绝。附件保持不可变，修订发布新版本。

## Windows 状态

[Host checks](https://github.com/XinmiaoZhao/NikonFirmwarePatch/actions/workflows/host-checks.yml) 包含跨平台路径检查。手动 Windows 作业按发布 SHA-256 下载最终 ZIP、对照当前提交核对全部成员，再分别用 Python 3.12 和 3.13 从解压目录构建两种组合，并把全选固件与指定回归输入的哈希比对。运行状态见上述 Actions 链接。

当前功能与测试范围见[验证记录](validation.md)，贡献者与许可见 [NOTICE](../NOTICE.md)。

## English

The four groups ship in v0.5.0. A release has four assets: the command-line toolkit ZIP; the F LUT ZIP with the `.cube`, its identity record, numerical checks, [guide](../luts/README.md) and license; the signed and notarized [Mac app](macos-app.md) disk image, which bundles the runtime files of the same toolkit; and `SHA256SUMS.txt` covering the other three. `build_release.py` writes both ZIPs and the checksum file; the app is built from that toolkit ZIP as described in [macos/README.md](../macos/README.md), and its DMG checksum line is added to the same file.

The toolkit ZIP carries what builds and verifies firmware: `patch.py`, `verify.py`, feature source, recipes and icons, tests and checkers, the license, changelog and text guides, plus nineteen matching compiled patch units. Other tracked files stay in the repository and in GitHub’s source archive of the tag: screenshots, the colour report with its figures, data and plotting scripts, the optional F LUT (offered as its own download), earlier validation pages, repository configuration, publisher-only tools, and the macOS app source (the app ships as its own disk image). `tools/check_release.py` assigns every tracked file to one of the two lists, and the release tool refuses unassigned files. Original/full modified firmware, camera media, runtimes and compilers are not distributed.

Source checkouts use explicit source compilation or the toolkit of the same release. Independent verification checks the exact input, declared edits, untouched bytes, other modules and identities. Release assets are built from a clean reviewed commit and retain that identity. Windows firmware jobs verify the published toolkit digest and source commit, then build from its extracted files on Python 3.12 and 3.13.
