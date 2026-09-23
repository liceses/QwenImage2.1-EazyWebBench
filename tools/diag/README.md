# 诊断脚本说明（含一个已修复的坑）

> ⚠️ **本目录的脚本都是"调查过程"的记录，其中大部分使用了错误的 API 调用格式。**
> 直接用它们复现会得到错误结论。保留它们是为了留痕，不是让人照抄。

## 那个坑：ComfyUI Autogrow 入参格式

`TextEncodeQwenImage21` 的参考图入参 `images` 是 ComfyUI 的 **Autogrow 动态输入**。
在 API 格式里必须用**扁平的带点键**：

```python
# ✅ 正确
"inputs": {"clip": [...], "prompt": "...", "images.image_1": ["10", 0]}

# ❌ 错误 —— 会被静默忽略，参考图完全不进模型，退化成纯文生图
"inputs": {"clip": [...], "prompt": "...", "images": {"image_1": ["10", 0]}}
```

依据：`comfy_api/latest/_io.py` 的 `Autogrow._expand_schema_for_dynamic`
用 `finalize_prefix()` 把子输入展开成 `images.image_N`，并且只认 `live_inputs` 里的扁平键。

## 本目录脚本的格式情况

| 脚本 | 用的格式 | 结论是否可信 |
|---|---|---|
| `diag_multiref.py` | ❌ 嵌套 | 否 —— 全部是 Bug 假象 |
| `diag_multiref2.py` | ❌ 嵌套 | 否 |
| `diag_multiref3.py` | ❌ 嵌套 | 否 |
| `diag_cache.py` | ❌ 嵌套 | 否（但"缓存节点无影响"这一条恰好仍成立，因为没图可缓存） |
| `diag_compose.py` | ❌ 嵌套 | 否 |
| `diag_tagname.py` | ❌ 嵌套 | 否 |
| `diag_samechar.py` | ❌ 嵌套 | 否 |
| `diag_edit_fidelity.py` | ❌ 嵌套 | 否 |
| `diag_resolution.py` | ❌ 嵌套 | 否 |
| **`diag_autogrow.py`** | ✅ **两种对比** | **是 —— 这是定位根因的那个脚本** |
| `first_run.py` | 无参考图（纯 t2i） | 是（文生图部分有效） |

**只有 `diag_autogrow.py` 是可信的定位实验**，它用「输出画布尺寸」作为判据：
- 嵌套写法 → 画布 1024×1024（正方形，说明参考图没进去）
- 扁平写法 → 画布 960×1568（= 参考图 945×1562 的比例，说明图进去了）

## 复现正确做法

直接用工作台（`启动工作台.bat`）或参考 `server.py` 里 `build_workflow()` 的正确写法。
修复后的实测效果见项目根目录 `修复验证/`。

---

# 另外两个诊断脚本：HTTP / 端口（与上面的坑无关，结论都可信）

排查「终端说启动成功，浏览器却显示 `127.0.0.1 未发送任何数据`」时用的。详见
项目根目录 [开发注意.md](../../开发注意.md) 第 2 节。

| 脚本 | 用途 | 结论 |
|---|---|---|
| `diag_http_min.py` | 同一进程内自起一个最小 `ThreadingHTTPServer` 并自己请求一次，用来判断"HTTP 层本身是否正常" | 3.13 / 3.14 均正常 → 问题不在标准库 |
| `diag_port_semantics.py` | 隔离验证 `SO_REUSEADDR` / 双绑定 / 空闲端口 connect 的真实语义 | 空闲端口 connect 会**超时**；带 `SO_REUSEADDR` 的第二个 socket **能绑上同一端口**；不带则报 `WinError 10048` |

用法（端口可换）：

```bat
python tools\diag\diag_http_min.py 18642
python tools\diag\diag_port_semantics.py 18660
```

---

# 透明通道（RGBA）诊断脚本

排查/验收「透明背景出图与编辑」时用。完整结论见项目根目录
[能力清单.md](../../能力清单.md) 第 15 节。**这些结论都可信**（不涉及上面那个 Autogrow 坑）。

| 脚本 | 用途 | 关键结论 |
|---|---|---|
| `diag_vae_alpha.py` | 直接读 VAE 权重，判断解码器输出通道数 | `decoder.head.2.weight = [4,144,1,3,3]` → **4 通道（含 alpha）** |
| `diag_vae_rgba.py` | 走 ComfyUI 的 VAEEncode/VAEDecode，看 alpha 能否往返 | 解码结果经 `SaveImage` 写出 **RGBA** |
| `diag_alpha_roundtrip.py` | `LoadImage → SaveImage` 是否保留 alpha | 保留（4 通道被原样写出） |
| `diag_mask_alpha_convention.py` | 用**非对称探针**（左不透明/右透明）判定 mask/alpha 取值约定 | `LoadImage.MASK` 数值上 = **1−alpha**；`SaveImageWithAlpha` 会把 mask 取反 |
| `diag_alpha_chain.py` | 四段探针（alpha 0/85/170/255）逐环量整条链 | **`JoinImageWithAlpha(image, LoadImage.MASK)` 正确**；先 `InvertMask` 反而会反掉 |
| `diag_alpha_scan.py` | 扫描历史产物，统计有多少图真的带透明像素 | 180 张全是 RGBA，但 alpha 都在 252~255（= 视觉全不透明） |
| `diag_transparent_gen.py` | 端到端：按官方模板生成一张，量 alpha | 官方模板 → **透明像素 70~79%**；`--scan <png>` 可只扫已有产物 |
| `cmp_alpha.py` | 逐像素比较两张 PNG 的 alpha（判断是否互为反相） | 「和≈255 占比 >90%」即判定为反相 |
| `accept_transparency.py` | **验收脚本**：文生图 + 编辑两条透明路径，并生成肉眼对照图 | 4 项检查；对照图输出到 `示例效果/透明背景-*-对照.png`（该目录不存在时会自动创建） |

```bat
python tools\diag\diag_alpha_scan.py            rem 扫历史产物
python tools\diag\accept_transparency.py        rem 完整验收（会真出两张图，约 1 分钟）
python tools\diag\cmp_alpha.py A.png B.png      rem 比两张图的 alpha
```

---

# 尺寸来源诊断

排查「界面显示的尺寸和实际图片不一致」时用。

| 脚本 | 用途 | 关键结论 |
|---|---|---|
| `diag_size_source.py` | 逐个任务比对「记录的宽高」与「产物 PNG 的真实像素」 | 实测 104 个任务里 **35 个不一致**；规律是**参考图编辑模式下画布跟随 `<image1>`**，而 `params.width/height` 只是界面上那个不生效的默认值（例：记录 1024×1024、实际 960×1568） |

```bat
python tools\diag\diag_size_source.py
```

**修法**：尺寸的唯一来源收敛到产物文件本身 ——
`server.py` 用 `png_size()` 读 IHDR 登记到 `images[].width/height`；
界面各处（结果介绍 / 历史缩略图角标 / 查看器标题）统一由图片元素的实际像素得出。

---

# 局部编辑诊断 / 验收脚本

排查"圈选、涂抹能否做局部编辑"时用。完整结论见项目根目录
[能力清单.md](../../能力清单.md) 第 16 节。

| 脚本 | 用途 | 关键结论 |
|---|---|---|
| `diag_circle_edit.py` | 把红圈/红斑画在参考图上，看模型认不认 | ✅ **圈内变、圈外原样**：标记引导（视觉提示）确实有效 |
| `diag_latent_mask_inpaint.py` | 潜空间掩码重绘（`SetLatentNoiseMask`）可行性 | ❌ 掩码被无视，仍整图重绘 |
| `cmp_region_diff.py` | 按"掩码内 / 掩码外"分区统计像素差异 | 掩码外 **100% 被改动** → 掩码路不可用 |
| `accept_local_edit.py` | **验收脚本**：标注 → 模型重绘 → 按标注合成 | 3 项硬指标；标注区外 **0/1001863 = 0.000%** |
| `make_sidebyside.py` | 把多张图横向拼成对照图（交付"看得见"的证据） | 供 `示例效果/局部编辑-前后对照.png` 使用；仓库不含位图，图由验收脚本现场生成 |

```bat
rem 圈住某个区域要求改色（自行调整圆心/半径/诉求）
python tools\diag\diag_circle_edit.py --circle=0.40,0.33,0.10 --inside="the hair" --want="pink"
python tools\diag\diag_circle_edit.py --mode=disc --circle=0.50,0.60,0.16 --want="solid bright red"

python tools\diag\accept_local_edit.py          rem 局部编辑完整验收（会真出图，约 1 分钟）
python tools\diag\cmp_region_diff.py A.png B.png --box=330,230,580,460
python tools\diag\make_sidebyside.py out.png a.png b.png c.png
```
