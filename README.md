# Qwen-Image-2.1 本地工作台

浏览器打开就能用的 **Qwen-Image-2.1** 出图工作台。推理全部在你自己的机器上完成，
**不调用任何在线 API**；界面与后端都是本地文件，可离线使用。

📖 详细说明见 **[使用说明.md](使用说明.md)**｜模型能力调研见 **[能力清单.md](能力清单.md)**｜
改代码前必读 **[开发注意.md](开发注意.md)**

> ⚠️ **许可**：Qwen-Image-2.1 使用 **Qwen Research License，仅限非商用**。
> 商用需单独向官方申请。若你的用途涉及商用，请改选 Apache-2.0 的
> Qwen-Image-2512 / Edit-2509 等版本。

---

## 它能做什么

| 能力 | 说明 |
|---|---|
| **文生图** | 中英文提示词均可；官方支持 2K，本工作台默认 1024 档（12 GB 显存可跑） |
| **参考图编辑** | 最多 **10 张**参考图；用官方标记 `<image1>` `<image2>` 指代，`<image1>` 决定画布与基准风格 |
| **透明背景（RGBA）** | 打开开关即按官方模板补全提示词；本机实测透明像素 **70~79%**，出图后回报实测比例 |
| **局部编辑** | 在图上**画标记**（圈/涂）→ 模型重绘 → 按标记**确定性合成**回原图，标注区外逐点不变（实测 0.000%） |
| 图片查看 | 点结果图放大：滚轮以光标为中心缩放、拖动平移、1:1 / 适应窗口、下载 |

**已知不支持**：ControlNet（官方无 2.1 权重）、经典 img2img 去噪强度、加速 LoRA（2.1 目前没有任何 Lightning/distill）。
细节见 [能力清单.md](能力清单.md)。

---

## 你需要准备什么

| 项 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows 10/11 64 位 | 启动脚本是 `.bat`；Linux/macOS 可直接 `python server.py`（未实测） |
| 显卡 | **NVIDIA，显存 ≥ 12 GB** | 实测 1024×1024 峰值占 11518/12227 MB（**94%**），12 GB 是底线 |
| 内存 | 建议 ≥ 32 GB | |
| 磁盘 | ≥ 30 GB 可用 | 权重 17.3 GB + 工作余量 |
| Python | **3.10+** | 后端只用标准库，**无需 pip 安装任何东西** |
| ComfyUI | **较新版本（master）** | 参考图编辑依赖 `TextEncodeQwenImage21` 节点，**它不在 v0.30.0~v0.36.0 任何正式 tag 里**，必须 master |

> 如果你已有 ComfyUI 在 `127.0.0.1:8188` 运行，可以直接复用，无需配置路径。

---

## 快速开始

### 1) 克隆

```bat
git clone https://github.com/liceses/QwenImage2.1-EazyWebBench.git
cd QwenImage2.1-EazyWebBench
```

### 2) 准备 ComfyUI

推荐**便携版**（自带匹配的 PyTorch，免装环境）：
从 <https://github.com/comfyanonymous/ComfyUI/releases> 下载
`ComfyUI_windows_portable_nvidia.7z`，解压到任意目录。

工作台按以下顺序自动找它，**任选一种**即可：

1. 环境变量 `QWEN21_COMFY_ROOT`
2. 项目根目录下的 `config.json`：
   ```json
   { "comfy_root": "D:\\ComfyUI_windows_portable" }
   ```
   （可复制 `config.example.json` 改名）
3. 常见位置自动探测：项目内 `ComfyUI/`、`~/ComfyUI_windows_portable`、
   `~/Desktop/ComfyUI_windows_portable`、`C:\` `D:\` `E:\` 盘根目录等
4. **ComfyUI 已在 8188 运行** → 直接复用，本步可跳过

> `comfy_root` 指**包含 `ComfyUI/main.py` 的那一层**（便携版形如 `...\ComfyUI_windows_portable`）。

### 3) 下载权重（约 17.3 GB）

```bat
python tools\download.py
```

特性：多镜像自动切换（hf-mirror → ModelScope → 官方 HF，实测 **23–30 MB/s**）、
断点续传、按官方字节数校验完整性。只想下某一个：`python tools\download.py --only vae`

三个文件会放到（脚本自动建目录）：

| 文件 | 大小 | 目录 |
|---|---|---|
| `qwen_image_2.1_int8_convrot.safetensors` | 7.26 GB | `models/diffusion_models/` |
| `qwen3vl_8b_int8_convrot.safetensors` | 9.35 GB | `models/text_encoders/` |
| `qwen_image_2.1_vae_bf16.safetensors` | 0.68 GB | `models/vae/` |

### 4) 启动

双击 **`启动工作台.bat`**（或在该目录执行它）。终端会打印：

```
====================================================================
  工作台已启动，请在浏览器打开:  http://127.0.0.1:8642
  按 Ctrl+C 退出
====================================================================
```

工作台会自动：**查权重 → 让 ComfyUI 读到权重 → 检测/拉起 ComfyUI → 起界面**。

> 权重如何被 ComfyUI 看到：优先写一份 `extra_model_paths.yaml`（**零拷贝、零额外空间，跨盘也可用**）；
> 不行才退化为硬链接，再不行才复制（会明确提示要多占 17 GB）。

### 5) 自检（推荐）

```bat
python tools\selfcheck.py
```

全部正常会输出 `结果：全部通过，工作台处于可出图状态`；异常会逐项列 `[FAIL]` 并说明原因。

---

## 怎么用（要点）

### 文生图
写提示词（中英文都行）→ 选尺寸 → 点「开始生成」。首次出图要加载约 16 GB 权重，会明显慢；
之后单张约 **25–35 秒**（RTX 5070 Ti Laptop 12 GB / int8 / 1024 档 / 25 步）。

**负向提示词默认不生效** —— 官方设计为引导强度 `true_cfg_scale = 1.0`（不开引导）。
要它生效得调到 > 1，代价是每步计算量翻倍。

### 参考图编辑
上传参考图后即进入编辑模式。**提示词里用官方标记指代**：

```
把 <image1> 里少女的发色改成粉色，其余一切保持不变。
```

- **`<image1>` 是编辑目标**，决定画布尺寸与基准风格 —— 把「要保持构图的那张」放第一位
- 编辑模式下「尺寸 / 比例」不生效（画布跟随 `<image1>`）
- 单图可用自然指代，**多图必须用 `<imageN>` 标记**（官方称该格式 mandatory）

### 透明背景
打开「透明背景（RGBA 出图）」开关即可 —— 工作台会按官方句式自动补全提示词。
出图后：结果区变**棋盘格**、显示实测透明像素比例、下载按钮变「下载透明 PNG（RGBA）」。
若显示 **0%** 说明这次没生成透明区域，**换个随机种子重试**。

### 局部编辑
在「局部编辑」卡片里：选图 → 在图上画标记（画笔可调）→ 写「要改成什么」→ 点「按标注局部修改」。
工作台先让模型按标记重绘，再**按你画的区域把结果合成回原图**，
所以**没画到的地方逐点不变**。

> 标记区内的效果取决于模型：**换颜色 / 纯色填充很稳**；要求「画出某个特定图形」可能需要换种子重试。

---

## 常见问题

<details>
<summary><b>报「未找到 ComfyUI 安装目录」</b></summary>

按上面第 2 步任选一种方式配置 `comfy_root`。注意它指**包含 `ComfyUI/main.py` 的那一层**。
如果 ComfyUI 已经在 8188 跑着，这条可以直接忽略。
</details>

<details>
<summary><b>报「模型权重未就绪」</b></summary>

跑 `python tools\download.py` 补齐。界面顶部会写明**缺哪个文件、该放哪里、大小对不对**。
</details>

<details>
<summary><b>显存不足 / CUDA out of memory</b></summary>

按有效性排序：① **关掉其它占显存的程序**（浏览器硬件加速、游戏、其它 AI 工具）——
这是最有效的一招；② 尺寸降到 896 或 768；③ 步数降到 20 以下；④ **不要用 2048×2048**，按显存推算必 OOM。
</details>

<details>
<summary><b>浏览器显示「无法使用此页面 / 127.0.0.1 未发送任何数据」</b></summary>

这是**同一端口起了两个工作台实例**（Windows 允许两个进程绑同一端口，连接被随机分配）。
最常见原因是**启动脚本被双击了两次**。当前版本已经堵住：启动脚本检测到已有实例就直接打开它，
`server.py` 启动前用独占探针检查端口、被占则明确报错退出。

仍然遇到（比如旧版本留下的僵死进程）时，按终端给的命令处理：
```bat
netstat -ano | findstr :8642       rem 看最后一列的 PID
taskkill /PID <那个PID> /F
```
应急可用 `python server.py --force` 强行接管端口。
</details>

<details>
<summary><b>参考图编辑出来跟原图不像</b></summary>

① 确认提示词里写了 `<image1>`（多图时必须用 `<imageN>`）；
② 确认 ComfyUI 是 **master 分支**（旧版没有 2.1 节点）；
③ 参考图长边别超过 2000px。
</details>

<details>
<summary><b>负向提示词好像没用？</b></summary>

正常的。默认引导强度 1.0 = 不开引导，负向提示词被完全忽略（官方设计）。调到 > 1 才生效。
</details>

<details>
<summary><b>能不能换端口 / 不自动拉起 ComfyUI</b></summary>

```bat
python server.py --port 9000        rem 换端口
python server.py --no-comfy         rem 不自动拉起（自己先启动）
python server.py --force            rem 跳过端口预检（应急）
```
</details>

---

## 实测性能（RTX 5070 Ti Laptop 12 GB / int8 / 1024 档）

| 场景 | 步数 | 耗时 | 显存峰值 |
|---|---|---|---|
| 文生图首次（含权重加载） | 25 | **34.5 s** | 11518 MB |
| 文生图后续 | 25 | **29.3 s** | — |
| 参考图编辑（单图） | 25 | **37–125 s** | — |
| 三视图 / 多图合成 | 25 | **230–260 s** | — |

每采样步约 **1.38 s**。输出 PNG / RGBA（模型原生支持透明通道）。

---

## 目录结构

```
QwenImage2.1-EazyWebBench/
├─ 启动工作台.bat            一键启动（双击）
├─ server.py                 后端（纯 Python 标准库，零第三方依赖）
├─ requirements.txt          依赖说明（其实什么都不用装）
├─ config.example.json       ComfyUI 路径配置模板
├─ web/                      界面（手写 Material Design 3，无 CDN / 无在线字体）
│  ├─ index.html  app.css  app.js  favicon.svg
├─ tools/
│  ├─ download.py            权重下载器（多镜像 + 断点续传 + 完整性校验）
│  ├─ selfcheck.py           环境自检：一条命令核验权重/服务/节点
│  ├─ first_run.py           独立出图实测（记录耗时与显存）
│  ├─ speedtest.py           下载源测速
│  ├─ verify_mirror.py       校验镜像权重与官方一致
│  ├─ _paths.py              共享路径解析（环境变量优先，不依赖本机路径）
│  └─ diag/                  诊断与验收脚本（文档里结论的复现脚本）
├─ models/                   ← 权重放这里（需自己下载，17.3 GB）
├─ outputs/                  出图结果（运行期生成）
├─ 能力清单.md                模型能力调研 + 关键坑与实测结论
├─ 使用说明.md                详细使用说明
├─ 分享说明.md                分发说明
└─ 开发注意.md                改代码前必读的两个坑
```

> 仓库**不含**模型权重、出图结果与其它任务的产物（见 `.gitignore`）。
> `示例效果/` 里的对照图由 `tools/diag/` 的验收脚本在你机器上重新生成。

---

## 给要改这个项目的人

改之前请先读 **[开发注意.md](开发注意.md)**，那里记录了**两个会静默失败的坑**：

1. **ComfyUI Autogrow 入参必须用扁平带点键**（`images.image_1`）——
   写成嵌套 dict 会被**静默忽略**，参考图根本不进模型，退化成纯文生图，**不报错**。
2. **Windows 端口双绑定** —— `SO_REUSEADDR` 允许两个进程绑同一端口，
   另一个实例卡住时页面就会「连上了但一个字节都没回来」。

另外 [能力清单.md](能力清单.md) 第 12 / 15 / 16 节记录了透明通道与局部编辑的完整实测结论与踩坑过程。

---

## 致谢与来源

- 模型：**Qwen-Image-2.1**（[QwenLM/Qwen-Image-2.1](https://github.com/QwenLM/Qwen-Image-2.1)，Qwen Research License）
- 权重（int8 量化版）：[Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1)
- 推理后端：[ComfyUI](https://github.com/comfyanonymous/ComfyUI)（需要 master 分支）
- 官方工作流参考：[Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates)

本仓库是围绕上述开源项目做的**本地工作台封装**（后端 + 界面 + 工具链），不含模型本身。
