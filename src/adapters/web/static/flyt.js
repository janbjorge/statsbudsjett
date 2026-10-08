// Pengestrømmen: Sankey per year on one shared scale, plus the 2026 → 2027 change chart.
// Details show in a fixed panel above the chart: hover on desktop, tap on mobile.
(() => {
const DATA = JSON.parse(document.getElementById("flyt-data").textContent);
const f1 = new Intl.NumberFormat("nb-NO", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmt = v => f1.format(v);
const signed = v => (v > 0 ? "+" : v < 0 ? "−" : "±") + f1.format(Math.abs(v));
const color = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const html = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Colour follows the entity: income is slot 1, each expense group keeps its slot, the last group is gray
const groupVar = Object.fromEntries(DATA.groups.map((g, i) => [g, i < DATA.groups.length - 1 ? `--series-${i + 2}` : "--other"]));
const parentOf = {};
for (const fs of Object.values(DATA.flows)) for (const f of fs) if (f.level === 2) parentOf[f.target] = f.source;
function colorVar(name, level) {
  if (level === 0 || DATA.income.includes(name)) return "--series-1";
  if (name.startsWith("Statsbudsjettet")) return "--text-secondary";
  return groupVar[name] || groupVar[parentOf[name]] || "--other";
}

const totals = Object.fromEntries(Object.entries(DATA.flows).map(([y, fs]) => [y, d3.sum(fs.filter(f => f.level === 0), f => f.beløp)]));
const maxNodes = Math.max(...Object.values(DATA.flows).map(fs => fs.filter(f => f.level === 2).length + 1));
let year = "2027", unit = "nok", pinned = null;

function nodeOrder(flows) {
  const total = flows.find(f => f.level === 0).target;
  const income = DATA.income.filter(n => flows.some(f => f.source === n));
  const groups = DATA.groups.filter(n => flows.some(f => f.target === n));
  const leaves = groups.flatMap(g => flows.filter(f => f.level === 2 && f.source === g).sort((a, b) => b.beløp - a.beløp).map(f => f.target));
  return [...income, total, ...groups, ...leaves];
}

// ---------- info panel ----------
const info = document.getElementById("flow-info");
const HINT = matchMedia("(hover: hover)").matches
  ? "Hold musepekeren over en strøm for å se detaljer. Klikk for å holde valget fast."
  : "Trykk på en strøm eller en stolpe for å se detaljer.";

function describe(d, total) {
  const share = `${fmt(d.value)} mrd. kr <span class="muted">· ${f1.format(d.value / total * 100)} % av alt</span>`;
  if (d.source) {
    const ofSource = d.source.sourceLinks.length > 1 ? ` <span class="muted">· ${f1.format(d.value / d.source.value * 100)} % av ${html(d.source.name)}</span>` : "";
    return `<div class="t">${html(d.source.name)} → ${html(d.target.name)}</div><div>${share}${ofSource}</div>`;
  }
  const out = d.sourceLinks.slice().sort((a, b) => b.value - a.value);
  const parts = out.slice(0, 4).map(l => `${html(l.target.name)} <b>${fmt(l.value)}</b>`);
  if (out.length > 4) parts.push(`og ${out.length - 4} til`);
  const more = out.length ? `<div class="sub">Går til: ${parts.join(" · ")}</div>`
    : d.targetLinks.length ? `<div class="sub">Del av ${html(d.targetLinks[0].source.name)}</div>` : "";
  return `<div class="t">${html(d.name)}</div><div>${share}</div>${more}`;
}

function showInfo(d, total) {
  if (!d) { info.innerHTML = `<div class="muted">${HINT}</div>`; info.classList.remove("on"); return; }
  info.innerHTML = describe(d, total) + (d === pinned ? `<button class="share" type="button" data-unpin>Nullstill</button>` : "");
  info.classList.add("on");
}

// Below the chart: the chapters and posts of what was clicked. A flow opens its income source or its target.
function showDetail(d) {
  const n = !d.source ? d : d.level === 0 ? d.source : d.target;
  if (n.name.startsWith("Statsbudsjettet")) return;
  htmx.ajax("GET", `/flyt/del?vis=${encodeURIComponent(n.name)}`, { target: "#flow-detail", swap: "outerHTML" });
}

// ---------- Sankey ----------
function drawSankey() {
  const el = document.getElementById("sankey");
  const W = Math.max(el.parentElement.clientWidth - 2, 720);
  const narrow = W < 900;
  const NODE_W = 10, PAD = 14, TOP = 8;
  const KPX = (narrow ? 640 : 720) / d3.max(Object.values(totals));
  const flows = DATA.flows[year], total = totals[year];
  const order = nodeOrder(flows);
  const levelOf = { [order[DATA.income.length]]: 1 };
  flows.forEach(f => { if (f.level === 0) levelOf[f.source] = 0; if (f.level === 1) levelOf[f.target] = 2; if (f.level === 2) levelOf[f.target] = 3; });
  const H = d3.max(Object.values(totals)) * KPX + PAD * (maxNodes - 1) + TOP * 2;

  const sankey = d3.sankey()
    .nodeId(d => d.name).nodeWidth(NODE_W).nodePadding(PAD)
    .nodeAlign(d => levelOf[d.name]).nodeSort((a, b) => order.indexOf(a.name) - order.indexOf(b.name))
    .extent([[1, TOP], [W - 1, H - TOP]]);
  const graph = sankey({
    nodes: order.map(name => ({ name })),
    links: flows.map(f => ({ source: f.source, target: f.target, value: f.beløp, level: f.level })),
  });

  // Rescale to the shared px-per-billion, keeping d3's order and centring each column
  for (const nodes of d3.group(graph.nodes, d => d.layer).values()) {
    nodes.sort((a, b) => a.y0 - b.y0);
    const used = d3.sum(nodes, n => n.value * KPX) + PAD * (nodes.length - 1);
    let y = TOP + (H - TOP * 2 - used) / 2;
    for (const n of nodes) { const h = n.value * KPX; n.y0 = y; n.y1 = y + h; y += h + PAD; }
  }
  for (const l of graph.links) l.width = l.value * KPX;
  sankey.update(graph);

  const svg = d3.create("svg").attr("width", W).attr("height", H).attr("viewBox", [0, 0, W, H])
    .attr("role", "img").attr("aria-label", `Pengestrømmen i statsbudsjettet ${year}`);
  svg.append("rect").attr("width", W).attr("height", H).attr("fill", "transparent").on("click", () => { pinned = null; highlight(null); });

  const links = svg.append("g").attr("fill", "none").selectAll("path").data(graph.links).join("path")
    .attr("class", "link")
    .attr("d", d3.sankeyLinkHorizontal())
    .attr("stroke", d => color(colorVar(d.level === 0 ? d.source.name : d.target.name, d.level)))
    .attr("stroke-opacity", d => d.level === 0 ? 0.32 : 0.38)
    .attr("stroke-width", d => Math.max(1, d.width));

  const node = svg.append("g").selectAll("g").data(graph.nodes).join("g");
  node.append("rect")
    .attr("x", d => d.x0).attr("y", d => d.y0)
    .attr("width", d => d.x1 - d.x0).attr("height", d => Math.max(1, d.y1 - d.y0)).attr("rx", 2)
    .attr("fill", d => color(colorVar(d.name, levelOf[d.name])));

  // Left half reads rightwards, right half leftwards; the total's label sits above it
  const isTotal = d => levelOf[d.name] === 1;
  node.append("text")
    .attr("class", d => "node-label" + (isTotal(d) ? " big" : ""))
    .attr("x", d => isTotal(d) ? (d.x0 + d.x1) / 2 : d.x0 < W / 2 ? d.x1 + 6 : d.x0 - 6)
    .attr("y", d => isTotal(d) ? d.y0 - 12 : (d.y0 + d.y1) / 2).attr("dy", "0.35em")
    .attr("text-anchor", d => isTotal(d) ? "middle" : d.x0 < W / 2 ? "start" : "end")
    .call(t => t.append("tspan").text(d => d.name))
    .call(t => t.append("tspan").attr("class", "val").attr("dx", 5).text(d => fmt(d.value)));
  const hits = node.append("rect").attr("class", "hit")
    .attr("x", d => d.x0 - 8).attr("y", d => d.y0 - 5)
    .attr("width", d => d.x1 - d.x0 + 16).attr("height", d => Math.max(12, d.y1 - d.y0 + 10))
    .attr("fill", "transparent");

  function highlight(d) {
    svg.classed("dim", !!d);
    links.classed("hi", l => !!d && (l === d || l.source === d || l.target === d));
    showInfo(d, total);
  }
  for (const sel of [links, hits]) {
    sel.on("pointerenter", (ev, d) => { if (ev.pointerType === "mouse") highlight(d); })
      .on("pointerleave", () => highlight(pinned))
      .on("click", (ev, d) => { ev.stopPropagation(); pinned = pinned === d ? null : d; highlight(pinned); if (pinned) showDetail(d); });
  }
  info.onclick = ev => { if (ev.target.closest("[data-unpin]")) { pinned = null; highlight(null); } };

  pinned = null;
  highlight(null);
  el.replaceChildren(svg.node());
  el.parentElement.classList.toggle("overflows", W > el.parentElement.clientWidth);
  document.getElementById("sankey-title").textContent = `Statsbudsjettet ${year}`;
}

// ---------- change chart ----------
function diffRows() {
  const rows = [{ section: "Inntekter" }];
  DATA.diff.filter(d => d.level === 0).sort((x, y) => DATA.income.indexOf(x.key) - DATA.income.indexOf(y.key))
    .forEach(d => rows.push({ ...d, depth: 1 }));
  rows.push({ section: "Utgifter" });
  for (const g of DATA.groups) {
    const gd = DATA.diff.find(d => d.level === 1 && d.key === g);
    if (!gd) continue;
    rows.push({ ...gd, depth: 1 });
    DATA.diff.filter(d => d.level === 2 && d.parent === g).sort((x, y) => y.y2027 - x.y2027).forEach(d => rows.push({ ...d, depth: 2 }));
  }
  return rows;
}

function drawDiff() {
  const el = document.getElementById("diff");
  const Wd = Math.max(el.parentElement.clientWidth - 2, 640);
  const narrow = Wd < 900;
  const rows = diffRows();
  const val = d => unit === "nok" ? d.change : d.pct;
  const ROW = 28, SEC = 36, LABEL_W = narrow ? 220 : 300, VAL_W = narrow ? 104 : 124;
  let y = 8;
  rows.forEach(r => { r.y = y; y += r.section ? SEC : ROW; });
  const H = y + 30;
  const vals = rows.filter(r => !r.section).map(val).filter(v => v != null);
  const x = d3.scaleLinear().domain([Math.min(0, d3.min(vals)), Math.max(0, d3.max(vals))]).nice()
    .range([LABEL_W + VAL_W + 24, Wd - (narrow ? 56 : VAL_W)]);

  const svg = d3.create("svg").attr("width", Wd).attr("height", H).attr("viewBox", [0, 0, Wd, H])
    .attr("role", "img").attr("aria-label", "Endring per område fra 2026 til 2027");
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - 24})`)
    .call(d3.axisBottom(x).ticks(narrow ? 4 : 8).tickSize(-(H - 32))
      .tickFormat(v => (v > 0 ? "+" : "") + f1.format(v).replace(",0", "") + (unit === "pct" ? " %" : "")))
    .call(g => g.select(".domain").remove());
  svg.append("line").attr("class", "zero").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 4).attr("y2", H - 24);

  const g = svg.append("g").selectAll("g").data(rows).join("g").attr("transform", r => `translate(0,${r.y})`);
  g.filter(r => r.section).append("text").attr("class", "sec-label").attr("y", SEC - 10).text(r => r.section);

  const data = g.filter(r => !r.section)
    .attr("data-tip", r => `<b>${html(r.key)}</b>${r.parent ? ` <span class="muted">(${html(r.parent)})</span>` : ""}<br>` +
      `2026: ${fmt(r.y2026)} mrd.<br>2027: ${fmt(r.y2027)} mrd.<br>` +
      `Endring: <b>${signed(r.change)} mrd.</b> (${r.pct == null ? "ny" : signed(r.pct) + " %"})`);
  data.append("rect").attr("class", "row-hit").attr("width", Wd).attr("height", ROW).attr("rx", 4);
  data.filter(r => r.depth === 1).append("rect")
    .attr("y", ROW / 2 - 5).attr("width", 10).attr("height", 10).attr("rx", 2)
    .attr("fill", r => color(colorVar(r.key, r.level)));
  data.append("text").attr("class", r => `row-label l${r.depth}`)
    .attr("x", r => r.depth === 1 ? 16 : 28).attr("y", ROW / 2).attr("dy", "0.35em").text(r => r.key);
  data.append("text").attr("class", "val-label").attr("x", LABEL_W + VAL_W).attr("y", ROW / 2).attr("dy", "0.35em")
    .attr("text-anchor", "end").text(r => `${fmt(r.y2026)} → ${fmt(r.y2027)}`);

  const bh = r => r.depth === 1 ? 14 : 9;
  data.append("rect")
    .attr("x", r => Math.min(x(0), x(val(r) ?? 0))).attr("y", r => ROW / 2 - bh(r) / 2)
    .attr("width", r => Math.max(1, Math.abs(x(val(r) ?? 0) - x(0)))).attr("height", bh).attr("rx", 3)
    .attr("fill", r => color(val(r) >= 0 ? "--up" : "--down"))
    .attr("fill-opacity", r => r.depth === 1 ? 1 : 0.55);
  data.append("text").attr("class", "val-label")
    .attr("x", r => x(val(r) ?? 0) + (val(r) >= 0 ? 6 : -6)).attr("y", ROW / 2).attr("dy", "0.35em")
    .attr("text-anchor", r => val(r) >= 0 ? "start" : "end")
    .attr("font-weight", r => r.depth === 1 ? 600 : 400)
    .text(r => val(r) == null ? "ny" : signed(val(r)) + (unit === "pct" ? " %" : ""));

  el.replaceChildren(svg.node());
  el.parentElement.classList.toggle("overflows", Wd > el.parentElement.clientWidth);
  document.getElementById("diff-sub").textContent = unit === "nok"
    ? "Endring i mrd. kr. Blå er økning, rød er nedgang. Tallene i midten viser 2026 → 2027."
    : "Endring i prosent av 2026-beløpet. Små beløp kan gi store prosentvise endringer.";
}

function drawTable() {
  const rows = diffRows().filter(r => !r.section);
  document.getElementById("table").innerHTML =
    `<table class="tbl"><thead><tr><th>Område</th><th class="num">2026</th><th class="num">2027</th><th class="num">Endring</th><th class="num">%</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td>${r.depth === 2 ? "&nbsp;&nbsp;&nbsp;" : ""}${html(r.key)}</td><td class="num">${fmt(r.y2026)}</td><td class="num">${fmt(r.y2027)}</td>` +
      `<td class="num">${signed(r.change)}</td><td class="num">${r.pct == null ? "ny" : signed(r.pct)}</td></tr>`).join("") +
    `</tbody></table>`;
}

// ---------- wiring ----------
const press = (sel, on) => document.querySelectorAll(sel).forEach(b => b.setAttribute("aria-pressed", b === on));
document.querySelectorAll("[data-year]").forEach(b => b.addEventListener("click", () => { year = b.dataset.year; press("[data-year]", b); drawSankey(); }));
document.querySelectorAll("[data-unit]").forEach(b => b.addEventListener("click", () => { unit = b.dataset.unit; press("[data-unit]", b); drawDiff(); }));
document.addEventListener("charts:redraw", () => { drawSankey(); drawDiff(); drawTable(); });
})();
