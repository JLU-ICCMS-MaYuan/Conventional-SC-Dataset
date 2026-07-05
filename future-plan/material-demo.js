const demoState = {
  selectedElements: new Set(["La", "H"]),
  selectionMode: "combination",
  records: [
    { year: 2019, formula: "LaH10", type: "Hydride", pressure: "200 GPa", tc: "250 K", source: "Local", status: "Approved", doi: "10.1038/s41586-demo" },
    { year: 2015, formula: "H3S", type: "Hydride", pressure: "155 GPa", tc: "203 K", source: "Local", status: "Approved", doi: "10.1038/s41586-demo2" },
    { year: 2024, formula: "YH9", type: "Hydride", pressure: "180 GPa", tc: "185 K", source: "HTSC-2025", status: "External", doi: "-" },
  ],
};

function $(selector, root = document) {
  return root.querySelector(selector);
}

function $all(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

function showSnackbar(message) {
  let bar = $(".snackbar");
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "snackbar";
    document.body.appendChild(bar);
  }
  bar.textContent = message;
  bar.classList.add("demo-toast-visible");
  clearTimeout(showSnackbar.timer);
  showSnackbar.timer = setTimeout(() => bar.classList.remove("demo-toast-visible"), 2200);
}

function downloadMock(filename, content, type = "application/json") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showSnackbar(`已生成 ${filename}`);
}

function wireRows() {
  $all(".data-table tbody tr").forEach((row) => {
    row.addEventListener("click", () => {
      $all(".data-table tbody tr").forEach((item) => item.classList.remove("selected"));
      row.classList.add("selected");
      const cells = $all("td", row).map((cell) => cell.textContent.trim());
      const sheet = $(".side-sheet");
      if (sheet && cells.length) {
        const title = $("h2", sheet);
        if (title) title.textContent = "记录详情";
        const mono = $(".mono", sheet) || document.createElement("p");
        mono.className = "mono";
        mono.textContent = `${cells[1] || cells[0]} · ${cells[3] || "当前对象"} · ${cells[4] || cells.at(-1)}`;
        if (!mono.parentElement) sheet.insertBefore(mono, sheet.children[1] || null);
      }
      showSnackbar("详情面板已更新");
    });
  });
}

function wireChips() {
  $all(".toolbar .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const siblings = $all(".chip", chip.parentElement);
      siblings.forEach((item) => item.classList.remove("primary"));
      chip.classList.add("primary");
      showSnackbar(`已切换到：${chip.textContent.trim()}`);
    });
  });
}

function initUploadDemo() {
  const card = $(".content .grid article.card:nth-of-type(4) .card.filled") || $(".card.filled");
  if (card) {
    card.classList.add("demo-upload");
    card.innerHTML = "<strong>点击模拟上传 PDF / CIF / POSCAR</strong><span class=\"demo-muted\">选择后展示解析进度和完整性检查</span><div class=\"progress\" style=\"width:100%\"><span style=\"width:0%\"></span></div>";
    card.addEventListener("click", () => {
      $(".progress span", card).style.width = "100%";
      showSnackbar("文件已解析，结构来源仍需补充");
    });
  }
  $all("button").forEach((button) => {
    const text = button.textContent.trim();
    if (text.includes("保存")) button.addEventListener("click", () => showSnackbar("草稿已保存"));
    if (text.includes("提交")) button.addEventListener("click", () => showSnackbar("已提交到审核队列"));
  });
}

function initMaintenanceDemo() {
  wireRows();
  const batch = $all("button").find((button) => button.textContent.includes("批量"));
  if (batch) batch.addEventListener("click", () => showSnackbar("已模拟批量审核 2 条记录"));
  $all(".side-sheet button").forEach((button) => {
    button.addEventListener("click", () => showSnackbar(`审核动作：${button.textContent.trim()}`));
  });
}

function renderDiscoveryPanel() {
  const header = $(".page-header");
  if (!header || $("#discovery-interactive")) return;
  const panel = document.createElement("section");
  panel.id = "discovery-interactive";
  panel.className = "grid two-col demo-section";
  panel.innerHTML = `
    <article class="card elevated">
      <h2>SC-hotspot 热点概览</h2>
      <div class="grid two-col">
        <div><h3>Tc-year</h3><div class="mock-chart" data-chart="year"></div></div>
        <div><h3>Tc-pressure</h3><div class="mock-chart" data-chart="pressure"></div></div>
      </div>
      <div class="nobel-grid" style="margin-top:16px">
        ${["Onnes", "Bardeen", "Cooper", "Schrieffer", "Josephson", "Bednorz"].map((name) => `<div class="nobel-card"><strong>${name}</strong><span class="demo-muted">Nobel superconductivity lineage</span></div>`).join("")}
      </div>
    </article>
    <article class="card">
      <h2>SC-explore 元素周期表检索</h2>
      <input class="demo-input" id="formula-search" value="LaH10" aria-label="Formula search">
      <div class="periodic-mini" id="periodic-mini" style="margin:16px 0"></div>
      <div class="segmented" role="group">
        <button class="segment active" data-mode="combination">选择元素的组合</button>
        <button class="segment" data-mode="exact">仅包含选择元素</button>
        <button class="segment" data-mode="contains">包含所选元素</button>
      </div>
      <div class="toolbar" style="margin-top:16px">
        <span class="chip primary" id="selected-elements">La, H</span>
        <button class="button filled" id="enter-results">进入结果页</button>
        <button class="button outlined" id="clear-elements">清除选择</button>
      </div>
    </article>
  `;
  header.insertAdjacentElement("afterend", panel);
  renderMockCharts();
  renderPeriodicMini();
}

function renderMockCharts() {
  $all(".mock-chart, .chart").forEach((chart) => {
    chart.innerHTML = "";
    const points = chart.dataset.chart === "pressure"
      ? [[18, 70], [40, 55], [62, 38], [78, 26]]
      : [[12, 76], [32, 64], [58, 42], [84, 22]];
    points.forEach(([left, top], index) => {
      const point = document.createElement("button");
      point.className = "mock-point";
      point.style.left = `${left}%`;
      point.style.top = `${top}%`;
      point.title = demoState.records[index % demoState.records.length].formula;
      point.addEventListener("click", () => showSnackbar(`${point.title} 数据点已选中`));
      chart.appendChild(point);
    });
  });
}

function renderPeriodicMini() {
  const grid = $("#periodic-mini");
  if (!grid) return;
  const elements = ["H", "Li", "Be", "B", "C", "N", "O", "F", "Mg", "Al", "Si", "S", "Ca", "Y", "La", "Lu"];
  grid.innerHTML = elements.map((symbol, index) => `<button class="element-tile ${demoState.selectedElements.has(symbol) ? "selected" : ""}" data-symbol="${symbol}"><small>${index + 1}</small>${symbol}</button>`).join("");
  $all(".element-tile", grid).forEach((tile) => {
    tile.addEventListener("click", () => {
      const symbol = tile.dataset.symbol;
      if (demoState.selectedElements.has(symbol)) demoState.selectedElements.delete(symbol);
      else demoState.selectedElements.add(symbol);
      updateSelectedElements();
      tile.classList.toggle("selected");
    });
  });
  $all(".segment").forEach((button) => {
    button.addEventListener("click", () => {
      $all(".segment").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      demoState.selectionMode = button.dataset.mode;
      showSnackbar(`筛选模式：${button.textContent.trim()}`);
    });
  });
  $("#clear-elements")?.addEventListener("click", () => {
    demoState.selectedElements.clear();
    updateSelectedElements();
    $all(".element-tile").forEach((tile) => tile.classList.remove("selected"));
  });
  $("#enter-results")?.addEventListener("click", () => showSnackbar("已按当前元素组合刷新结果表格"));
}

function updateSelectedElements() {
  const label = $("#selected-elements");
  if (!label) return;
  label.textContent = demoState.selectedElements.size ? Array.from(demoState.selectedElements).sort().join(", ") : "未选择";
}

function initDiscoveryDemo() {
  renderDiscoveryPanel();
  wireRows();
  wireChips();
  $all("button").forEach((button) => {
    const text = button.textContent.trim();
    if (text.includes("JSON")) {
      button.addEventListener("click", () => downloadMock("sc-wiki-filtered-records.json", JSON.stringify({ records: demoState.records }, null, 2)));
    }
    if (text.includes("RIS")) {
      button.addEventListener("click", () => downloadMock("sc-wiki-filtered-citations.ris", "TY  - JOUR\nTI  - Mock superconductivity record\nER  -", "application/x-research-info-systems"));
    }
  });
}

function initKnowledgeDemo() {
  const card = $(".content .card");
  if (!card || $(".graph-canvas")) return;
  const graph = document.createElement("div");
  graph.className = "graph-canvas demo-section";
  graph.innerHTML = `
    <button class="graph-node active" style="left:8%;top:18%">Onnes 1911</button>
    <button class="graph-node" style="left:38%;top:30%">BCS 1957</button>
    <button class="graph-node" style="left:62%;top:16%">Cuprates 1986</button>
    <button class="graph-node" style="left:48%;top:62%">Hydrides 2015</button>
  `;
  card.insertAdjacentElement("afterend", graph);
  $all(".graph-node").forEach((node) => {
    node.addEventListener("click", () => {
      $all(".graph-node").forEach((item) => item.classList.remove("active"));
      node.classList.add("active");
      showSnackbar(`已选择节点：${node.textContent.trim()}`);
    });
  });
}

function initRagDemo() {
  const main = $(".content");
  if (!main || $(".chat-layout")) return;
  main.innerHTML = `
    <section class="page-header"><div><p class="eyebrow">RAG Question Answering</p><h1>SC-chat 三栏证据问答</h1><p>模拟旧版流式回答、引用映射和右侧文献来源面板。</p></div><button class="button outlined" id="new-chat">新对话</button></section>
    <section class="chat-layout">
      <aside class="card"><h2>会话</h2><div class="chip primary">LaH10 Tc</div><div class="chip" style="margin-top:8px">氢化物趋势</div></aside>
      <article class="card elevated"><h2>对话流</h2><div class="chat-feed" id="chat-feed"><div class="message assistant">可以问我一个超导问题，回答会带证据引用。</div></div><div class="toolbar" style="margin-top:16px"><input class="demo-input" id="chat-input" value="LaH10 在 200 GPa 附近的 Tc 是多少？"><button class="button filled" id="send-chat">发送</button></div></article>
      <aside class="card side-sheet"><h2>文献来源</h2><div id="evidence-list"><p class="demo-muted">发送问题后显示证据。</p></div></aside>
    </section>`;
  $("#send-chat").addEventListener("click", streamAnswer);
  $("#new-chat").addEventListener("click", () => {
    $("#chat-feed").innerHTML = "<div class=\"message assistant\">新对话已创建。</div>";
    $("#evidence-list").innerHTML = "<p class=\"demo-muted\">发送问题后显示证据。</p>";
    showSnackbar("新对话已创建");
  });
}

function streamAnswer() {
  const feed = $("#chat-feed");
  const input = $("#chat-input");
  const question = input.value.trim() || "LaH10 的代表 Tc 是多少？";
  feed.insertAdjacentHTML("beforeend", `<div class="message user">${question}</div>`);
  const answer = document.createElement("div");
  answer.className = "message assistant";
  feed.appendChild(answer);
  const text = "本地审核记录显示 LaH10 在 200 GPa 附近的代表 Tc 约为 250 K。证据来自论文片段 [1] 和本地记录 [2]。";
  let index = 0;
  const timer = setInterval(() => {
    answer.textContent = text.slice(0, index++);
    if (index > text.length) {
      clearInterval(timer);
      answer.innerHTML = text.replace("[1]", "<button class=\"cite-link\" data-evidence=\"1\">[1]</button>").replace("[2]", "<button class=\"cite-link\" data-evidence=\"2\">[2]</button>");
      renderEvidence();
      showSnackbar("回答完成，证据已更新");
    }
  }, 22);
}

function renderEvidence() {
  $("#evidence-list").innerHTML = `
    <div class="card filled evidence-card" data-evidence="1"><h3>[1] 论文片段</h3><p>LaH10 high-pressure superconductivity record.</p></div>
    <div class="card filled evidence-card" data-evidence="2" style="margin-top:12px"><h3>[2] 本地记录</h3><p>LaH10 · 200 GPa · representative_tc = experimental_tc.</p></div>
    <div class="card" style="margin-top:12px"><h3>候选记录</h3><span class="chip warning">非公开数据，需审核</span></div>`;
  $all(".cite-link").forEach((link) => link.addEventListener("click", () => selectEvidence(link.dataset.evidence)));
  $all(".evidence-card").forEach((card) => card.addEventListener("click", () => selectEvidence(card.dataset.evidence)));
}

function selectEvidence(id) {
  $all(".evidence-card").forEach((card) => card.classList.toggle("selected", card.dataset.evidence === id));
  showSnackbar(`已定位证据 [${id}]`);
}

function initPredictDemo() {
  const result = $(".side-sheet") || $(".card.elevated");
  const firstCard = $(".content .card");
  if (firstCard && !$("#predict-files")) {
    firstCard.insertAdjacentHTML("beforeend", `
      <div id="predict-files" class="grid two-col" style="margin-top:16px">
        <label class="demo-upload"><strong>选择 POSCAR / CONTCAR</strong><input type="file" class="demo-hidden" id="structure-file"></label>
        <label class="demo-upload"><strong>选择 PDOS_H.dat 与金属 PDOS</strong><input type="file" multiple class="demo-hidden" id="pdos-file"></label>
      </div>`);
  }
  $all(".demo-upload").forEach((label) => {
    label.addEventListener("click", () => showSnackbar("已模拟选择输入文件"));
  });
  $all("button").forEach((button) => {
    if (button.textContent.includes("预测") || button.textContent.includes("运行")) {
      button.addEventListener("click", () => {
        button.textContent = "预测中...";
        setTimeout(() => {
          button.textContent = "运行预测";
          if (result) result.innerHTML = "<h2>预测结果</h2><p class=\"eyebrow\">PREDICTED ONLY</p><h1>187.42 K</h1><p>f2 = 0.83，dos_H_ratio = 0.61，bonds_mean = 1.08 Å。该结果不会自动进入公开数据库。</p>";
          showSnackbar("预测完成");
        }, 900);
      });
    }
  });
}

function initCommunityDemo() {
  renderMockCharts();
  $all("button").forEach((button) => {
    const text = button.textContent.trim();
    if (text.includes("CSV")) button.addEventListener("click", () => downloadMock("personal-chart.csv", "formula,pressure,tc\nLaH10,200,250\nH3S,155,203", "text/csv"));
    if (text.includes("默认")) button.addEventListener("click", () => showSnackbar("已恢复当前图表默认配置"));
  });
  wireRows();
}

document.addEventListener("DOMContentLoaded", () => {
  const demo = document.body.dataset.demo;
  wireChips();
  if (demo === "upload") initUploadDemo();
  if (demo === "maintenance") initMaintenanceDemo();
  if (demo === "discovery") initDiscoveryDemo();
  if (demo === "knowledge") initKnowledgeDemo();
  if (demo === "rag") initRagDemo();
  if (demo === "predict") initPredictDemo();
  if (demo === "community") initCommunityDemo();
});
