# Log 设置与后期流程 / Log settings and post-production

[中文](#机内设置与适用范围) · [English](#english)

**当前采用经实拍标定的 M1 与常量 Cpxs，保留原厂截零。** 测量数据和覆盖范围见[色彩报告](log-colour-report.md)。以下说明各档素材的输入解释与后期转换顺序。

## 机内设置与适用范围

`--features log-colour` 提供三档：

| 机内选择 | 后期输入色域 / Input gamut | 后期输入曲线 / Input gamma |
|---|---|---|
| N-Log | Rec.2020 / BT.2020 | Nikon N-Log |
| S-Log3 | Sony S-Gamut3.Cine | Sony S-Log3 |
| Log3G10 | REDWideGamutRGB | RED Log3G10 |

1. 选择支持 Log 的录像类型，例如 H.265 10-bit 或 ProRes 422，并选择 Log 色调。
2. 在视频拍摄菜单的“Log 设定”中选择所需类型；它按视频拍摄菜单库保存。
3. 按需开启机内显示辅助。辅助只影响监看，不烘焙进录像；后期仍须按原 Log 类型解释。

全选固件已实机验证已有和新录 N-RAW 代理回放。取景图标、适用的片段元数据随所选类型对应。回放名称与显示辅助按片段识别，返回取景后恢复菜单选择。S-Log3 保留非负截断，菜单没有截零测试行。

**以下步骤用于已编码的 H.265／ProRes 422 Log 片段。** N-RAW、ProRes RAW 走各软件的 RAW 解码路径；机内选了 S-Log3 或 Log3G10，不等于 RAW 已编码成该曲线。RAW 的色调分类保留原厂行为。

## 自动识别：已有测试说明了什么

已有软件测试使用 **Final Cut Pro 11.2** 和 **DaVinci Resolve 21.1.2（免费版）**。其中包含只改元数据的样片，验证的是软件识别结果；不是最终组合包在各软件中的完整调色验收，也不证明颜色准确度。

| 软件 | 已观察到的行为 | 使用当前补丁素材时应做什么 |
|---|---|---|
| Resolve | 对应当前 S-Log3／Log3G10 写法的 Nikon 色调标签被识别为 `Rec709 (Scene)`；修改 Apple 的色彩键没有让它改认 S-Log3 | 在媒体池里手动指定实际输入色域和曲线。只改项目默认输入不够，片段的明确标签可能仍优先 |
| FCP | 带相应色彩键的 ProRes 和 H.265 样片可选择 `Nikon N-Log` 或 `Sony S-Log3/S-Gamut3.Cine`；不带该键时显示 `None` | 导入后检查“相机 LUT”。S-Log3 应使用带 **Cine** 的选项；Log3G10 按下面的自定转换流程处理 |

当前补丁为 N-Log／S-Log3 写入相应色彩键，Log3G10 不借用 N-Log 或 Sony 的相机 LUT 标识。因此，**`Rec709 (Scene)` 或 `None` 不代表 Log 画面已还原**。软件升级后也应复核设置，不假定识别行为永远相同。其他后期软件也按输入表指定色域／曲线，或使用输入、输出明确的技术 LUT；没有本仓库识别测试的软件，不预设它能自动识别。

## DaVinci Resolve

### 方案 A：使用项目色彩管理

1. 打开“项目设置 → 色彩管理”（Project Settings → Color Management），将 Color science 设为 **DaVinci YRGB Color Managed**。关闭 Automatic color management，以便明确指定设置。
2. 以 SDR Rec.709 交付为例，可选自定色彩处理，将 Timeline color space 设为 **DaVinci Wide Gamut / DaVinci Intermediate**，Output color space 设为 **Rec.709 / Gamma 2.4**。HDR 项目应改用实际交付目标；输入类型不随输出目标改变。
3. 在媒体池中按拍摄类型分组多选片段，右键 **Input Color Space**，指定上表的完整组合。若版本分别显示 Input Color Space 与 Input Gamma，就分别指定两项。不要把 S-Gamut3 与 **S-Gamut3.Cine** 混用。
4. 对 S-Log3／Log3G10 确认片段不再保留误识别的 `Rec709 (Scene)`。调色时由项目完成输入和输出转换，节点中不要再叠同一套 Log→Rec.709 还原 LUT 或输入 CST。

批量指定片段输入的方式见 [Blackmagic Design《Colorist Guide》色彩管理章节](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Colorist-Guide.pdf)。这里的 SDR 设置是一种明确的工作流示例，不是所有交付的统一标准。

### 方案 B：手动使用 CST 节点

若希望把转换过程直接放在节点里，项目 Color science 选 **DaVinci YRGB**，自行建立输入和输出变换。不要同时让方案 A 再做一次输入转换。

`素材 Log → 输入 CST → 工作空间内调色 → 输出 CST → 交付空间`

| 节点 | Color Space Transform 设置 |
|---|---|
| 输入 CST | Input Color Space / Input Gamma 按机内类型选上表组合；Output Color Space = DaVinci Wide Gamut，Output Gamma = DaVinci Intermediate |
| 输出 CST（SDR 示例） | Input Color Space = DaVinci Wide Gamut，Input Gamma = DaVinci Intermediate；Output Color Space = Rec.709，Output Gamma = Gamma 2.4 |

双 CST 的组织方式及 Nikon N-Log 输入选项可参照 [Nikon 的 Resolve 编辑指南](https://nps.nikonimaging.com/technical_info/technical_solutions/z_cinema_tips/guide/en/edit_with_davinci_resolve_13.html)。Log3G10 的输入要用 **REDWideGamutRGB / Log3G10**，不能因文件来自 Nikon 就选 N-Log。这里没有验证并保证与 FCP 内置相机 LUT 的观感相同。

**电平是另一项设置。** Clip Attributes → Data Levels 可先保持 Auto；现有识别测试没有证明所有格式都应强制 Full 或 Video。若黑白位异常，应核对具体素材的范围标记和解码结果，不要用电平切换补偿错误的输入色彩空间。

## Final Cut Pro

### 资源库与项目

为保留 Log 处理的余量，可把资源库 Color Processing 设为 **Wide Gamut HDR**；若交付 SDR，项目 Color Space 仍选 **Standard – Rec.709**。资源库处理空间和项目输出是两件事，使用宽色域资源库不要求交付 HDR。[Apple：宽色域 HDR 处理](https://support.apple.com/guide/final-cut-pro/ver1cd9629a5/mac)

### N-Log 与 S-Log3

导入后选中浏览器片段，打开“信息检查器”（⌘4 → Info），Metadata View 选 **Settings**，检查 **Camera LUT**：

- N-Log：`Nikon N-Log`。
- S-Log3：`Sony S-Log3/S-Gamut3.Cine`。如果自动识别为 None 或选错，手动改成这一项。

用相机 LUT 完成转换后，不要在片段上再叠同样的 Log→Rec.709 Custom LUT。相机 LUT 在片段效果之前运行，并作用于资源库中该媒体的所有实例；时间线中的自定 LUT 效果是另一层处理。[Apple：相机 LUT 与自定 LUT](https://support.apple.com/guide/final-cut-pro/ver24f966423/mac)

### Log3G10

在测试过的 FCP 版本中，没有可用于这类 Z8 片段的内置 RWG／Log3G10 相机 LUT；不能替选 `Nikon N-Log` 或 Sony 的 LUT。

对于普通 SDR 交付，可在 Camera LUT 菜单选择 **Add Custom Camera LUT**，导入明确标注 **RWG / Log3G10 → Rec.709** 的技术 LUT，并把导入对话框的 **Output Color Space** 设为该 LUT 的实际输出 Rec.709。RED 的 IPP2 Output Presets 是这类显示变换的一种来源；不同对比度／高光过渡预设会改变观感。[Nikon 对 IPP2 输出预设的说明](https://nps.nikonimaging.com/technical_info/technical_solutions/z_cinema_tips/guide/en/edit_with_davinci_resolve_13.html)

这是依据软件接口和 LUT 输入／输出定义整理的手动流程，**尚无本仓库最终组合素材逐片完成这条 FCP 流程的验收记录**。选用已经输出 Rec.709 的 LUT 后，后续处理应以它的输出为准，不能再把它解释成原始 Log。

## 可选 F LUT：不是还原 LUT

仓库的 [65³ F 模型 LUT](../luts/README.md)输入、输出均为 **RWG / Log3G10**，只近似增加参照 RED 解码路径中的饱和度映射。它不把 Log 变成 Rec.709；录像矩阵的标定与 F 映射各自独立。

- **Resolve：** 如果节点已经处于 DaVinci Wide Gamut / Intermediate，在完成白平衡后，用 CST 转到 RWG / Log3G10 → F LUT → CST 转回工作空间，再继续调色／输出。夹住 F 的这对 CST 只做空间转换，不加额外的色调映射或色域压缩。若输入本来就是未经转换的 RWG / Log3G10，可在显示变换前直接放 F。导入 `.cube` 可用 Project Settings → Color Management → Open LUT Folder，放入文件后 Update Lists；插值可设 Tetrahedral。
- **FCP：** 不要把这个 Log→Log 的 F LUT 直接当作唯一的 Camera LUT，也不要放在已经转换完成的相机 LUT 后。若要用相机 LUT 路径同时加入 F，需要另备包含 **F＋显示变换**、输出空间明确的组合 LUT；本仓库尚未提供或验证这种组合。当前可先在有明确 RWG／Log3G10 节点的流程中完成 F，再交给 FCP 处理。
- **RAW 参照：** 已经经由本项目参照的 RED 解码路径引入 F 的素材，不再加一次。N-RAW 在 Resolve 中先核对 Camera RAW 的实际解码输出；本项目保留的原生 N-Log 默认是 Rec.2020 / Nikon N-Log。ProRes RAW 未做同等的标签对照测试，不外推其软件行为。

F LUT 的数值核验、使用顺序和限制见 [LUT 说明](../luts/README.md)。上述位置说明不等于已在两款软件中完成 F LUT 的端到端画面验收。

## 色彩依据

[中文色彩报告](log-colour-report.md)与[英文版](log-colour-report.en.md)给出当前两套录像矩阵的实拍色卡数据、简化链路模拟，以及机内显示辅助的来源与目标。

## English

**The current data use the camera-tested M1 matrices and constant Cpxs, retaining stock clamping.** Measurements and coverage are in the [colour report](log-colour-report.en.md). The settings below describe source interpretation and post-production conversion order.

### Camera and clip scope

Choose a Log-capable mode such as 10-bit H.265 or ProRes 422, select Log tone, then select N-Log, S-Log3 or Log3G10 in Log settings. The choice is stored per movie bank. View assist is for monitoring and is not baked into the recording. Playback follows the clip; returning to live view restores the menu choice. S-Log3 keeps the non-negative clamp.

Use these input pairs:

| Camera choice | Input gamut | Input gamma |
|---|---|---|
| N-Log | Rec.2020 / BT.2020 | Nikon N-Log |
| S-Log3 | Sony S-Gamut3.Cine | Sony S-Log3 |
| Log3G10 | REDWideGamutRGB | RED Log3G10 |

These instructions cover encoded H.265/ProRes 422 clips. N-RAW and ProRes RAW retain their native RAW classification and require the application's RAW decode workflow; the camera's Log-menu choice does not establish their decoded output space.

### What the existing tests establish

Metadata tests used **Final Cut Pro 11.2** and **DaVinci Resolve 21.1.2 Free**. Some samples changed tags only: they test recognition, not colour accuracy or the final combined firmware.

- Resolve identified the Nikon tag used by the current S-Log3/Log3G10 implementation as `Rec709 (Scene)`. Changing the Apple colour key did not make it recognise S-Log3. Explicitly override each clip's input; changing only the project default may leave the clip tag in effect.
- FCP selected Nikon N-Log or Sony S-Log3/S-Gamut3.Cine for appropriately tagged ProRes and H.265 samples; removing the key gave None. Check Camera LUT after import. The current Log3G10 implementation does not borrow a Nikon/Sony camera-LUT identifier.

`Rec709 (Scene)` and `None` do not mean that the recorded Log image has already been converted. Recheck behaviour when changing software versions. In other editors, assign the table's input pair or use a technical LUT with explicit input/output spaces; automatic recognition has not been established by this repository.

### Resolve: managed or explicit CST workflow

For managed grading, choose **DaVinci YRGB Color Managed** in Project Settings → Color Management and disable Automatic color management. An SDR example uses a **DaVinci Wide Gamut / DaVinci Intermediate** timeline and **Rec.709 / Gamma 2.4** output. Group clips by recording type in the media pool, right-click Input Color Space and explicitly assign the pair in the table; assign gamut and gamma separately if your version exposes separate controls. Confirm that S-Log3/Log3G10 clips no longer retain the mistaken Rec709 (Scene) input. Do not add a duplicate input CST or Log-to-display LUT. [Blackmagic Design guide](https://documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-20-Colorist-Guide.pdf)

Alternatively, choose **DaVinci YRGB** and handle transforms in nodes:

`source Log → input CST → grading in DWG/Intermediate → output CST → delivery`

The first CST uses the table's input pair and outputs DaVinci Wide Gamut / DaVinci Intermediate. The last CST converts that working pair to Rec.709 / Gamma 2.4 for the SDR example. Use the actual delivery target for HDR. This does not promise the same rendering as an FCP camera LUT. [Nikon's CST workflow](https://nps.nikonimaging.com/technical_info/technical_solutions/z_cinema_tips/guide/en/edit_with_davinci_resolve_13.html)

Data Levels is separate from colour-space assignment. Start with Clip Attributes → Data Levels → Auto; the recognition tests do not justify forcing Full or Video for every format. Investigate a specific clip's range flags and decoding if black/white levels are wrong.

### Final Cut Pro

Use **Wide Gamut HDR** library processing to retain Log-processing headroom; an SDR project can still use **Standard – Rec.709**. Library processing does not determine that the delivery must be HDR. [Apple library/project settings](https://support.apple.com/guide/final-cut-pro/ver1cd9629a5/mac)

Select a browser clip, open the Info inspector (⌘4), choose the Settings metadata view and check Camera LUT. Use **Nikon N-Log** for N-Log, or **Sony S-Log3/S-Gamut3.Cine** for S-Log3; correct None or an incorrect selection manually. Do not add a second equivalent conversion. Camera LUTs affect all instances of the media in the library and precede clip effects. [Apple LUT controls](https://support.apple.com/guide/final-cut-pro/ver24f966423/mac)

For Log3G10, the tested FCP version has no suitable built-in RWG/Log3G10 camera LUT for these clips. For SDR, use **Add Custom Camera LUT** with a technical **RWG/Log3G10 → Rec.709** LUT, and set its imported **Output Color Space** to the LUT's actual Rec.709 output. RED IPP2 output presets are one source; contrast/highlight-roll-off choices affect rendering. [Nikon's IPP2 preset description](https://nps.nikonimaging.com/technical_info/technical_solutions/z_cinema_tips/guide/en/edit_with_davinci_resolve_13.html)

This manual route follows documented interfaces and LUT contracts; it has not received an end-to-end test with the final combined firmware. Do not reinterpret an already converted Rec.709 result as source Log.

### Optional F processing and RAW

The supplied [65³ F-model LUT](../luts/README.md) maps **RWG/Log3G10 to RWG/Log3G10**. It is optional saturation processing, not a display conversion or a recalibration of the recording matrices.

- In Resolve, after white balance, convert the working space to RWG/Log3G10, apply F, and convert back before subsequent grading/output. Use no tone/gamut mapping in this conversion pair. If the node already receives unconverted RWG/Log3G10, place F before the display transform. Import the CUBE through Open LUT Folder / Update Lists; use tetrahedral interpolation when available.
- In FCP, F alone is not a valid replacement for the camera's Log-to-working/display conversion, and adding it after an active camera LUT gives it the wrong input. A camera-LUT route needs a separately prepared **F plus display transform** LUT with a defined output; this repository has not supplied or tested one. An explicit RWG/Log3G10 pipeline can apply F before handing off to FCP.
- Do not add F again to footage already processed through the reference RED decode path. For N-RAW, inspect Camera RAW's actual output; the retained native N-Log default in the existing Resolve test was Rec.2020 / Nikon N-Log. ProRes RAW did not receive the equivalent tag comparison.

See the [LUT documentation](../luts/README.md) for its numerical checks and limits. No end-to-end F-LUT UI acceptance in either editor is claimed. The [English colour report](log-colour-report.en.md) presents the current camera measurements and simulated colour shifts with simplified processing.
