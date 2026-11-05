# 色彩报告数据 / Colour report data

[中文版](../log-colour-report.md) · [English](../log-colour-report.en.md)

实拍与模拟分开保存。实拍图只取当前实现的两段重复录像及各自拍摄前后的 N-RAW。模拟图使用冷光 1/250、冷光 1/500、暖光 1/250 三组 N-Log 的固定区域均值，四种方案共用每组反算出的 M1 前输入。每种输出分别按目标曲线、色域解码，使用三灰片对齐、D65 白点和每组参照的最亮色片亮度计算 ΔE00。模拟图的中位数与 P95 汇总全部 144 个色片条件。两种 Log 均将每段 ROI 码值解码到目标线性 RGB，再等权平均两段。主参照也取前后 N-RAW 的线性均值，前后单独比较另存为 pre、post。实拍表和累计分布每个条件取 48 片。文件码值误差直接在码值域计分。

- [录像与参照](log-camera.json)含 ROI 均值、参考时序、文件与数值来源哈希。
- [模型输入与预测](log-controls.json)含 N-Log 均值、反算共同输入、线性 RWG 参照、有效 M1 和四条链路的预测 YCbCr。Log3G10 的简化模型使用早期实现的有效 Q10 矩阵。对应 S-Log3 模型按 BT.2020 与 S-Gamut3.Cine 的 D65 原色计算转换矩阵，基表量化到 Q10 并保持行和，再与本机 Q14 标定矩阵相乘取整。
- [色差统计](log-response-summary.json)model 和 camera 中每组三个数依次为 ΔE00 的中位数、P95、最大值。linear_metrics 保存新口径的比例、亮度、留出色样与码值统计。另有 8 块未参与拟合的色样，单独报告其通道比例和亮度误差。
- [色域参考矩阵](adobe-z8-matrix.json)和 [CIE 1931 标准观察者](cie-1931.json)用于编码色域示意图。光谱轨迹来自 [CIE 2019](https://doi.org/10.25039/CIE.DS.xvudnb9b)，数据及含该轨迹的图形按 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 提供。

需要 Python、NumPy、Matplotlib 和 Pillow。以下命令重算统计并生成中英文的分模式四链路色度图、实拍色度图、实拍 ΔE00 累计分布及模拟色差图，中文字体可通过 `--chinese-font` 指定。另可从自行取得的原厂 C 3.11 文件读取曲线和 Cpxs 表，逐片重算模型预测并核对输入往返。

```sh
python tools/plot_log_response.py
python tools/plot_log_response.py --check
python tools/replay_log_controls.py /path/to/Z_8_0311.bin
```

Camera samples, simulated file codes and numerical summaries are separate datasets. The first command renders the bilingual camera and model figures from public numerical data. The second checks all saved colour-difference summaries. The optional third command uses the identified stock firmware to reproduce the N-Log input means from their estimated pre-M1 values and all four forward predictions. All comparisons share fixed parameters and the same neutral-alignment rule. The additional warm 1/500 s camera capture is included in the S-Log3 measurement table and cumulative plot.

含 CIE 光谱轨迹的图组为 `log-colour-spaces`、`log-slog3-chromaticity`、`log-rwg-prediction` 和 `log-measured-chromaticity`，均含中英文版本。新绘的实拍与模拟 xy 图只使用色片坐标。
