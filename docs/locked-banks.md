# 锁定菜单库（原型） / Locked menu banks (prototype)

[简体中文](#简体中文) · [English](#english)

## 简体中文

`--features locked-banks` 让照片拍摄菜单库和自定义设定库像已保存的预设一样工作。在某个库中所做的更改保留到切换离开为止；切换回来时，该库恢复为上次保存的状态。

**原型状态。** 本功能未经审核或实机测试，配方为推导所得、未经审核。已通过离线检查；照片拍摄菜单库和自定义设定库已在模拟器中测试（见[测试覆盖](#测试覆盖)）。请勿用于重要工作。交互菜单中为选项 6，从不包含在选项 5（全部已审核功能）中。

### 行为

| 操作 | 原厂 C 3.11 | 锁定菜单库 |
|---|---|---|
| 在库 A 中更改设定，切换 A → B → A | 更改保留在 A 中 | A 恢复为已保存状态 |
| 把当前设定保存到 A | 离开 A 时自动保存 | 在 A 为当前库时，于库菜单中再次选择 **A** |
| 复制库，来源为当前库 | 先把当前更改保存到来源，再复制 | 复制来源已保存的状态；来源不变 |
| 复制库，目标为当前库 | 当前设定变为复制结果 | 相同 |
| 重设库 | 库恢复默认 | 相同；重设直接写入该库 |
| 关闭**扩展照片菜单库** | 把当前曝光设定保存到当前库 | 不保存到库 |
| 开启**扩展照片菜单库** | 把当前曝光设定保存到共享设定 | 相同 |
| 由批量设定更新切换库（原厂调用 `410df7ec`，例如载入已保存的菜单设定） | 把当前更改保存到离开的库 | 不保存 |
| 不切换库，关机再开机 | 更改保留 | 更改保留；切换离开再回来仍会还原 |

保存方法：**MENU → 照片拍摄菜单 → 照片拍摄菜单库**，高亮当前库并按 **OK**。自定义设定使用**自定义设定库**，方法相同。从 i 菜单或指定按钮选择当前库可能不会保存，请使用菜单。

### 构建

`locked-banks` 可在源码检出中单独构建：

```sh
python patch.py "/path/to/Z_8_0311.bin" --features locked-banks --version 04.09 --tag l0 --output build/locked-banks
python verify.py "/path/to/Z_8_0311.bin" build/locked-banks/Z_8_0409.bin --features locked-banks --version 04.09 --tag l0
```

与预拍、像素位移或开放门组合时，先把 v0.3.0-r1 Release 工具包中的 `resources/*.bin` 机器码复制到 `resources/`。构建会逐项与配方比对，任何不符都会停止。

刷机前，用**设定菜单 → 保存/载入菜单设定 → 保存菜单设定**备份设定。

### 实机测试

每项约 2 分钟。测试 1 至 3 请用一眼可读的设定，例如照片拍摄菜单中的**色调模式**。

1. **锁定。** 在库 A 中记下色调模式，然后更改。切换到库 B，再回到 A。预期：恢复为记下的值。
2. **再次选择即保存。** 在 A 中更改色调模式。在**照片拍摄菜单库**中再次选择 **A**。切换到 B，再回到 A。预期：新值保留。
3. **自定义设定库。** 用**自定义设定库**和某项自定义设定（例如 **a1 AF-C 优先选择**）重复测试 1 和 2。
4. **复制库。** 在 A 中做一项未保存的更改。在**照片拍摄菜单库**中按“管理”按钮，把库 A 复制到库 C。预期：C 为 A 已保存的状态，不含未保存的更改；A 不变。
5. **其他切换方式。** 若按钮或 i 菜单可切换库，用它重复测试 1。预期：结果与测试 1 相同。
6. **关机再开机。** 在 A 中做一项未保存的更改，关机再开机。预期：更改仍在。切换到 B 再回到 A。预期：更改消失。

如有失败，请报告测试编号。

撤销方法：重新安装官方 C 3.11；Z8 支持降级。

### 测试覆盖

| 路径 | 离线字节检查 | 模拟器（[RdWing/z8-qemu](https://github.com/RdWing/z8-qemu)） | 实机 |
|---|---|---|---|
| 照片库锁定（测试 1） | 是 | 通过 | 尚未 |
| 照片库再次选择即保存（测试 2） | 是 | 通过 | 尚未 |
| 自定义设定库锁定与再次选择即保存（测试 3） | 是 | 通过 | 尚未 |
| 复制库、扩展菜单库开关、关机再开机（测试 4–6） | 是 | 尚未 | 尚未 |

模拟器加载与所构建 `Z_8_0409.bin` 相同的 MAIN 代码，并在原厂和补丁固件上并排回放菜单按键。它不执行固件更新，也不模拟存储卡、传感器或关机后的设定保存。

### 实现

[`z8lockbank/patcher.py`](../z8lockbank/patcher.py) 修改五条原厂指令，并在 `408BF900` 加入 12 条指令的例程。相机把当前设定放在数据存储槽 0，库 A–D 放在槽 1–4；普通设定更改只写槽 0。补丁拦截原厂所有从槽 0 复制到库的操作：

| 位置 | 原厂例程 | 改动 |
|---|---|---|
| `410dd26c` | 照片库选择 `410dd1ec` | 仅在所选库为当前库时保存 |
| `410de0a8` | 自定义设定库选择 `410de050` | 相同 |
| `410ddafc` | 复制照片库 `410dda64` | 跳过向来源的保存 |
| `410de62c` | 复制自定义设定库 `410de5a0` | 跳过向来源的保存 |
| `410dd8bc` | 扩展菜单库开关 `410dd84c` | 跳过向当前库的保存 |

这些是原厂中仅有的从槽 0 复制到库槽的调用（已核对槽复制 `41013a14` 的全部 18 处调用）。重设库直接把默认值写入库槽，因此不受影响。ProRes 和开放门新增的设定通过同一逐项库复制移动，遵循相同规则。

## English

`--features locked-banks` makes the photo shooting menu banks and custom settings banks behave like saved presets. Changes you make while in a bank stay until you switch away. Switching back restores the bank as it was last saved.

**Prototype status.** This feature has not been reviewed or tested on a camera, and its recipes are derived, not reviewed. It is offline-checked, and the photo shooting menu bank and custom settings bank are emulator-tested (see [Test coverage](#test-coverage)). Do not use it for important work. In the interactive menu it is option 6 and is never part of option 5 (all reviewed features).

### Behaviour

| Action | Stock C 3.11 | Locked banks |
|---|---|---|
| Change a setting in bank A, switch A → B → A | Change is kept in A | A returns to its saved state |
| Save the current settings into A | Happens automatically when you leave A | Select **A** again in the bank menu while A is active |
| Copy bank, source is the active bank | Saves live changes into the source, then copies | Copies the source's saved state; the source is unchanged |
| Copy bank, destination is the active bank | Live settings become the copy | The same |
| Reset a bank | Bank returns to defaults | The same; the reset is stored in the bank directly |
| Turn **Extended photo menu banks** off | Saves live exposure settings into the active bank | Does not save into the bank |
| Turn **Extended photo menu banks** on | Saves live exposure settings into the shared set | The same |
| Bank changed by a batch settings update (stock caller `410df7ec`, for example loading saved menu settings) | Saves live changes into the bank being left | Does not save |
| Power off and on without switching | Changes kept | Changes kept; switching away and back still reverts them |

To save, use **MENU → Photo shooting menu → Shooting menu bank**, highlight the active bank and press **OK**. For custom settings, use **Custom settings bank** the same way. Selecting the active bank from the i menu or an assigned control may not save; use the menu.

### Build

`locked-banks` builds on its own from a source checkout:

```sh
python patch.py "/path/to/Z_8_0311.bin" --features locked-banks --version 04.09 --tag l0 --output build/locked-banks
python verify.py "/path/to/Z_8_0311.bin" build/locked-banks/Z_8_0409.bin --features locked-banks --version 04.09 --tag l0
```

To combine it with pre-capture, pixel shift or open gate, first copy that toolkit's `resources/*.bin` units from the v0.3.0-r1 Release into `resources/`. The build compares every edit with the recipe and stops on any mismatch.

Before flashing, save your settings with **Setup menu → Save/load menu settings → Save menu settings**.

### Camera test

Each test takes about 2 minutes. For tests 1 to 3, use a setting you can read at a glance, such as **Tone mode** in the photo shooting menu.

1. **Lock.** In bank A, note the tone mode, then change it. Switch to bank B, then back to A. Expected: the noted value is back.
2. **Save by re-selecting.** In A, change tone mode. In **Shooting menu bank**, select **A** again. Switch to B, then back to A. Expected: the new value stays.
3. **Custom settings bank.** Repeat tests 1 and 2 with a custom setting, for example **a1 AF-C priority selection**, using **Custom settings bank**.
4. **Copy bank.** In A, make an unsaved change. In **Shooting menu bank**, press the Manage button and copy bank A to bank C. Expected: C has A's saved state, without the unsaved change, and A is unchanged.
5. **Other ways of switching.** If a control or the i menu switches banks, repeat test 1 with it. Expected: the same result as test 1.
6. **Power cycle.** In A, make an unsaved change and turn the camera off and on. Expected: the change is still there. Switch to B and back to A. Expected: the change is gone.

Report any test that fails, with its number.

To undo, install official C 3.11 again; Z8 accepts downgrades.

### Test coverage

| Path | Offline byte checks | Emulator ([RdWing/z8-qemu](https://github.com/RdWing/z8-qemu)) | Camera |
|---|---|---|---|
| Photo bank lock (test 1) | Yes | Pass | Not yet |
| Photo bank save by re-selecting (test 2) | Yes | Pass | Not yet |
| Custom settings bank lock and save by re-selecting (test 3) | Yes | Pass | Not yet |
| Copy bank, extended banks toggle, power cycle (tests 4–6) | Yes | Not yet | Not yet |

The emulator run loads the same MAIN code as the built `Z_8_0409.bin` and replays menu button presses on stock and patched firmware side by side. It does not perform a firmware update or model the card, sensor or storage of settings across power cycles.

### Implementation

[`z8lockbank/patcher.py`](../z8lockbank/patcher.py) changes five stock instructions and adds a 12-instruction routine at `408BF900`. The camera keeps live settings in data-store slot 0 and banks A–D in slots 1–4. Ordinary setting changes write only slot 0. The patch gates every stock copy from slot 0 into a bank:

| Site | Stock routine | Change |
|---|---|---|
| `410dd26c` | photo bank select `410dd1ec` | save only when the selected bank is the active one |
| `410de0a8` | custom bank select `410de050` | the same |
| `410ddafc` | copy photo bank `410dda64` | skip the save into the source |
| `410de62c` | copy custom bank `410de5a0` | skip the save into the source |
| `410dd8bc` | extended banks toggle `410dd84c` | skip the save into the active bank |

These are the only stock calls that copy slot 0 into a bank slot (all 18 callers of the slot copy `41013a14` were checked). Bank resets write default values into the bank slot directly, so they are unaffected. Settings added by ProRes and open gate move with the same per-item bank copy, so they follow the same rule.
