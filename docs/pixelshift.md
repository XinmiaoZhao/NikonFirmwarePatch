# 像素位移合成 / Pixel-shift merge

[简体中文](#简体中文) · [English](#english)

## 简体中文

### 功能

`--features pixelshift` 在照片拍摄菜单加入“像素变化合成”，浏览两张卡上的像素位移组，选择一组或多组并在机内合成 NEFX。

### 支持范围

**当前仅支持每组在新建文件夹中拍摄，文件编号从 `0001` 开始。**

支持完整的 **4／8／16／32 张、FX/L、8256×5504、14-bit 无损压缩 NEF** 组。HE／HE★、DX、残缺或重复组不能合成；RAW 预拍生成的 HE／HE★ NEF 也不适用。补丁不改变像素位移拍摄动作。

### 使用步骤

1. 在像素变化拍摄的起始存储文件夹设置中，同时勾选 **New folder（新建文件夹）** 和 **Reset file numbering（重置文件编号）**，使每组在新文件夹中从 `0001` 开始。
2. 使用原厂像素变化拍摄取得完整组，等待写卡完成。
3. 打开照片拍摄菜单中的“像素变化合成”。
4. 上下移动，OK 勾选，选择开始合成并确认；已有输出的组可再次合成。
5. 合成中按 MENU 取消；OK 不取消。半按离开页面也会取消，再次进入可查看结果。等写入结束再关机或取卡。

### 输出与显示

列表显示首帧缩略图、文件夹／首张文件名、张数和状态。输出在原组目录，名为 `DSC_XXXX_MERGED.NEFX`；重复合成使用 `_MERGED_2` 等新名，不覆盖原片或旧输出。`PSMERGE.LOG` 保存日志。

4／8 张组输出 **8256×5504**，16／32 张组输出 **16512×11008**。NEFX 在电脑上读取。

### 已知问题

- 缩略图只显示首帧，机内回放不能查看最终合成结果。
- 输入格式和完整性必须满足上述条件；缺帧或错误组不能选择。
- 移动物体、机位变化和曝光变化会影响合成。内存不足时程序先减少缓存，再尝试同步处理；仍无法分配时提示错误。

## English

### Overview

`--features pixelshift` adds Pixel shift merge to the photo shooting menu. Browse groups on both cards, select one or more, and merge them into NEFX in the camera.

### Supported modes

**Currently, each group must be captured in a new folder with file numbering starting at `0001`.**

Supports complete **4/8/16/32-frame, FX/L, 8256×5504, 14-bit lossless-compressed NEF** groups. HE/HE★, DX, incomplete and duplicate groups are unsupported, including HE/HE★ NEFs from pre-capture. The patch does not change pixel-shift shooting itself.

### Steps

1. Under **Pixel shift shooting → Starting storage folder**, enable both **New folder** and **Reset file numbering** so that each group starts at `0001` in a new folder.
2. Capture a complete group using stock pixel-shift shooting and wait for writes to finish.
3. Open Pixel shift merge in the photo shooting menu.
4. Move up/down, use OK to select groups, then start and confirm merging. Groups with existing outputs can be merged again.
5. MENU cancels an active merge; OK does not. Leaving by half-press also cancels, and the result is available on re-entry. Wait for writes before power-off or card removal.

### Files and display

The list shows the first-frame thumbnail, folder/first filename, frame count and status. Output is `DSC_XXXX_MERGED.NEFX` beside the originals; repeated merges use `_MERGED_2` and subsequent names without overwriting inputs or earlier outputs. `PSMERGE.LOG` stores the log.

Output is **8256×5504** for 4/8 frames and **16512×11008** for 16/32 frames. Read NEFX on a computer.

### Known issues

- Thumbnails show the first frame only; camera playback does not display the final merge.
- Input format/completeness must meet the conditions above; incomplete or invalid groups cannot be selected.
- Subject movement, camera movement and exposure changes affect merging. Under memory pressure, the program reduces cache size, then tries synchronous processing; allocation failure produces an error.

## 相关文档 / Related documents

[构建与截图 / Build and screenshots](../README.md) · [已知问题 / Known issues](known-issues.md) · [验证记录 / Validation](validation.md) · [致谢与许可 / Attribution](../NOTICE.md)
