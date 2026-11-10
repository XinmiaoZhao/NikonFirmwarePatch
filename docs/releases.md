# 工具包、源码与验证 / Toolkit, source and verification

当前四组工具包为 [v0.4.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.4.0)。已经发布的版本、附件与对应提交见 [GitHub Releases](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases)；功能变化见[更新日志](../CHANGELOG.md)。工具包版本与用户选择的固件版本相互独立。

## 工具包内容

完整 toolkit 包含源码、许可证、功能文档、色彩报告及中英文图表、数值数据、后期 F LUT，以及九份由公开 C／汇编源码编译的补丁单元：

`precapture.bin`、`pixelshift.bin`、`pixelshift-af.bin`、`opengate.bin`、`anamorphic.bin`、`h265.bin`、`log.bin`、`quality.bin`、`shared.bin`。

不分发原厂或修改后的完整固件、实拍原片、运行库或编译器。Git 克隆与自动 Source code 归档不带补丁机器码；从源码构建时显式使用 `--code-source source`，或使用与源码一致的完整 toolkit。默认预编译模式不调用编译器，也不自动下载缺失文件。

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
python tests/validate_distribution.py --archive /path/to/new-assets/NikonFirmwarePatch-VERSION-toolkit.zip --archive-only --report /path/to/archive-report.json
python tests/validate_combinations.py --stock /path/to/Z_8_0311.bin --report /path/to/combinations-report.json
python tests/validate_prebuilt_cli.py --stock /path/to/Z_8_0311.bin --report /path/to/prebuilt-cli-report.json
python tests/validate_f_lut.py
python tools/check_repository.py --all
```

发布工具只纳入明确列出的已提交文件。独立检查器核对成员、源码字节、代码及来源，额外固件、缺失文件和错误身份会被拒绝。附件保持不可变，修订发布新版本。

## Windows 状态

[Host checks](https://github.com/XinmiaoZhao/NikonFirmwarePatch/actions/workflows/host-checks.yml) 包含跨平台路径检查。手动 Windows 作业按发布 SHA-256 下载最终 ZIP、对照当前提交核对全部成员，再分别用 Python 3.12 和 3.13 从解压目录构建两种组合，并把全选固件与指定回归输入的哈希比对。运行状态见上述 Actions 链接。

当前功能与测试范围见[验证记录](validation.md)，贡献者与许可见 [NOTICE](../NOTICE.md)。

## English

The four groups ship in v0.4.0. A complete toolkit packages public source, documentation, bilingual colour figures/data, the optional F LUT and nine matching compiled patch units. Original/full modified firmware, camera media, runtimes and compilers are not distributed.

Source checkouts use explicit source compilation or a matching complete toolkit. Independent verification checks the exact input, declared edits, untouched bytes, other modules and identities. Release assets are built from a clean reviewed commit and retain that identity. Windows firmware jobs verify the published toolkit digest and source commit, then build from its extracted files on Python 3.12 and 3.13.
