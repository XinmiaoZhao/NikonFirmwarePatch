# 当前版本验证 / Current validation

适用于 v0.3.1。v0.3.1 只改像素位移的组识别；ProRes、RAW 预拍和开放门／N-RAW 的固件字节与 v0.3.0／v0.3.0-r1 相同，下述记录继续适用于这三项。构建与核验程序（`patch.py`、`verify.py`、源码与机器码加载器）自 v0.3.0-r1 起未变。上一公开版为 [v0.2.0](validation-v0.2.0.md)，功能变化见[更新日志](../CHANGELOG.md)。[机器可读摘要](validation-v0.3.1.json)保留验证项目及证据哈希。

## v0.3.1 像素位移修复 / Pixel-shift fix

修复 [issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)。改动只在 `z8pixelshift/src/group.c`（起始文件字按字段核对、整字作组身份）、`group.h` 注释和 `job.c` 日志首行。编译所得 `pixelshift.bin`（130,520 B）与此前已审核的合成实现逐字节相同；`pixelshift-af.bin` 及其他两份机器码不变。

- **合成元数据，30 例。** 公开源码在主机上编译（ASan/UBSan），扫描内存中的 TIFF 夹具：起始编号 1、2、9、2048、2049、4097、8192、9996，issue 原值 2841，跨过 9999 进入下一文件夹，卡槽 2，文件夹 100 与 999，8／32 张组，同一文件夹两组，均能识别；文件编号 0／10000、文件夹 99／1000、JPG／TIF 类型、最高两位置位、版本错误、未启用像素位移和普通照片均被拒；缺帧和重复帧的组不可选。同一夹具下旧版有 16 例少认组。
- **相机原片主机回归。** 生产代码的完整合成作业在主机上运行。六组相机原片（起始编号均为 `0001`）的输出与此前固定的结果相同。把同样的原片复制，只改写起始文件字，模拟 `102NCZ_8/DSC_2841` 起的 issue 版式、同一文件夹两组、跨过 `DSC_9999` 的 8 张组和卡槽 2 的 32 张组；全部识别并合成，每个输出与原组输出只差 NEFX 自身的起始文件字 4 字节。旧版对 issue 版式认 0 组。80 个原片前后哈希不变。
- **15 种组合。** 含像素位移的 8 种配方只改同一个代码窗口；其余 7 种与 v0.3.0-r1 逐行相同，同身份构建的固件逐字节相同。全部组合通过独立封装、修改范围和版本身份核验，源码与预编译构建一致。
- **QEMU。** 使用同一份像素位移代码的测试包在 SD 槽对 issue 版式的两组完成列表、选择和合成，输出与运行前固定的主机预期逐字节相同。公开 v0.3.1 的 8 种配方没有重跑 QEMU 启动检查。
- **未覆盖。** 尚未在相机上用以非 `0001` 编号起始的实拍组验证，也没有取得 issue 报告者的原片。下表的像素位移实机记录来自旧代码，测试组都从 `0001` 开始。

v0.3.1 fixes issue #17 by changing pixel-shift group discovery only. The compiled `pixelshift.bin` (130,520 B) is byte-identical to the previously reviewed merge implementation; the other machine code is unchanged. Host checks of the public source passed 30 synthetic cases (any starting number, folder rollover, slot 2, two groups per folder; field and structure negatives rejected) and a full host merge on camera originals: six original groups reproduce the pinned outputs, and copies with rewritten start-file words (issue layout, two groups per folder, a group rolling over `DSC_9999`, a slot-2 32-frame group) merge with outputs differing only in that 4-byte word. Only the code window of the eight pixel-shift recipes changed; the seven other selections build identical firmware to v0.3.0-r1, and all 15 pass independent verification and source/prebuilt equivalence. The same code merged the issue layout in QEMU in an implementation-matched test package. Camera confirmation with a group starting at another number is still pending; the pixel-shift camera records below come from the previous code.

## r1 主机验证 / Host revision checks

本次修订只统一源码身份键的路径表示；源码仍按原始字节计算 SHA-256。四份补丁机器码与全部组合配方沿用 v0.3.0，同身份、同功能选择应生成相同固件字节。下述原指令、QEMU 与实机记录仍绑定原功能实现，本次不新增设备安全结论。

- `tests/test_compiled_paths.py` 用独立清单、真实文件及 Python 的 Windows 路径语义检验加载器，覆盖四份补丁、两种加载模式，以及改动源码／机器码、缺失／额外文件的拒绝路径。无需固件或编译器。
- [Host checks](https://github.com/XinmiaoZhao/NikonFirmwarePatch/actions/workflows/host-checks.yml) 在真实 Windows Python 3.12／3.13、Linux 与 macOS 执行路径回归。手动发布门另在 Windows 使用发布源码与哈希固定的同字节预编译单元执行 `prores precapture` 和全选组合，清空 PATH 排除编译器调用，并单独运行 `verify.py`。源码和四份机器码哈希逐项与最终 ZIP 比对；执行记录见 Release 链接。
- 全部 15 种组合、源码／预编译一致性及分发包负控继续在 macOS 核验。

This host-only revision canonicalizes path keys without normalizing source bytes or relaxing integrity checks. Firmware code and recipes are unchanged. The release gate runs matching source and prebuilt units on Windows Python 3.12/3.13, records every source/code hash for comparison with the final ZIP, builds the reported and all-feature selections without a compiler, and independently verifies both outputs. Cross-platform path tests also cover altered and missing inputs. Native-code, QEMU and camera records below are inherited from the unchanged v0.3.0 implementation.

## 构建与启动

- 四项功能的 15 种非空组合均通过独立封装、修改范围、未改字节和版本身份核验；全选组合的源码构建与预编译构建一致。
- 原指令检查覆盖菜单库、功能选择隔离、RAW 剩余张数及刷新、NEF 建头、登记拒绝后的 JPEG 回退和再次尝试。
- 15 种配方具备与 v0.3.0 实现一致的最小 QEMU 启动记录（v0.3.1 的 8 种像素位移配方未重跑），可进入固件版本页并返回重进。此检查使用解密 MAIN、合成外设输入和文件型虚拟卡，检查止于更新入口，不执行刷写。

## 实机与文件

| 功能 | 已完成的检查 |
|---|---|
| ProRes | 两段录像共 294 帧完整解码；编码档位与文件结构对应，菜单库行为由测试者确认 |
| 开放门／N-RAW | 六段录像共 897 帧及对应 897 帧代理完整解码，画幅和码率预算符合设置；机内显示和回放由测试者确认 |
| RAW 连拍／预拍 | 278 个文件的身份、RAW／JPEG 元数据和双卡配对核验，其中 159 NEF、119 JPEG；60 对同类型备份的影像内容一致，NEF 的 RAW 负载相同 |
| 像素位移 | 旧代码（v0.3.0）；测试组均在新建文件夹中拍摄，文件编号从 `0001` 开始；4／32 张组的两份 NEFX 与预先固定的完整输出一致，85 份原片／旧输出未变；MENU、半按和普通关机取消均无新增输出或临时残留 |

文件解码、像素比较和机身操作反馈分别记录；菜单、回放等界面结论来自测试者观察。验证按对应功能实现绑定，代码不变的功能保留其既有记录。这些结果说明已检查的行为，不是对所有场景的可靠性保证。当前已确认的问题和功能限制见[已知问题](known-issues.md)。

## English

The four-feature version passes independent build/byte checks for all 15 selections, source/prebuilt equivalence, bounded native-code checks and implementation-matched minimal QEMU startup checks (v0.3.0 implementation; the eight v0.3.1 pixel-shift recipes were not re-run in QEMU). QEMU uses decrypted MAIN and synthetic peripherals; it does not perform a firmware update.

Camera evidence includes 294 decoded ProRes frames; 897 N-RAW frames and their proxies; a 278-file RAW/JPEG metadata/routing check; and exact 4/32-frame pixel-shift outputs plus cancellation recovery. The pixel-shift camera tests used the v0.3.0 code with groups captured in new folders starting at `0001`. UI behavior is tester-reported. Records are bound to the implementation checked and retained where code is unchanged. See [known issues](known-issues.md#english), the [previous public release](validation-v0.2.0.md), and the [changelog](../CHANGELOG.md).
