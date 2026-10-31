# 当前版本验证 / Current validation

适用于 v0.3.0 四功能版本及 v0.3.0-r1 主机工具修订。上一公开版为 [v0.2.0](validation-v0.2.0.md)，功能变化见[更新日志](../CHANGELOG.md)。[机器可读摘要](validation-summary.json)保留验证项目及证据哈希。

## r1 主机验证 / Host revision checks

本次修订只统一源码身份键的路径表示；源码仍按原始字节计算 SHA-256。四份补丁机器码与全部组合配方沿用 v0.3.0，同身份、同功能选择应生成相同固件字节。下述原指令、QEMU 与实机记录仍绑定原功能实现，本次不新增设备安全结论。

- `tests/test_compiled_paths.py` 用独立清单、真实文件及 Python 的 Windows 路径语义检验加载器，覆盖四份补丁、两种加载模式，以及改动源码／机器码、缺失／额外文件的拒绝路径。无需固件或编译器。
- [Host checks](https://github.com/XinmiaoZhao/NikonFirmwarePatch/actions/workflows/host-checks.yml) 在真实 Windows Python 3.12／3.13、Linux 与 macOS 执行路径回归。手动发布门另在 Windows 使用发布源码与哈希固定的同字节预编译单元执行 `prores precapture` 和全选组合，清空 PATH 排除编译器调用，并单独运行 `verify.py`。源码和四份机器码哈希逐项与最终 ZIP 比对；执行记录见 Release 链接。
- 全部 15 种组合、源码／预编译一致性及分发包负控继续在 macOS 核验。

This host-only revision canonicalizes path keys without normalizing source bytes or relaxing integrity checks. Firmware code and recipes are unchanged. The release gate runs matching source and prebuilt units on Windows Python 3.12/3.13, records every source/code hash for comparison with the final ZIP, builds the reported and all-feature selections without a compiler, and independently verifies both outputs. Cross-platform path tests also cover altered and missing inputs. Native-code, QEMU and camera records below are inherited from the unchanged v0.3.0 implementation.

## 构建与启动

- 四项功能的 15 种非空组合均通过独立封装、修改范围、未改字节和版本身份核验；全选组合的源码构建与预编译构建一致。
- 原指令检查覆盖菜单库、功能选择隔离、RAW 剩余张数及刷新、NEF 建头、登记拒绝后的 JPEG 回退和再次尝试。
- 15 种配方具备与实现一致的最小 QEMU 启动记录，可进入固件版本页并返回重进。此检查使用解密 MAIN、合成外设输入和文件型虚拟卡，检查止于更新入口，不执行刷写。

## 实机与文件

| 功能 | 已完成的检查 |
|---|---|
| ProRes | 两段录像共 294 帧完整解码；编码档位与文件结构对应，菜单库行为由测试者确认 |
| 开放门／N-RAW | 六段录像共 897 帧及对应 897 帧代理完整解码，画幅和码率预算符合设置；机内显示和回放由测试者确认 |
| RAW 连拍／预拍 | 278 个文件的身份、RAW／JPEG 元数据和双卡配对核验，其中 159 NEF、119 JPEG；60 对同类型备份的影像内容一致，NEF 的 RAW 负载相同 |
| 像素位移 | 测试组均在新建文件夹中拍摄，文件编号从 `0001` 开始；4／32 张组的两份 NEFX 与预先固定的完整输出一致，85 份原片／旧输出未变；MENU、半按和普通关机取消均无新增输出或临时残留 |

文件解码、像素比较和机身操作反馈分别记录；菜单、回放等界面结论来自测试者观察。验证按对应功能实现绑定，代码不变的功能保留其既有记录。这些结果说明已检查的行为，不是对所有场景的可靠性保证。当前已确认的问题和功能限制见[已知问题](known-issues.md)。

## English

The current four-feature version passes independent build/byte checks for all 15 selections, source/prebuilt equivalence, bounded native-code checks and implementation-matched minimal QEMU startup checks. QEMU uses decrypted MAIN and synthetic peripherals; it does not perform a firmware update.

Camera evidence includes 294 decoded ProRes frames; 897 N-RAW frames and their proxies; a 278-file RAW/JPEG metadata/routing check; and exact 4/32-frame pixel-shift outputs plus cancellation recovery. The pixel-shift test groups were captured in new folders with file numbering starting at `0001`. UI behavior is tester-reported. Records are bound to the implementation checked and retained where code is unchanged. See [known issues](known-issues.md#english), the [previous public release](validation-v0.2.0.md), and the [changelog](../CHANGELOG.md).
