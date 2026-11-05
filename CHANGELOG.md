# v0.4.0-rc.1 — 2026-11-05

四组安装选项统一为画幅、视频品质、Log 色彩与照片工具。新增反挤压、H.265 五档码率、ProRes HQ 星标与三档 Log；RAW 预拍增加 DX 与无损选择回退 HE★，像素偏移支持任意起始编号。开放门继续与 N-RAW 四档绑定。共享菜单、设置复制、星标和资源布局已统一。

2026-11-05：采用经实拍标定的 M1 与常量 Cpxs；三档菜单、原厂截零及按片段回放修复保留。色彩报告给出机身录像相对 N-RAW 的误差，并模拟简化链路产生的偏色。N-RAW 旧录与新录素材的片段 Log 名称及辅助观感已上机确认。

English: the 2026-11-05 revision adopts the camera-tested matrices and constant Cpxs, with three choices, stock clamping and per-clip playback retained. The report now contains camera measurements and common-input simulations of simplified colour processing. On-camera playback showed the expected Log name and assist appearance for existing and newly recorded N-RAW clips. Four build groups add desqueeze, H.265 quality, ProRes HQ stars, selectable Log colour, DX pre-capture and HE★ fallback, with updated pixel-shift group recognition. See the [colour report](docs/log-colour-report.md) and optional [post-production F LUT](luts/README.md).

# Changelog / 更新日志

## v0.3.1 (未单独发布 / unreleased intermediate revision) — 2026-11-04

- 修复 [issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17)：像素位移合成只识别起始文件编号除以 2048 余 1 的组（如 `0001`、`2049`），其他组被拒而列表为空。MakerNote `0x0056` 的第 4–7 字节是连拍起始文件字（卡槽、文件夹、文件编号、类型），旧版把其低 16 位当作固定值 `0x0022`。
- 现按字段核对起始文件字（文件夹 100–999、文件编号 1–9999、类型为 NEF、最高两位为 0），并以整字作为组身份。任意起始编号、同一文件夹中连续拍摄的多组、跨过 `DSC_9999` 进入下一文件夹的组、卡槽 2 的组均可识别和合成；不再需要“新建文件夹”和“重置文件编号”。
- 其余检查不变：版本、像素位移状态、帧数与序号、相机序列号、快门起点、位移、裁切、曝光和白平衡。合成流程与输出格式不变，日志中的组 `id` 为起始文件字的十进制值。
- 只改像素位移机器码 `pixelshift.bin`（130,456 → 130,520 B）及 8 种含像素位移组合中的同一个代码窗口；其他三份机器码、7 种不含像素位移的组合配方及构建与核验程序（`patch.py`、`verify.py`、源码与机器码加载器）与 v0.3.0-r1 相同；维护者配方导出器只改配方 ID 前缀，预编译 CLI 回归改用新的示例版本号。
- 含像素位移的选择请用新的固件版本号重新构建（示例 05.25）。未选像素位移的已装固件无需重刷。此修复已通过主机回归、独立核验和 QEMU 运行，尚未在相机上以新编号实拍组验证。

English: fixes [issue #17](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/17), where pixel-shift merge accepted only groups whose first file number is 1 mod 2048 (e.g. `0001`, `2049`) and showed an empty list otherwise. Bytes 4–7 of MakerNote `0x0056` hold the burst start-file word (slot, folder, file number, type); the scanner had compared its low 16 bits with a constant `0x0022`. The word is now checked by field (folder 100–999, file 1–9999, NEF type, top two bits zero) and the whole word identifies the group. Any starting number, several groups in one folder, groups rolling over `DSC_9999` and slot-2 groups are recognized; New folder and Reset file numbering are no longer required. All other checks and the merge itself are unchanged. Only `pixelshift.bin` (130,456 → 130,520 B) and one code window in the eight pixel-shift recipes changed; other machine code, the seven other recipes and the build/verification programs (`patch.py`, `verify.py`, source and machine-code loaders) are unchanged from v0.3.0-r1; the maintainer recipe exporter changes only the recipe ID prefix and the prebuilt CLI regression uses the new example version. Rebuild pixel-shift selections with a new firmware version number (05.25 in the README). The fix passed host regression, independent verification and a QEMU run; it has not yet been confirmed in the camera with a group starting at another number.

## [v0.3.0-r1](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.3.0-r1) — 2026-10-29

- v0.3.0 的第一次主机工具修订，修复 [issue #12](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/12)：Windows 的反斜杠路径被误判为源码不匹配。
- 源码身份键统一为 `/`；仍逐字节校验源码与预编译补丁，不改变哈希要求。
- 加入 Windows／POSIX 路径回归、缺失与损坏文件负控，以及 Windows 默认预编译构建检查。
- 四份补丁机器码、15 种组合配方、原厂 C 3.11 输入要求及机内功能均与 v0.3.0 相同。原 v0.3.0 标签与附件保持不变。

English: first host-tool revision of v0.3.0. Fixes Windows source-path comparison by using forward-slash manifest keys, while preserving exact byte/hash checks. Adds cross-platform path regression, integrity negative controls and Windows prebuilt CLI checks. Firmware code, all 15 recipes and the required C 3.11 input are unchanged; the original v0.3.0 tag and assets are retained.

## [v0.3.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.3.0) — 2026-10-29

- 新增机内像素位移组浏览、选择与 NEFX 合成，支持 4／8／16／32 张无损 NEF 组。
- 新增 FX 3:2 N-RAW 开放门，支持 8.3K 30／25／24p。
- 新增 N-RAW Fine／Basic，形成 High／Fine／Normal／Basic 四档，并提供相应菜单、文件标识与剩余录制时间估算。
- 四个功能选项可独立选择，共 15 种非空组合；ProRes 可与“开放门＋N-RAW”分别构建。
- 改进 RAW 预拍剩余张数：计入 NEF，并随 RAW 压缩、JPEG 档位及 ★ 设置刷新。
- 改进 RAW 预拍的登记拒绝处理：只尝试 JPEG 回退，不再绕过数据库直接写 NEF；后续帧可继续尝试正常 NEF 写入。停止文件机制仍保留。

English: adds in-camera pixel-shift merging, FX 3:2 N-RAW at 8.3K 30/25/24p, four N-RAW quality tiers, and independent selection of four features. Improves pre-capture remaining counts and database-refusal handling; the stop-file mechanism remains in use.

## [v0.2.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.2.0)

- RAW 连拍／预拍新增 HE★，可在机内“RAW 记录”选择 HE／HE★。
- 移除对 `Z8PRE.CFG` 的依赖，直接使用机内设置；旧配置文件不再读取。
- QUAL／f2、i 菜单和取景画质标识使用普通“画质”设置。
- 完善双卡备份及 RAW／JPEG 分卡规则，每帧使用提交时的主卡槽和副卡槽设置。
- 保留 ProRes 四档与菜单库分别保存功能。

English: adds HE★ RAW capture, removes the CFG dependency, aligns quality controls/displays with the ordinary menu, and extends dual-card routing using the settings stored when each frame is submitted.

## [v0.1.0](https://github.com/XinmiaoZhao/NikonFirmwarePatch/releases/tag/v0.1.0)

- 首次公开面向官方 Nikon Z8 C 3.11 的补丁构建工具。
- 提供 ProRes HQ／Standard／LT／Proxy，支持按拍摄菜单库分别保存。
- 提供 C15／C30 HE RAW 连拍与预拍，使用普通画质菜单选择 RAW／RAW+JPEG／JPEG；NEF 带整幅预览并支持机内回放。
- ProRes 与 RAW 预拍可单独或组合构建。
- 提供源码、预编译补丁工具包和独立固件核验工具。

English: first public release for official Z8 C 3.11, with four ProRes grades, per-bank settings, C15/C30 HE RAW/pre-capture, selectable feature combinations, precompiled patch distribution and independent output verification.
