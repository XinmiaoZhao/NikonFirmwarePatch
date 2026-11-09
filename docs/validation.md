# v0.4.0-rc.2 验证范围 / Validation coverage

本轮补丁以用户自行取得的原厂 Z8 C 3.11 为输入。构建时选择的固件版本号用于区分文件；以下按功能组合说明证据。

| 项目 | 已验证的范围 |
|---|---|
| 四组构建 | 15 种非空组合独立解封装，核对身份、补丁窗口、未改动字节、共享菜单和资源边界。源码重编与工具包内预编译单元比对 |
| 有界启动 | 每种组合从解密 MAIN 启动，使用模拟外设进入菜单，两次到固件版本页，停在更新入口。机身更新流程不在模拟范围内 |
| N-RAW 回放 | 使用本轮更新的补丁构建全选固件。Z8 机身回放旧录的 S-Log3 和新录的 Log3G10，详情页名称均正确，测试者确认开启辅助后的还原观感符合各自片段。屏摄记录了名称和 ASSIST 图标；面板色度没有仪器测量 |
| ProRes | 此前同一编码实现的全选固件在 SD 上记录 1 段 HQ、3 段 LT。四段 4K 29.97p、10-bit 4:2:2 全部解码到片尾 |
| RAW 预拍 | 同一照片实现的 FX／DX 样本中，选择“无损”实际记录 HE★。99 张预拍 NEF 全部解码，59 个配对 JPEG 与同次快门一致。直接选择 DX、C30、仅 RAW、HE★ 的组合仍待补测 |
| 像素位移 | 机内合成 4 张和 16 张两组，从非 0001 编号起拍。两份 NEFX 均完整解码；每份抽查 16,388 个位置，红、绿与源帧重建一致，蓝的差异仅位于 AF 校正行 |
| 共享设置与显示 | 先前的有界执行覆盖菜单分流、星标刷新、菜单库字段复制。机身试用反馈反挤压绿点正常。跨库切换、取电重开、取景器边缘及各回放页仍需分别观察 |
| 记录视频方向（开发组） | 含 `video-orientation` 的构建通过全量单元测试，`verify.py` 对单选与“四视频组＋视频方向”产物独立核验通过；非空组合增至 31 种，全部配方冻结（15 份无照片工具组合真实构建逐字节复验，16 份含照片工具组合经混合装配与结构审计冻结）。行值渲染已过仿真人工验收，菜单库随库切换的双向记忆经仿真实证；实机菜单行为（保存、菜单库切换、断电回默认开、菜单重设）全部验证通过，与已发布的 H.265 档位功能完全一致。实机首录验收定位两个缺陷并已修复（2026-11-10，待复验）：轴表按 NEV 文件矩阵实证改为 X＝竖直轴／Y＝翻滚轴；一次性锁存改为粘性锁存＋会话边界清零（详见外仓 `docs/t15-h265-rotation-loss-re.md`）。修复镜像 vr-only `03.00.v1` 已构建并通过全部离线检查；实机复验（每格式×每握持）与竖拍 Y 极性一次标定待做；该组未随 v0.4.0-rc.2 发布，详见[记录视频方向指南](video-orientation.md) |

录像色彩与模型对照见[色彩报告](log-colour-report.md)。可选 F LUT 已做格点、插值和中性轴数值检查；剪辑软件及显示器的端到端输出另需校验。发布工具包在 Windows Python 3.12 和 3.13 上的实际运行状态见 [Host checks](https://github.com/XinmiaoZhao/NikonFirmwarePatch/actions/workflows/host-checks.yml)。[机器摘要](validation-summary.json) · [历史像素位移修订](validation-v0.3.1.md) · [历史预拍修订](validation-v0.2.0.md)

## English

The original Z8 C 3.11 package is checked before building. All 15 nonempty selections are independently decoded and checked for identity, patch windows, preserved bytes and shared-resource boundaries. Each bounded emulator run boots decrypted MAIN with synthetic peripherals, enters the firmware version page twice and stops at the update entry.

The all-feature firmware built with this update was tested on a Z8. A previously recorded S-Log3 N-RAW clip and a newly recorded Log3G10 clip showed the correct names in playback. The tester confirmed the expected assist rendering; the photographs document the label and ASSIST indicator. Display colour accuracy was not measured.

The development-branch fifth group `video-orientation` is outside this release's scope. Its offline checks pass: the full unit suite, `verify.py` on the single-group and four-video-groups-plus-orientation outputs, and the frozen 31 combination recipes (15 rebuilt byte-exactly; the 16 photo-tools combinations frozen via hybrid assembly with a structural audit). The menu-row value rendering passed manual emulator acceptance, and the per-bank memory across menu-bank switches is emulator-verified. On the camera, the menu behaviour — saving the setting, switching between different menu banks, the power-cycle default and the reset-menu behaviour — all matches the shipped H.265 tier feature exactly. The first camera recording round located two defects, both fixed (2026-11-10, pending re-verification): the axis table now follows the NEV-file-proven mapping (X = camera vertical, Y = roll), and the retired one-shot latch became a sticky session latch with boundary clears (see the outer repository's `docs/t15-h265-rotation-loss-re.md`). The fixed vr-only image `03.00.v1` is built and passes every offline check; the camera re-verification matrix (every format by every grip) and the one-clip portrait Y-polarity calibration remain. See the [video-orientation guide](video-orientation.md).

Earlier all-feature camera checks on the same recording and photo implementations covered four decoded ProRes HQ/LT recordings, 99 decoded pre-capture NEFs and 59 matching JPEGs, DX/FX lossless-to-HE★ fallback, and two fully decoded 4-/16-frame pixel-shift merges from non-default starting file numbers. The tester also reported normal lit AF points with desqueeze. Menu-bank/power-cycle transitions and individual playback icons, small-viewfinder or subject-detection geometries remain separate checks.

See the [colour measurements](log-colour-report.en.md), [known limitations](known-issues.md) and [Windows toolkit CI](https://github.com/XinmiaoZhao/NikonFirmwarePatch/actions/workflows/host-checks.yml). Windows jobs build on Python 3.12 and 3.13 using the released ZIP and verify the full-selection output against the supplied reference digest.
