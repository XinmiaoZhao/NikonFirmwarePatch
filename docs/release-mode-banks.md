# 释放模式随照片拍摄菜单库切换 / Release mode per photo shooting menu bank

[简体中文](#简体中文) · [English](#english)

## 简体中文

> 本节中文由 AI 根据英文原文翻译。

### 功能

使用 `--features raw-precapture` 时，若“照片拍摄菜单”中的**扩展菜单库**为“开启”，释放模式（单张拍摄、低速连拍、高速连拍、C15、C30、C60、C120 和自拍）会保存在每个照片拍摄菜单库（A–D）中，选择该菜单库时恢复。例如：菜单库 A = C30，菜单库 B = 高速连拍，菜单库 C = 单张拍摄。对应[问题 #41](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/41)第 1 项。

**状态：已在 Z8 机身上测试（固件 03.12.r2，与本分支相同的代码与地址）：扩展菜单库开启，菜单库 A = C30、B = 高速连拍、C = 单张拍摄，在菜单库之间切换时恢复各自的释放模式。扩展菜单库开／关、“复制”以及关机后保持尚未报告测试结果。**

### 行为

- 扩展菜单库为“关闭”时，行为与原厂相同：切换菜单库不改变释放模式。将其关闭时，恢复开启之前使用的释放模式（“全局”值），与原厂对曝光模式、快门速度和光圈的处理相同；再次开启时恢复当前菜单库的释放模式。
- 与其他菜单库设置一样，释放模式在切换到另一个菜单库时存入原菜单库。安装后，每个菜单库在以所需释放模式离开一次之前，保持当前的释放模式。
- 所有选择菜单库的方式均有效：照片拍摄菜单、i 菜单、指定为“照片拍摄菜单库”的按钮以及 PTP。
- “管理菜单库”›“复制”会连同菜单库一起复制释放模式。
- 切换到 C15–C120 时的附带调整与用释放模式按钮选择该模式时相同（原厂规则）。
- 低速连拍和高速连拍的拍摄速度以及预拍选项（预拍连拍和释放后连拍，DS 02001C11h／02001C12h）不在此列：与原厂一样跟随“自定义设定库”。
- “重设照片拍摄菜单”不改变已保存的释放模式；恢复出厂设置（“重设所有设定”）会将其清除。存储卡上的“保存／载入菜单设定”不包含这些值。
- 没有菜单项，不新增字符串。

### 原理

- 释放模式由 DS 06000108h（0 单张，1 连拍，4 自拍）和 0600010Ah（0 低速，1 高速，3 C30，4 C120，5 C60，6 C15）表示。二者位于设置组 1，该组没有菜单库存储，因此不能直接加入菜单库列表（0xA0299E888，465 项）。
- 存储：设置组 1Eh 填充区中的五个空闲字节（随该组保存，不分菜单库，默认值 0）：A–C 为 0xA03D732B1–B3，D 为 0xA03D732B9，全局值为 0xA03D732BA。字节 = 0x80 | 模式 << 4 | 连拍类型；0 表示从未保存（释放模式保持不变）。
- 原厂设置引擎的规则只执行一层（请求先入队，再调用该项的规则；规则排入的从属更改不再执行各自的规则），因此本功能把每项更改连同原厂规则的从属更改一起入队，与用户请求更改释放模式时相同；只入队实际改变的值，连拍类型仅在连拍模式下恢复。
- 四处单字钩子（均核对原厂字节）：

| 位置 | 原厂指令 | 作用 |
|---|---|---|
| 0x410DD4D8 | `bl 0x41012CF0`（菜单库切换规则 0x410DD1EC 中 C 档检查的批量读取） | 把当前释放模式存入离开的菜单库，把新菜单库的释放模式排入该规则的更改列表，并把新值交给原厂 C 档检查，使从 C30 菜单库切换到单张菜单库时不会重设后者的设置 |
| 0x410E95A8 | `b 0x410DD84C`（扩展菜单库规则） | 开启／关闭时在全局值与菜单库值之间切换 |
| 0x410D71E0 | `bl 0x410DDA64`（复制菜单库） | 复制源菜单库的释放模式字节 |
| 0x410DDE5C | `bl 0x41012CF0`（复制到当前菜单库时的 C 档检查） | 恢复复制得到的释放模式 |

- 代码：`z8relbank/patcher.py`，用 `z8prores.a64.Block` 汇编为 0x409FF800 处的 1,044 字节，没有编译单元（`resources/compiled.json` 不变）。仅选 `raw-precapture` 时，代码复制边界由 0x409FA000 变为 0x40A00000，以覆盖整个预拍代码区（`z8patch/contract.py` 相应调整，并检查四处钩子仅在选择 `raw-precapture` 时存在）。`resources/combinations.json` 中包含 `raw-precapture` 的 8 种配置各增加 5 行，仅选 `raw-precapture` 的配置另有复制边界一行改变，其余不变。

## English

### What it does

Installed with `--features raw-precapture`. With **Extended menu banks** On in the Photo shooting menu, the release mode (Single frame, Continuous L, Continuous H, C15, C30, C60, C120 and self-timer) is stored in each photo shooting menu bank (A–D) and restored when that bank is selected. Example: bank A = C30, bank B = Continuous H, bank C = Single frame. Item 1 of [issue #41](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/41).

**Status: tested on a Z8 (firmware 03.12.r2, the same code at the same address as this branch): with Extended menu banks On, bank A = C30, B = Continuous H, C = Single frame; switching between the banks restores each bank's release mode. Extended menu banks On/Off, Copy and retention after power-off have not been reported yet.**

### Behaviour

- Extended menu banks Off: stock behaviour; selecting a bank does not change the release mode. Turning it Off restores the release mode that was in use before it was turned On (the "global" value), as the stock firmware does for exposure mode, shutter speed and aperture; turning it On again restores the bank's.
- Like the other bank settings, the release mode is saved into a bank when another bank is selected. After installing, each bank keeps the current release mode until it has been left once with the wanted mode.
- Works with every way of selecting a bank: the Photo shooting menu, the i menu, a button assigned to "Photo shooting menu bank", and PTP.
- Manage menu banks › Copy copies the release mode with the bank.
- The side effects of C15–C120 are applied as when the mode is chosen with the release mode button (stock rules).
- The Continuous L and Continuous H frame rates and the Pre-Release Capture options (pre-release and post-release burst, DS 02001C11h/02001C12h) are not included: they follow the Custom settings bank, as in stock firmware.
- Reset photo shooting menu does not change the stored release modes; a factory reset ("Reset all settings") clears them. Save/load menu settings on a memory card does not include them.
- No menu item and no strings.

### How it works

- The release mode is DS 06000108h (0 single, 1 continuous, 4 self-timer) and 0600010Ah (0 CL, 1 CH, 3 C30, 4 C120, 5 C60, 6 C15). Both are in settings group 1, which has no bank storage, so they cannot simply be added to the bank list (0xA0299E888, 465 items).
- Storage: five spare bytes in the padding of settings group 1Eh (saved with the group, not banked, default 0): A–C at 0xA03D732B1–B3, D at 0xA03D732B9, the global value at 0xA03D732BA. Byte = 0x80 | mode << 4 | kind; 0 = never stored (the release mode is left as it is).
- The stock settings engine runs rules one level deep (a request is queued, then its rule runs; dependents a rule queues are applied without their own rules). The module therefore queues each change together with the stock rule's dependents, as a release-mode request would. Only values that change are queued; the kind is restored only for a continuous mode.
- Four one-word hooks, each checked against the stock word:

| Site | Stock instruction | Purpose |
|---|---|---|
| 0x410DD4D8 | `bl 0x41012CF0` (batch get for the C-mode check in the bank rule 0x410DD1EC) | saves the live release mode into the bank being left, queues the new bank's release mode into the rule's change list and hands the new values to the stock C-mode check, so a switch from a C30 bank to a Single-frame bank does not reset the latter's settings |
| 0x410E95A8 | `b 0x410DD84C` (Extended menu banks rule) | On/Off switches between the global and the bank value |
| 0x410D71E0 | `bl 0x410DDA64` (copy bank) | copies the source bank's release-mode byte |
| 0x410DDE5C | `bl 0x41012CF0` (C-mode check when copying into the selected bank) | restores the copied release mode |

- Code: `z8relbank/patcher.py`, 1,044 bytes at 0x409FF800 assembled with `z8prores.a64.Block`; no compiled unit (`resources/compiled.json` is unchanged). For the RAW-only selection the text copy boundary moves from 0x409FA000 to 0x40A00000 so that the whole pre-capture cave is copied (`z8patch/contract.py` follows, and checks that the four hooks are present exactly when `raw-precapture` is selected). In `resources/combinations.json` each of the 8 profiles with `raw-precapture` gains 5 rows, and the RAW-only profile's copy-boundary row changes; nothing else changes.
