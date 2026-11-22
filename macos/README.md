# Z8 补丁构建器 / Z8 Patch Builder（macOS）

本目录是 `patch.py` / `verify.py` 的 macOS 图形界面。它不重写构建逻辑：应用内置与 Release 工具包逐字节相同的运行文件、一个精简的 CPython 3.12 和 capstone 5.0.7，按顺序调用命令行工具。

## 应用做什么

1. **检查输入。** 应用先核对长度与 SHA-256，再运行 `patch.py <输入> --check`。只接受原厂 Z8 C 3.11。
2. **构建。** `patch.py <输入> --features … --version … --tag … --output <新文件夹>`，默认使用预编译单元；“高级 → 从源码编译”会先检测编译器版本。
3. **独立核验。** 在另一个进程运行 `verify.py`；它不导入构建器。
4. **读回校验。** 重新读取 `.bin`，与 `manifest.json`、`SHA256SUMS.txt` 和构建报告比对。

输出总是新建的文件夹（同名时自动加序号）。取消会终止子进程并删除这次未完成的输出；核验或读回失败时，`.bin` 改名为 `.bin.unverified`，以免误装。应用不写存储卡，也不更新相机。

启动时应用按 `release-manifest.json` 核对内置工具包的每个文件；有缺失、改动或多余文件时禁用构建。功能介绍、已知限制和操作演示的说明文字来自 [`resources/gui-catalog.json`](../resources/gui-catalog.json)，由 [`tests/validate_gui_catalog.py`](../tests/validate_gui_catalog.py) 对照 `features.py` 与 `docs/` 检查。

系统要求：macOS 14 或更高，Apple 芯片。界面提供简体中文、繁體中文和英文。

## 界面语言

界面文字在代码里写英文原文，译文放在 String Catalog [`Resources/Localizable.xcstrings`](Resources/Localizable.xcstrings)，可以用 Xcode 编辑，也可以导出 XLIFF 交给译者。`build_app.py` 用 `xcstringstool` 把它编译进各语言的 `.lproj`，并核对 Release 程序用到的每条文字都有译文。应用运行中可以切换语言，所以每次取文字都指定当前选择的语言。

改动界面文字后运行 `python3 -B macos/scripts/sync_strings.py`：它用编译器抽出代码里的字符串，加入新条目，标出已删除的条目。补齐译文后运行 `tests/validate_gui_catalog.py`。功能介绍、已知限制和操作演示的说明随工具包发布，放在 `resources/gui-catalog.json`，每段都有 `en`、`zh-Hans`、`zh-Hant` 三项。

繁體中文采用台湾用语；相机菜单名按原厂 C 3.11 的繁體中文菜单和补丁写进该语言的名称（如「短片品質(N-RAW)」「變形鏡頭拉伸顯示」「像素位移合成」）。增加语言时，在 `Lang` 增加一项，在两个目录里补译文，再加一个带 `InfoPlist.strings` 的 `.lproj`。

## 从源码构建

需要 Xcode 26（Swift 6.3）和本仓库的干净提交。先用发布工具生成工具包，再组装应用：

```sh
python3 -B tools/build_release.py --tag vX.Y.Z --output /tmp/z8-toolkit
python3 -B macos/scripts/build_app.py --toolkit-zip /tmp/z8-toolkit/NikonFirmwarePatch-vX.Y.Z-toolkit.zip --output /tmp/z8-app
```

`build_app.py` 会核对工具包 ZIP（`tools/check_release.py`），按 [`runtime.json`](runtime.json) 中固定的大小和 SHA-256 下载或使用本地的 python-build-standalone 与 capstone（`--python-archive`、`--capstone-wheel`），只保留工具包用到的标准库模块，编译应用，签名，运行 `--self-test`，最后生成 `NikonFirmwarePatch-vX.Y.Z-macOS.dmg` 和 `SHA256SUMS.txt`。默认是临时签名，只用于本机测试。

DMG 打开后是“拖到 Applications”的安装窗口：背景由 [`scripts/make_dmg_background.swift`](scripts/make_dmg_background.swift) 在构建时绘制（1x 与 2x），窗口大小、图标位置和背景由 dmgbuild 直接写进 DMG 的 `.DS_Store`，不需要操控 Finder。dmgbuild 及其依赖 ds-store、mac-alias 同样按 `runtime.json` 固定版本和 SHA-256，只在构建时使用，不进应用也不进 DMG；因此运行 `build_app.py` 的 Python 需要 3.10 或更新。图标名字由 Finder 叠加绘制，衬底取中灰（相对亮度约 0.18），黑字白字都约 4.5:1。

发布版需要 Developer ID。一次性准备两样东西：在 Xcode → 设置 → 帐户 → 管理证书中添加“Developer ID Application”证书；再用 Apple 帐户的 App 专用密码保存公证凭据（`xcrun notarytool store-credentials <配置名> --apple-id <Apple ID> --team-id <团队 ID>`，按提示输入密码）。如果 Xcode 拒绝创建 Developer ID 证书，可以在 developer.apple.com 的 Certificates 页面上传证书签名请求（CSR）手动创建，下载后双击装入登录钥匙串。然后：

```sh
python3 -B macos/scripts/build_app.py --toolkit-zip … --output … \
  --identity <证书的 SHA-1，见 security find-identity -v -p codesigning> --notary-profile <配置名>
```

脚本给 `libcapstone.dylib`、`python3.12` 和应用分别签名（Hardened Runtime，带时间戳），先核对三者都带团队 ID，再提交公证：先公证应用并装订票据，再用装订后的应用生成 DMG，公证并装订 DMG。每一步都用 Gatekeeper（`spctl`）复核，必须显示 “Notarized Developer ID”；公证日志保存在输出目录。应用单独装订后，从 DMG 拖出的副本离线也能通过 Gatekeeper。

## 测试

```sh
python3 -B tests/validate_gui_catalog.py
python3 -B macos/scripts/sync_strings.py --check
swift test --package-path macos
```

第一项检查两个文字目录：三种语言齐全、占位符与原文一致、简繁没有混用。第二项确认 String Catalog 与代码一致。单元测试不需要固件。设置以下变量后会运行真实构建：15 种组合通过应用的流水线和命令行各构建一次（最多 6 种同时进行，不超过核心数的一半），比对 `.bin`、`SHA256SUMS.txt` 与 `manifest.json`；另有修改过的输入、已打补丁的输入、已存在的输出文件夹、取消、核验失败和源码模式的检查。

```sh
Z8_APP=/tmp/z8-app/"Z8 Patch Builder.app" Z8_STOCK=/path/to/Z_8_0311.bin \
Z8_CLI_PYTHON=/path/to/venv/bin/python Z8_CLI_TOOLKIT=/path/to/extracted/NikonFirmwarePatch-vX.Y.Z \
swift test --package-path macos
```

`manifest.json` 只有 `source_hashes` 一项不同：它列出 `patch.py` 旁边的文件，应用只内置运行所需的文件，ZIP 还带测试、检查脚本和文字说明。两边共有的条目必须一致。

## 已知限制

- 操作演示里的相机菜单按相机原文重绘（文字取自所选界面语言的固件菜单），是示意动画，不是实拍画面；预拍信息栏和回放文件名做了简化。
- 应用把 Python 子进程的输出整段显示在日志里，没有逐项进度条；构建步骤本身约 5–10 秒。
- 菜单栏的系统项目只在启动时本地化，所以整个菜单栏保持启动时的语言。在设置里换语言后，窗口内的文字立即切换；设置里会出现“重新启动”，点了之后菜单栏才切换。汉字字形也按启动时的语言选择：从简体换到繁體中文后，要重新启动才显示台湾字形（如「骨」「述」）。
- “跟随系统”按 macOS“首选语言”列表的顺序，取第一个应用提供的语言（简体中文、繁體中文或英文），都没有时用英文。香港、澳门的繁體中文和粤语也显示为繁體中文（台湾用语），没有单独的香港版。

## English

This folder is a macOS front end for `patch.py` and `verify.py`. It does not reimplement the builder: the app bundles the release toolkit's runtime files byte for byte, a trimmed CPython 3.12 and capstone 5.0.7, and runs the command-line tools in order — `patch.py --check`, the build, `verify.py` in a separate process, then a read-back of the `.bin` against `manifest.json` and `SHA256SUMS.txt`. Outputs always go to a new folder. Cancelling removes the incomplete output; a failed verification renames the firmware to `.bin.unverified`. The app never writes to memory cards or updates a camera. At launch it checks every bundled toolkit file against `release-manifest.json` and disables building on any mismatch. Requires macOS 14 or later on Apple silicon. The interface is in Simplified Chinese, Traditional Chinese (Taiwan usage) and English: interface strings are written in English in the code and translated in the String Catalog `Resources/Localizable.xcstrings` (refresh it with `macos/scripts/sync_strings.py`); feature text in `resources/gui-catalog.json` carries `en`, `zh-Hans` and `zh-Hant`.

Build with `tools/build_release.py` and then `macos/scripts/build_app.py` as shown above; pinned runtime downloads are listed in `runtime.json`, including dmgbuild (with ds-store and mac-alias), which writes the disk image's drag-to-Applications window layout at build time and needs Python 3.10 or later; the window background is drawn by `scripts/make_dmg_background.swift`. Ad-hoc signing is for local tests only; releases use a Developer ID identity and `--notary-profile`, which notarizes and staples the app, then builds, notarizes and staples the disk image, checking each with Gatekeeper. Tests: `tests/validate_gui_catalog.py`, `macos/scripts/sync_strings.py --check` and `swift test --package-path macos`; set `Z8_APP`, `Z8_STOCK`, `Z8_CLI_PYTHON` and `Z8_CLI_TOOLKIT` to run all 15 selections through the app pipeline and the command line (up to six at a time, at most half the cores), plus negative controls.
