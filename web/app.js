/* Qwen-Image-2.1 本地工作台 —— 前端逻辑（无第三方依赖） */
"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  cfg: null,
  refs: [],          // {name, url}
  history: [],       // 会话内历史
  activeJobId: null,
  polling: null,
  shownJobId: null,  // 当前展示的任务
};

/* ----------------------------------------------------------- 工具 */

function showMsg(text, kind = "err", extraHtml = "") {
  const el = $("globalMsg");
  el.className = "msg " + kind;
  el.innerHTML = escapeHtml(text) + (extraHtml ? "<br>" + extraHtml : "");
  el.classList.remove("hide");
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideMsg() {
  $("globalMsg").classList.add("hide");
}

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtBytes(n) {
  if (!n && n !== 0) return "-";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0, v = Number(n);
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return v.toFixed(v < 10 ? 2 : 1) + u[i];
}

function fmtDuration(s) {
  if (s == null) return "-";
  if (s < 60) return s.toFixed(1) + " 秒";
  const m = Math.floor(s / 60);
  return m + " 分 " + Math.round(s - m * 60) + " 秒";
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  let body = null;
  try { body = await r.json(); } catch (e) { body = null; }
  if (!r.ok) {
    const msg = (body && body.error) || ("请求失败 HTTP " + r.status);
    const err = new Error(msg);
    err.status = r.status;
    err.body = body;
    throw err;
  }
  return body;
}

/* ----------------------------------------------------------- 初始化 */

async function init() {
  try {
    state.cfg = await api("/api/config");
  } catch (e) {
    showMsg("无法读取工作台配置：" + e.message + "\n请确认服务是否正常运行。");
    return;
  }

  // 比例预设
  const preset = $("preset");
  preset.innerHTML = "";
  state.cfg.aspect_presets.forEach((p, i) => {
    const o = document.createElement("option");
    o.value = String(i);
    o.textContent = p.label;
    preset.appendChild(o);
  });
  preset.value = "0";

  // 采样器 / 调度器
  const sp = $("sampler"), sc = $("scheduler");
  state.cfg.samplers.forEach((s) => sp.add(new Option(s, s)));
  state.cfg.schedulers.forEach((s) => sc.add(new Option(s, s)));
  sp.value = state.cfg.defaults.sampler_name;
  sc.value = state.cfg.defaults.scheduler;

  preset.addEventListener("change", () => {
    const p = state.cfg.aspect_presets[Number(preset.value)];
    if (p) { $("width").value = p.width; $("height").value = p.height; }
  });
  $("width").addEventListener("input", () => preset.value = "");
  $("height").addEventListener("input", () => preset.value = "");

  // 自定义画布（合影/海报等新构图）：勾选后尺寸控件解禁
  if ($("customCanvas")) {
    $("customCanvas").addEventListener("change", () => {
      if ($("customCanvas").checked) {
        // 官方指南：合影/合照无画布时用 3:2 横版 —— 直接给个合理起点
        $("width").value = 1152;
        $("height").value = 768;
        const sel = $("preset");
        for (let i = 0; i < sel.options.length; i++) {
          if (sel.options[i].text.indexOf("16:9") >= 0) { sel.value = sel.options[i].value; break; }
        }
      }
      updateSizeControls();
    });
  }

  // 参考图
  $("drop").addEventListener("click", () => $("fileInput").click());
  $("fileInput").addEventListener("change", (e) => {
    uploadFiles(Array.from(e.target.files || []));
    e.target.value = "";
  });
  const drop = $("drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => {
    e.preventDefault(); drop.classList.add("over");
  }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => {
    e.preventDefault(); drop.classList.remove("over");
  }));
  drop.addEventListener("drop", (e) => {
    const files = Array.from((e.dataTransfer && e.dataTransfer.files) || [])
      .filter((f) => f.type.startsWith("image/"));
    if (files.length) uploadFiles(files);
  });

  $("cfg").addEventListener("input", updateNegNote);
  updateNegNote();

  $("btnGen").addEventListener("click", generate);

  initMarkUI();
  initLightbox();
  initRefsDragula();

  await refreshStatus();
  await loadJobs();
}

function updateNegNote() {
  const cfg = Number($("cfg").value || 0);
  const n = $("negNote");
  if (cfg > 1) {
    n.innerHTML = "当前引导强度 = <b>" + cfg + "</b>（&gt;1），负向提示词<b>已生效</b>，每步计算量翻倍。";
    n.style.color = "var(--warn)";
  } else {
    n.innerHTML = "官方默认不开引导（引导强度 = 1.0）：此时负向提示词<b>不生效</b>。要让它生效，需把引导强度调到 &gt; 1（计算量翻倍）。";
    n.style.color = "";
  }
}

/* ----------------------------------------------------------- 状态 */

async function refreshStatus() {
  let st;
  try {
    st = await api("/api/status");
  } catch (e) {
    $("badgeBackend").className = "badge err";
    $("badgeBackend").textContent = "后端不可用";
    return;
  }

  const bm = $("badgeModel");
  if (st.models_ready) {
    bm.className = "badge ok";
    bm.textContent = "权重就绪";
  } else {
    const bad = Object.values(st.models).filter((m) => m.status !== "ok");
    bm.className = "badge err";
    bm.textContent = "权重缺失 " + bad.length + "/3";
  }

  const bb = $("badgeBackend");
  if (st.comfyui.ready) {
    bb.className = "badge ok";
    bb.textContent = "后端就绪" + (st.comfyui.info && st.comfyui.info.comfyui_version
      ? " (ComfyUI " + st.comfyui.info.comfyui_version + ")" : "");
    const g = $("badgeGpu");
    if (st.comfyui.info && st.comfyui.info.device) {
      const i = st.comfyui.info;
      g.className = "badge";
      g.textContent = i.device.replace("NVIDIA GeForce ", "") +
        " · 显存 " + i.vram_free_gb + "/" + i.vram_total_gb + "GB 可用";
    }
  } else {
    bb.className = "badge warn";
    bb.textContent = "后端未就绪";
    showMsg("ComfyUI 后端未就绪：" + st.comfyui.detail, "warn");
  }

  if (!st.models_ready) {
    const lines = Object.values(st.models)
      .filter((m) => m.status !== "ok")
      .map((m) => "· " + m.message)
      .join("<br>");
    showMsg(
      "模型权重未就绪，暂时无法出图：",
      "err",
      lines +
      "<br><br>权重根目录：<code>" + escapeHtml(st.models_dir) + "</code>" +
      "<br>下载命令：<code>" + escapeHtml(st.download_hint) + "</code>"
    );
  }
  return st;
}

/* ----------------------------------------------------------- 参考图 */

async function uploadFiles(files) {
  const max = (state.cfg && state.cfg.max_reference_images) || 10;
  for (const f of files) {
    if (state.refs.length >= max) {
      showMsg("参考图最多 " + max + " 张，多余的已忽略。", "warn");
      break;
    }
    const fd = new FormData();
    fd.append("file", f, f.name);
    try {
      const r = await api("/api/upload", { method: "POST", body: fd });
      state.refs.push({ name: r.name, url: r.url });
    } catch (e) {
      showMsg("参考图上传失败：" + e.message);
    }
  }
  renderRefs();
}

function renderRefs() {
  const box = $("refs");
  box.innerHTML = "";
  state.refs.forEach((r, i) => {
    const d = document.createElement("div");
    d.className = "ref";
    // 拖拽后要靠它把 DOM 顺序映射回 state.refs（元素会被重建，不能挂在对象上）
    d.setAttribute("data-ref-name", r.name);
    d.innerHTML = '<img src="' + r.url + '" alt="参考图' + (i + 1) + '" draggable="false">' +
      '<span class="num">图' + (i + 1) + '</span>' +
      '<button class="ref-del" title="移除">×</button>';
    d.querySelector("button").addEventListener("click", () => {
      state.refs.splice(i, 1);
      renderRefs();
    });
    box.appendChild(d);
  });
  $("refNote").style.display = state.refs.length ? "block" : "none";
  $("refBudgetWrap").style.display = state.refs.length ? "block" : "none";
  const dragHint = $("refDragHint");
  if (dragHint) dragHint.style.display = state.refs.length > 1 ? "block" : "none";
  updateSizeControls();
  renderRefWarn();
  renderMarkSources();
}

/* ----------------------------------------------------------- 参考图拖拽排序（Dragula） */
/*
 * 顺序是有语义的：<image1> 是编辑目标、决定画布尺寸与基准风格。
 * Dragula 只搬 DOM —— 如果不同步回 state.refs，界面顺序变了但
 * 提交给后端的 reference_images 仍是旧顺序（= 只是"看起来"换了位置）。
 * 所以 drop 之后按 DOM 顺序重建 state.refs，再重渲染以刷新「图1/图2」编号。
 */
let refsDragula = null;

function syncRefsOrderFromDom() {
  const box = $("refs");
  if (!box) return;
  const byName = new Map(state.refs.map((r) => [r.name, r]));
  const next = [];
  Array.from(box.querySelectorAll(".ref")).forEach((el) => {
    const n = el.getAttribute("data-ref-name");
    if (n && byName.has(n) && !next.includes(byName.get(n))) next.push(byName.get(n));
  });
  // 保险：万一有元素没匹配上，补到尾部 —— 绝不因为拖拽把参考图弄丢
  state.refs.forEach((r) => { if (!next.includes(r)) next.push(r); });

  const before = state.refs.map((r) => r.name).join("\u0000");
  const after = next.map((r) => r.name).join("\u0000");
  state.refs = next;
  if (before === after) return;
  // 等 Dragula 处理完本次事件再重渲染，避免它还在引用被移除的节点
  setTimeout(() => { renderRefs(); }, 0);
}

function initRefsDragula() {
  const box = $("refs");
  if (!box) return;
  if (typeof dragula !== "function") {
    // 库没加载成功时不静默：顺序仍以上传顺序为准，但要让用户知道拖拽不可用
    console.warn("Dragula 未加载，参考图拖拽排序不可用（顺序按上传先后）");
    return;
  }
  refsDragula = dragula([box], {
    // 点删除按钮时不要触发拖拽
    moves: (el, source, handle) => !(handle && handle.classList && handle.classList.contains("ref-del")),
    revertOnSpill: true,     // 拖到容器外松手 → 回原位，不会丢
    direction: "horizontal",
  });
  refsDragula.on("drop", syncRefsOrderFromDom);
  refsDragula.on("cancel", syncRefsOrderFromDom);
}

/* 编辑模式下画布默认由 <image1> 决定，尺寸控件停用；
   勾选「自定义画布」则改用宽高（= 官方 ComfySwitchNode 的 custom_size 行为），
   适用于合影/海报这类没有画布的新构图。 */
function updateSizeControls() {
  const editing = state.refs.length > 0;
  const custom = $("customCanvas") ? $("customCanvas").checked : false;

  const label = $("customCanvasLabel");
  if (label) label.style.display = editing ? "block" : "none";

  const lock = editing && !custom;   // 编辑模式 + 未勾自定义 → 禁用尺寸
  ["preset", "width", "height"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.disabled = lock;
    el.style.opacity = lock ? "0.45" : "";
    el.style.cursor = lock ? "not-allowed" : "";
  });
  const tip = $("sizeLockTip");
  if (tip) tip.style.display = lock ? "block" : "none";
}

/* 官方 prompt 指南（prompt_rewrite/prompts/system_prompt_edit.txt）明确规定：
   - **单图输入（N=1）不要用 <image1> 标记**，用自然指代（"图中""这个角色"）。
     原文：For single-image input (N = 1), do NOT use tags — refer to the image naturally.
   - **多图输入（N>=2）必须用 <image1> <image2> ……** 原文称 "mandatory and non-negotiable"，
     并明确禁止 "图1""第一张图""the first image""image A"。
   - 还要写清每张图的角色：哪张是画布（构图与未点名内容保留），哪张提供素材。 */
function renderRefWarn() {
  const el = $("refWarn");
  const n = state.refs.length;
  if (n < 1) {
    el.style.display = "none";
    return;
  }
  el.style.display = "block";

  const tplBtn = '<button class="small" id="btnRefTpl" style="margin-top:8px">插入这个句式模板</button>';

  if (n === 1) {
    el.innerHTML =
      "<b>单张参考图：用自然指代，不要写 <code>&lt;image1&gt;</code>。</b><br>" +
      "官方指南原文：<i>“For single-image input (N = 1), do NOT use tags — refer to the image naturally.”</i><br>" +
      "写法示例：<code>把图中少女的发色改成粉色，其余一切保持不变。</code><br>" +
      "只点名要改的属性，其余保持输入保真 —— 实测「只改发色」能保住姿势、服装、配饰、背景。" + tplBtn;
  } else {
    el.innerHTML =
      "<b>用了 " + n + " 张参考图 —— 必须用 <code>&lt;image1&gt;</code> <code>&lt;image2&gt;</code> 标记。</b><br>" +
      "官方指南称该格式 <i>“mandatory and non-negotiable”</i>，并明确禁止「图1」「第一张图」「the first image」这类自然语言指代。<br>" +
      "还要写明每张图的角色：哪张是<b>画布</b>（构图和未点名的内容保留），哪张<b>提供素材</b>。" +
      "把「要保持构图的那张」放第一位。<br>" +
      "推荐写法：<code>&lt;image1&gt; 是（画布/构图基准），&lt;image2&gt; 是（素材来源）。&lt;指令&gt;</code>" + tplBtn;
  }

  const btn = $("btnRefTpl");
  if (btn) {
    btn.addEventListener("click", () => {
      const ta = $("prompt");
      if (state.refs.length === 1) {
        // 单图：官方要求自然指代，不用标签
        ta.value = "把图中（要改的部分）改成（目标效果），" +
          "其余一切（姿势、服装、配饰、背景）保持完全不变。";
      } else {
        const tags = state.refs.map((_, i) => "<image" + (i + 1) + ">").join(" 和 ");
        ta.value = "把 " + tags + " 中，<image1> 作为画布（构图与未点名的内容保留），" +
          "<image2> 提供素材。请：（描述要做的编辑）。保持 <image1> 的构图与主体不变。";
      }
      ta.focus();
    });
  }
}

/* ----------------------------------------------------------- 局部编辑（标注 → 生成 → 合成） */
/*
 * 原理（实测依据，见 能力清单.md 第 16 节）：
 *   Qwen-Image-2.1 的接口里**没有掩码参数**，但官方支持"把圈画在图上"这种视觉提示 ——
 *   实测：圈住眼睛要求改金色 / 涂肚子要求变红心，模型都只改了标记处。
 *   不过它本质上仍是"整图重绘 + 提示词约束"，标记外不保证逐点不变。
 *   所以工作台再做一步**确定性合成**：按用户画的区域，把模型结果贴回原图 →
 *   没画到的地方逐点不变，这才是真正的"局部编辑"。
 */

const mark = {
  strokes: [],      // [{points:[[x,y],...]}]，坐标归一化 0~1
  drawing: null,
  srcKey: "",
  srcs: [],         // [{key,label,url}]
  natural: [0, 0],
};

function renderMarkSources() {
  const sel = $("markSource");
  if (!sel) return;
  const items = [];
  if (state.shownJobId) {
    const j = state.history.find((x) => x.id === state.shownJobId);
    const f = j && j.images && j.images[0] && j.images[0].file;
    if (f) items.push({ key: "job:" + state.shownJobId, label: "本次结果", url: "/api/image?f=" + encodeURIComponent(f) });
  }
  state.history.forEach((j) => {
    if (!j.images || !j.images.length) return;
    if (state.shownJobId && j.id === state.shownJobId) return;
    const f = j.images[0].file;
    const p = j.params || {};
    const tag = (p.prompt || "").slice(0, 14) || j.id.slice(0, 8);
    items.push({
      key: "job:" + j.id,
      label: "历史 · " + tag,
      url: "/api/image?f=" + encodeURIComponent(f),
    });
  });
  state.refs.forEach((r) => {
    items.push({ key: "ref:" + r.name, label: "参考图 · " + r.name, url: r.url });
  });

  mark.srcs = items;
  const keep = items.some((i) => i.key === mark.srcKey) ? mark.srcKey : (items[0] ? items[0].key : "");
  sel.innerHTML = "";
  if (!items.length) {
    sel.add(new Option("（还没有可标注的图）", ""));
  } else {
    items.forEach((i) => sel.add(new Option(i.label, i.key)));
  }
  sel.value = keep;
  if (keep !== mark.srcKey) {
    mark.srcKey = keep;
    mark.strokes = [];
  }
  loadMarkImage();
}

function loadMarkImage() {
  const cv = $("markCanvas");
  if (!cv) return;
  const item = mark.srcs.find((i) => i.key === mark.srcKey);
  if (!item) {
    cv.width = 10; cv.height = 10;
    cv._img = null;
    cv._src = "";
    $("markEmpty").style.display = "flex";
    $("markEmpty").textContent = "先选择一张图（参考图 / 本次结果 / 历史图）";
    return;
  }
  // 同一张图不重复加载，否则用户在别的操作（如刷历史）后画到一半的标注会被清掉
  if (cv._src === item.url && cv._img) { drawMark(); return; }
  const im = new Image();
  im.onload = () => {
    // 画布像素尺寸跟随图片（上限 1024，够模型用；坐标存归一化值所以缩放无妨）
    const scale = Math.min(1, 1024 / Math.max(im.naturalWidth, im.naturalHeight));
    cv.width = Math.max(1, Math.round(im.naturalWidth * scale));
    cv.height = Math.max(1, Math.round(im.naturalHeight * scale));
    mark.natural = [im.naturalWidth, im.naturalHeight];
    cv._img = im;
    cv._src = item.url;
    $("markEmpty").style.display = "none";
    drawMark();
  };
  im.onerror = () => {
    $("markEmpty").style.display = "flex";
    $("markEmpty").textContent = "这张图加载失败，换一张试试";
  };
  im.src = item.url;
}

function drawMark() {
  const cv = $("markCanvas");
  const ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, cv.width, cv.height);
  if (cv._img) ctx.drawImage(cv._img, 0, 0, cv.width, cv.height);

  const b = brushPx(cv);
  ctx.lineJoin = ctx.lineCap = "round";
  ctx.strokeStyle = "rgba(255,48,48,0.78)";
  ctx.lineWidth = b * 2;                 // 半径换算成直径
  mark.strokes.forEach((st) => {
    const pts = st.points || [];
    if (pts.length === 1) {              // 单点也画成实心圆
      ctx.beginPath();
      ctx.arc(pts[0][0] * cv.width, pts[0][1] * cv.height, b, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,48,48,0.78)";
      ctx.fill();
      return;
    }
    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = p[0] * cv.width, y = p[1] * cv.height;
      if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    });
    ctx.stroke();
  });
}

function brushPx(cv) {
  const v = Number(($("markBrush") && $("markBrush").value) || 40);
  // 滑块是"屏幕上的像素半径"，换算成画布坐标下的半径
  const shown = cv.clientWidth || cv.width;
  return Math.max(3, v * (cv.width / Math.max(1, shown)));
}

function markPointFromEvent(cv, e) {
  const r = cv.getBoundingClientRect();
  const x = (e.clientX - r.left) / Math.max(1, r.width);
  const y = (e.clientY - r.top) / Math.max(1, r.height);
  return [Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))];
}

function initMarkUI() {
  const cv = $("markCanvas");
  if (!cv) return;

  $("markSource").addEventListener("change", () => {
    mark.srcKey = $("markSource").value;
    mark.strokes = [];
    loadMarkImage();
    setMarkStatus("");
  });

  $("markBrush").addEventListener("input", drawMark);

  cv.addEventListener("pointerdown", (e) => {
    if (!cv._img) return;
    cv.setPointerCapture(e.pointerId);
    mark.drawing = { points: [markPointFromEvent(cv, e)] };
    mark.strokes.push(mark.drawing);
    drawMark();
  });
  cv.addEventListener("pointermove", (e) => {
    if (!mark.drawing) return;
    mark.drawing.points.push(markPointFromEvent(cv, e));
    drawMark();
  });
  const stop = (e) => {
    if (!mark.drawing) return;
    mark.drawing = null;
    setMarkStatus("");
  };
  cv.addEventListener("pointerup", stop);
  cv.addEventListener("pointercancel", stop);

  $("btnMarkUndo").addEventListener("click", () => { mark.strokes.pop(); drawMark(); setMarkStatus(""); });
  $("btnMarkClear").addEventListener("click", () => { mark.strokes = []; drawMark(); setMarkStatus(""); });
  $("btnMarkAll").addEventListener("click", () => {
    // 全选：一整块矩形标注，等效"整图重绘"（想对比局部/整体的差异时用）
    mark.strokes = [{ points: [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]] }];
    drawMark();
    setMarkStatus("已全选画面（相当于整图重绘，仅用于对照）。");
  });
  $("btnMarkRun").addEventListener("click", runLocalEdit);
}

function setMarkStatus(html, kind) {
  const el = $("markStatus");
  if (!el) return;
  el.innerHTML = html || "";
  el.style.color = kind === "err" ? "var(--err)" : (kind === "ok" ? "var(--ok)" : "");
}

async function runLocalEdit() {
  const cv = $("markCanvas");
  const prompt = ($("markPrompt").value || "").trim();
  const item = mark.srcs.find((i) => i.key === mark.srcKey);

  if (!item || !cv._img) return setMarkStatus("先在「要标注的图」里选一张图。", "err");
  if (!mark.strokes.length) return setMarkStatus("请先在图上画出要修改的区域（圈一圈或涂一涂）。", "err");
  if (!prompt) { $("markPrompt").focus(); return setMarkStatus("请写清楚要把标注区域改成什么。", "err"); }
  if (state.activeJobId) return setMarkStatus("已有出图任务在进行中，请等它完成。", "err");

  const isRef = item.key.startsWith("ref:");
  setMarkStatus("① 正在把标注图交给模型重绘…");

  try {
    // 1) 把带标注的画布导出成 PNG 并上传（若来源本身就是参考图则直接复用，省一次上传）
    let refName;
    if (isRef && !mark.strokes.length) {
      refName = item.key.slice(4);
    } else {
      const blob = await new Promise((res) => cv.toBlob(res, "image/png"));
      if (!blob) throw new Error("标注图导出失败");
      const fd = new FormData();
      fd.append("file", blob, "marked.png");
      const up = await api("/api/upload", { method: "POST", body: fd });
      refName = up.name;
    }

    // 2) 按官方"标记引导"写法组织提示词，跑一次编辑生成
    const editPrompt =
      "This is an image with a red marking on it. Change ONLY what is inside the red marked area: "
      + prompt
      + ". Keep everything outside the red marking exactly unchanged, "
      + "and do not draw the red marking in the output.";
    const resp = await api("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: editPrompt,
        negative_prompt: "",
        steps: Number($("steps").value || 25),
        cfg: Number($("cfg").value || 1.0),
        seed: $("seed").value,
        sampler_name: $("sampler").value,
        scheduler: $("scheduler").value,
        reference_images: [refName],
        ref_resolution: 0,
        custom_canvas: false,
        transparent_bg: false,
      }),
    });
    const editJob = resp.job_id;
    state.activeJobId = editJob;
    setBusy(true, "局部修改中：模型正在重绘…", 0);
    pollProgress(editJob, { silentRender: true });

    // 3) 等这次生成结束
    await new Promise((resolve) => {
      const t = setInterval(() => {
        if (state.activeJobId !== editJob) { clearInterval(t); resolve(); }
      }, 500);
    });

    const job = await api("/api/jobs/" + editJob);
    if (!job.job || job.job.status !== "done" || !job.job.images.length) {
      setBusy(false);
      setMarkStatus("模型重绘失败：" + ((job.job && job.job.error) || "未知原因"), "err");
      return;
    }

    // 4) 关键一步：按标注区域把结果合成回基准图 —— 没画到的地方逐点不变
    setMarkStatus("② 正在按标注区域合成回原图…");
    let merged;
    if (isRef) {
      merged = await api("/api/merge-local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_ref: item.key.slice(4),
          edit_job_id: editJob,
          strokes: mark.strokes,
          brush: brushPx(cv) / Math.max(1, cv.width),
          feather: 2,
        }),
      });
    } else {
      merged = await api("/api/merge-local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_job_id: item.key.slice(4),
          edit_job_id: editJob,
          strokes: mark.strokes,
          brush: brushPx(cv) / Math.max(1, cv.width),
          feather: 2,
        }),
      });
    }

    setBusy(false);
    await loadJobs();
    state.shownJobId = merged.job_id;
    const full = await api("/api/jobs/" + merged.job_id);
    renderResult(full.job);
    renderMarkSources();
    setMarkStatus(
      "✅ 局部修改完成：只替换了标注区域（覆盖画面 " +
      (merged.masked_ratio * 100).toFixed(1) + "%），其余像素逐点沿用原图。",
      "ok");
  } catch (e) {
    setBusy(false);
    setMarkStatus("局部修改失败：" + e.message, "err");
  }
}


/* ----------------------------------------------------------- 图片查看器 */
/*
 * 点「生成结果」的大图或历史缩略图上的放大按钮 → 打开全屏查看器。
 * 支持：滚轮以光标为中心缩放、按住拖动平移、双击在 1:1 / 适应窗口间切换、
 *       Esc 关闭、下载原图。用 transform 做变换，图片本身始终是原始分辨率。
 */
const viewer = { url: "", scale: 1, tx: 0, ty: 0, natW: 0, natH: 0, dragging: false };

function openLightbox(url, name, meta) {
  const v = $("viewer");
  const img = $("vImg");
  if (!v || !img) return;
  viewer.url = url;
  viewer.scale = 1; viewer.tx = 0; viewer.ty = 0;
  $("viewerMeta").textContent = meta || name || "";
  $("vDownload").setAttribute("href", url);
  $("vDownload").setAttribute("download", name || "qwen21.png");
  img.onload = () => {
    viewer.natW = img.naturalWidth;
    viewer.natH = img.naturalHeight;
    fitLightbox();
  };
  img.src = url;
  v.hidden = false;
  v.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  const v = $("viewer");
  if (!v) return;
  v.classList.remove("open");
  v.hidden = true;
  $("vImg").removeAttribute("src");
  document.body.style.overflow = "";
}

function applyLightbox() {
  const img = $("vImg");
  if (!img) return;
  img.style.transform =
    "translate(" + viewer.tx + "px," + viewer.ty + "px) scale(" + viewer.scale + ")";
  $("vPct").textContent = Math.round(viewer.scale * 100) + "%";
}

function fitLightbox() {
  const stage = $("vStage");
  if (!stage || !viewer.natW) return;
  const pad = 28;
  const sw = stage.clientWidth - pad, sh = stage.clientHeight - pad;
  const s = Math.min(sw / viewer.natW, sh / viewer.natH, 1);
  viewer.scale = s > 0 ? s : 1;
  viewer.tx = 0; viewer.ty = 0;
  applyLightbox();
}

function zoomLightbox(factor, clientX, clientY) {
  const stage = $("vStage");
  if (!stage) return;
  const prev = viewer.scale;
  const next = Math.min(16, Math.max(0.05, prev * factor));
  if (next === prev) return;
  const r = stage.getBoundingClientRect();
  const cx = (clientX == null ? r.left + r.width / 2 : clientX) - (r.left + r.width / 2);
  const cy = (clientY == null ? r.top + r.height / 2 : clientY) - (r.top + r.height / 2);
  // 让光标下的像素保持不动
  viewer.tx = cx - (next / prev) * (cx - viewer.tx);
  viewer.ty = cy - (next / prev) * (cy - viewer.ty);
  viewer.scale = next;
  applyLightbox();
}

function initLightbox() {
  const v = $("viewer");
  if (!v) return;
  const stage = $("vStage");

  v.addEventListener("click", (e) => {
    if (e.target === v) closeLightbox();          // 点最外层空白关闭
  });
  $("vClose").addEventListener("click", closeLightbox);
  $("vFit").addEventListener("click", fitLightbox);
  $("vZoomIn").addEventListener("click", () => zoomLightbox(1.25));
  $("vZoomOut").addEventListener("click", () => zoomLightbox(1 / 1.25));
  $("vOne").addEventListener("click", () => {
    viewer.scale = 1; viewer.tx = 0; viewer.ty = 0; applyLightbox();
  });

  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoomLightbox(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
  }, { passive: false });

  stage.addEventListener("pointerdown", (e) => {
    viewer.dragging = true;
    viewer.px = e.clientX; viewer.py = e.clientY;
    stage.classList.add("dragging");
    stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener("pointermove", (e) => {
    if (!viewer.dragging) return;
    viewer.tx += e.clientX - viewer.px;
    viewer.ty += e.clientY - viewer.py;
    viewer.px = e.clientX; viewer.py = e.clientY;
    applyLightbox();
  });
  const stopDrag = (e) => {
    if (!viewer.dragging) return;
    viewer.dragging = false;
    stage.classList.remove("dragging");
  };
  stage.addEventListener("pointerup", stopDrag);
  stage.addEventListener("pointercancel", stopDrag);

  stage.addEventListener("dblclick", () => {
    if (viewer.scale > 0.999 && Math.abs(viewer.scale - 1) < 0.001) fitLightbox();
    else { viewer.scale = 1; viewer.tx = 0; viewer.ty = 0; applyLightbox(); }
  });

  window.addEventListener("keydown", (e) => {
    if (!v.classList.contains("open")) return;
    if (e.key === "Escape") closeLightbox();
    else if (e.key === "+" || e.key === "=") zoomLightbox(1.25);
    else if (e.key === "-") zoomLightbox(1 / 1.25);
    else if (e.key === "0") fitLightbox();
    else if (e.key === "1") { viewer.scale = 1; viewer.tx = 0; viewer.ty = 0; applyLightbox(); }
  });

  window.addEventListener("resize", () => {
    if (v.classList.contains("open")) fitLightbox();
  });
}

/* ----------------------------------------------------------- 生成 */

async function generate() {
  hideMsg();
  const prompt = $("prompt").value.trim();
  if (!prompt) {
    showMsg("提示词不能为空，请输入内容后再生成。");
    $("prompt").focus();
    return;
  }
  if (state.activeJobId) return;

  const payload = {
    prompt: prompt,
    negative_prompt: $("negative").value,
    steps: $("steps").value,
    cfg: $("cfg").value,
    width: $("width").value,
    height: $("height").value,
    seed: $("seed").value,
    sampler_name: $("sampler").value,
    scheduler: $("scheduler").value,
    reference_images: state.refs.map((r) => r.name),
    ref_resolution: $("refRes") ? $("refRes").value : 0,
    custom_canvas: $("customCanvas") ? $("customCanvas").checked : false,
    transparent_bg: $("transparentBg") ? $("transparentBg").checked : false,
  };

  setBusy(true, "正在提交任务…", 0);

  let resp;
  try {
    resp = await api("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    setBusy(false);
    let extra = "";
    if (e.status === 503) {
      extra = "请按上方提示补齐权重，或检查 ComfyUI 是否正常。";
    } else if (e.status === 429) {
      extra = "请等待当前任务完成。";
    }
    showMsg(e.message, e.status === 429 ? "warn" : "err", extra);
    return;
  }

  state.activeJobId = resp.job_id;
  state.shownJobId = resp.job_id;
  setBusy(true, "正在推理…", 0);
  pollProgress(resp.job_id);
}

function setBusy(busy, label, pct) {
  const btn = $("btnGen");
  btn.disabled = busy;
  btn.textContent = busy ? "出图中，请稍候…" : "开始生成";
  // 生成条常驻在左栏底部：出图时收起次要说明，把高度让给进度
  const bar = btn.closest(".generate-bar");
  if (bar) bar.classList.toggle("busy", !!busy);
  const w = $("progWrap");
  if (busy) {
    w.classList.add("show");
    $("progLabel").innerHTML = '<span class="spinner"></span>' + escapeHtml(label || "正在推理…");
    $("progBar").style.width = (pct || 0) + "%";
    $("progPct").textContent = (pct || 0) + "%";
  } else {
    w.classList.remove("show");
    const track = $("progBar") && $("progBar").parentElement;
    if (track) track.classList.remove("indeterminate");
    $("progBar").style.width = "0%";
  }
}

function pollProgress(jobId, opts) {
  const silent = !!(opts && opts.silentRender);   // 局部编辑流程要自己控制渲染，别被轮询打断
  if (state.polling) clearInterval(state.polling);
  state.polling = setInterval(async () => {
    let p;
    try {
      p = await api("/api/progress/" + jobId);
    } catch (e) {
      return;
    }

    if (p.status === "running") {
      const pct = Math.max(p.progress || 0, 1);
      const known = p.step != null && p.total_steps;   // 还不知道步数 → 进度条走未定态
      const bar = $("progBar");
      const track = bar.parentElement;
      if (track) track.classList.toggle("indeterminate", !known);
      bar.style.width = pct + "%";
      $("progPct").textContent = (known ? pct.toFixed(0) : "…") + (known ? "%" : "");
      const wrap = $("progWrap");
      if (wrap) wrap.setAttribute("aria-valuenow", known ? String(pct.toFixed(0)) : "0");
      let label = "正在推理…";
      if (known) {
        label = "去噪中：第 " + p.step + " / " + p.total_steps + " 步";
      }
      if (p.elapsed != null) label += "（已用 " + fmtDuration(p.elapsed) + "）";
      $("progLabel").innerHTML = '<span class="spinner"></span>' + escapeHtml(label);
      return;
    }

    // 结束
    clearInterval(state.polling);
    state.polling = null;
    state.activeJobId = null;
    setBusy(false);

    if (p.status === "error") {
      const e = p.error || "未知错误";
      let extra = "";
      const low = e.toLowerCase();
      if (low.includes("out of memory") || low.includes("outofmemory") || low.includes("显存")) {
        extra = "建议：把尺寸降到 1024×1024 或更小、把步数降到 20 以下，然后重试。";
        $("width").value = 1024; $("height").value = 1024;
      }
      showMsg("出图失败：" + e, "err", extra);
      return;
    }

    // 成功：拉完整任务数据
    if (silent) return;
    try {
      const full = await api("/api/jobs/" + jobId);
      renderResult(full.job);
      await loadJobs();
    } catch (err) {
      showMsg("结果读取失败：" + err.message);
    }
  }, 900);
}

/* ----------------------------------------------------------- 结果渲染 */

function renderResult(job) {
  const stage = $("stage");
  const meta = $("meta");
  if (job && job.id) state.shownJobId = job.id;
  renderMarkSources();
  // 有图时让结果区吃掉剩余高度：有图就不必再滚动，点开还能放大
  if (stage && meta) stage.classList.toggle("has-image", !!(job && job.images && job.images.length));

  if (!job.images || !job.images.length) {
    meta.style.display = "none";
    stage.innerHTML = '<div class="placeholder"><span class="big">本次任务没有产出图片</span>' +
      '请检查上方提示或换一组参数重试</div>';
    return;
  }

  const img = job.images[0];
  const url = "/api/image?f=" + encodeURIComponent(img.file);
  const alpha = img.alpha || null;
  const hasAlpha = !!(alpha && alpha.transparent_ratio > 0.01);
  stage.classList.toggle("alpha", hasAlpha);
  stage.innerHTML = '<img id="mainImg" src="' + url + '" alt="生成结果" title="点击放大查看">';
  $("mainImg").addEventListener("load", function () {
    // 按原始分辨率显示，不拉伸变形
    this.style.width = "auto";
    this.style.height = "auto";
  });

  const p = job.params || {};
  const dlName = (p.seed != null ? "qwen21_seed" + p.seed : "qwen21") + ".png";
  const viewMeta = (p.width || "?") + " × " + (p.height || "?")
    + (p.seed != null ? "  ·  seed " + p.seed : "")
    + (p.mode === "edit" ? "  ·  图像编辑" : "  ·  文生图")
    + (hasAlpha ? "  ·  透明 " + (alpha.transparent_ratio * 100).toFixed(1) + "%" : "");
  // 点大图 → 打开查看器（放大 / 平移 / 下载）
  stage.title = "点击放大查看";
  stage.addEventListener("click", () => openLightbox(url, dlName, viewMeta));
  const rows = [
    ["提示词", p.prompt],
    ["负向提示词", (p.negative_prompt && p.negative_prompt.trim()) || "（空）"],
    ["模式", p.mode === "edit" ? "图像编辑（含参考图）" : "文生图"],
    ["透明背景", p.transparent_bg
      ? (hasAlpha
          ? "已开启 · 实测透明像素 " + (alpha.transparent_ratio * 100).toFixed(1) + "%"
          : "已开启 · 未检出透明像素（换个种子再试）")
      : "未开启"],
    ["尺寸", p.width + " × " + p.height],
    ["采样步数", p.steps],
    ["引导强度", p.cfg + (p.cfg > 1 ? "（负向提示词生效）" : "（不开引导）")],
    ["随机种子", p.seed + (p.seed_was_random ? "（随机）" : "（固定）")],
    ["采样器 / 调度器", p.sampler_name + " / " + p.scheduler],
    ["本次耗时", fmtDuration(job.elapsed)],
    ["参考图", (p.reference_images && p.reference_images.length)
      ? p.reference_images.join("、") + (p.ref_has_alpha ? "（含 alpha）" : "")
      : "无"],
    ["输出通道", alpha
      ? (alpha.mode === "no-alpha" ? "RGB（无 alpha）" : alpha.mode + "，alpha " + alpha.min + "~" + alpha.max)
      : "—"],
  ];

  let html = '<table>';
  rows.forEach(([k, v]) => {
    html += '<tr><td>' + escapeHtml(k) + '</td><td class="pval">' + escapeHtml(v) + '</td></tr>';
  });
  html += '</table>';

  html += '<div class="actions">' +
    '<button class="small" id="btnView">放大查看</button>' +
    '<a href="' + url + '" download="' + escapeHtml(dlName) + '"><button class="small">' +
    (hasAlpha ? "下载透明 PNG（RGBA）" : "下载这张图片") + '</button></a>' +
    '<button class="small" id="btnReuse">用这组参数再生成</button>' +
    '</div>';
  if (hasAlpha) {
    html += '<div class="note">这张图带真实 alpha 通道（透明像素 ' +
      (alpha.transparent_ratio * 100).toFixed(1) + '%）。下载后用支持透明的软件打开即可看到透明背景；' +
      '本地预览的棋盘格是工作台加的背景，不是图片内容。</div>';
  }

  meta.innerHTML = html;
  meta.style.display = "block";

  const btnView = $("btnView");
  if (btnView) btnView.addEventListener("click", () => openLightbox(url, dlName, viewMeta));

  $("btnReuse").addEventListener("click", () => {
    $("prompt").value = p.prompt || "";
    $("negative").value = (p.negative_prompt || "").trim() === "" ? "" : p.negative_prompt;
    $("steps").value = p.steps;
    $("cfg").value = p.cfg;
    $("width").value = p.width;
    $("height").value = p.height;
    $("seed").value = p.seed_was_random ? "" : p.seed;
    $("sampler").value = p.sampler_name;
    $("scheduler").value = p.scheduler;
    if ($("transparentBg")) $("transparentBg").checked = !!p.transparent_bg;
    updateNegNote();
    $("prompt").focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

/* ----------------------------------------------------------- 历史 */

async function loadJobs() {
  let data;
  try {
    data = await api("/api/jobs");
  } catch (e) {
    return;
  }
  state.history = data.jobs || [];

  const box = $("history");
  box.innerHTML = "";
  const withImg = state.history.filter((j) => j.images && j.images.length);
  $("historyEmpty").style.display = withImg.length ? "none" : "block";
  withImg.forEach((j) => {
    const p = j.params || {};
    const d = document.createElement("div");
    d.className = "thumb" + (j.id === state.shownJobId ? " active" : "");
    const url = "/api/image?f=" + encodeURIComponent(j.images[0].file);
    const fname = (p.seed != null ? "qwen21_seed" + p.seed : "qwen21") + ".png";
    const vmeta = (p.width || "?") + " × " + (p.height || "?")
      + (p.seed != null ? "  ·  seed " + p.seed : "")
      + (p.mode === "edit" ? "  ·  图像编辑" : "  ·  文生图");
    d.innerHTML = '<img src="' + url + '" loading="lazy" alt="">' +
      '<button class="zoom" title="放大查看" aria-label="放大查看">⤢</button>' +
      '<div class="cap">' + escapeHtml(p.width + "×" + p.height + " · seed " + p.seed) + '</div>';
    // 放大按钮：直接开查看器，不切换当前结果
    d.querySelector(".zoom").addEventListener("click", (e) => {
      e.stopPropagation();
      openLightbox(url, fname, vmeta);
    });
    d.addEventListener("click", () => {
      state.shownJobId = j.id;
      renderResult(j);
      loadJobs();
      $("stage").scrollIntoView({ behavior: "smooth", block: "center" });
    });
    box.appendChild(d);
  });
  renderMarkSources();
}

/* ----------------------------------------------------------- 启动 */

document.addEventListener("DOMContentLoaded", init);
