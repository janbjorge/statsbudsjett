// Chart islands and small glue for the HTMX page. Everything else is rendered on the server.
// Islands read their data from data-* attributes and re-render after every HTMX swap.

const nb = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 });
const nb1 = new Intl.NumberFormat("nb-NO", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const kr = v => nb.format(Math.round(v)) + " kr";
// Same steps as fmt.amount on the server: mrd. from 1 bn, mill. from 1 mill., plain kroner below that
const amount = bn => Math.abs(bn) >= 1 ? nb1.format(bn) + " mrd. kr" : Math.abs(bn) >= 0.001 ? nb.format(bn * 1000) + " mill. kr" : kr(bn * 1e9);
const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- tooltip ----------
const tip = () => document.getElementById("tip");
function showTip(ev, html) {
  const t = tip(); t.innerHTML = html; t.style.opacity = 1;
  const r = t.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
  t.style.left = x + "px"; t.style.top = y + "px";
}
const hideTip = () => { tip().style.opacity = 0; };
// A tap shows the tip and nothing moves it away on a phone; it is fixed, so it would float over the page while scrolling
addEventListener("scroll", hideTip, { passive: true });
document.addEventListener("mousemove", ev => {
  const el = ev.target.closest?.("[data-tip]");
  if (el) showTip(ev, el.dataset.tip); else if (!ev.target.closest?.(".chart-mark")) hideTip();
});

// ---------- "For deg": turn the visible inputs into the shareable query ----------
document.addEventListener("htmx:configRequest", ev => {
  const form = ev.detail.elt.closest?.(".meg-form");
  if (!form) return;
  // Fields hidden by the form's CSS (a second adult, an unticked income, the child ages) count as 0
  const shown = el => el.offsetParent !== null;
  const digits = el => shown(el) && (el.value || "").replace(/[^\d]/g, "") || "0";
  const params = {
    meg: [...form.querySelectorAll("[data-persona]:checked")].map(c => c.value).join(","),
    barn: [...form.querySelectorAll("[data-kid]")].map(digits).join(","),
    lonn: [...form.querySelectorAll('[data-money="lonn"]')].map(digits).join(","),
    pensjon: [...form.querySelectorAll('[data-money="pensjon"]')].map(digits).join(","),
    naering: [...form.querySelectorAll('[data-money="naering"]')].map(digits).join(","),
    naering_type: [...form.querySelectorAll("[data-business-kind]")].map(s => s.value).join(","),
  };
  for (const [k, v] of Object.entries(params)) {
    if (ev.detail.parameters instanceof FormData) ev.detail.parameters.set(k, v);
    else ev.detail.parameters[k] = v;
  }
});

document.addEventListener("click", async ev => {
  const copy = ev.target.closest("[data-copy-url]");
  if (copy) {
    try { await navigator.clipboard.writeText(location.href); copy.textContent = "Lenken er kopiert"; }
    catch { prompt("Kopier lenken:", location.href); }
    setTimeout(() => { copy.textContent = "Kopier lenke til valgene dine"; }, 2000);
  }
  const preset = ev.target.closest("[data-set-tax]");
  if (preset) {
    const input = document.getElementById("tax");
    input.value = nb.format(+preset.dataset.setTax);
    document.querySelectorAll("[data-set-tax]").forEach(b => b.setAttribute("aria-pressed", b === preset));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dataset.mine = preset.id === "my-tax" ? "1" : "";
  }
});
// Kroner fields show plain digits while you type and 650 000, like the server renders them, once you leave
const onlyDigits = s => [...s].filter(c => c >= "0" && c <= "9").join("");
const isKroner = el => el.matches?.("[data-money], #tax");
document.addEventListener("focusin", ev => { if (isKroner(ev.target)) ev.target.value = onlyDigits(ev.target.value); });
document.addEventListener("focusout", ev => {
  const el = ev.target, raw = onlyDigits(el.value || "");
  if (isKroner(el)) el.value = raw ? nb.format(+raw) : "";
});
// Typing your own amount stops the receipt from following "For deg"
document.addEventListener("input", ev => { if (ev.isTrusted && ev.target.id === "tax") ev.target.dataset.mine = ""; });
// "For deg" swaps in a new "Din skatt" chip; if the receipt showed your tax, move it to the new amount
document.addEventListener("htmx:oobAfterSwap", ev => {
  if (ev.detail.target.id === "my-tax" && document.getElementById("tax").dataset.mine && !ev.detail.target.hidden) ev.detail.target.click();
});

// ---------- treemap of one budget level ----------
function drawTreemap(el) {
  const nodes = JSON.parse(el.dataset.nodes);
  const W = el.clientWidth || 800, H = Math.round(Math.min(560, Math.max(320, W * 0.56)));
  el.style.height = H + "px";
  const root = d3.hierarchy({ children: nodes }).sum(d => d.size || 0).sort((a, b) => b.value - a.value);
  d3.treemap().size([W, H]).paddingInner(3).round(true)(root);
  const parent = d3.sum(nodes, n => n.v);
  el.replaceChildren(...root.leaves().map(leaf => {
    const n = leaf.data, w = leaf.x1 - leaf.x0, h = leaf.y1 - leaf.y0;
    const div = document.createElement("div");
    div.className = "cell chart-mark" + (n.href ? "" : " leaf");
    Object.assign(div.style, { left: leaf.x0 + "px", top: leaf.y0 + "px", width: w + "px", height: h + "px", background: `var(--g-${n.slot})` });
    if (w > 70 && h > 34) div.innerHTML = `<div class="n">${esc(n.name)}</div>` + (h > 54 ? `<div class="v">${amount(n.v)}</div>` : "");
    div.addEventListener("mousemove", ev => showTip(ev, `<b>${esc(n.name)}</b><br>${amount(n.v)} · ${nb1.format(n.v / parent * 100)} %` + (n.href ? `<br><span class="muted">Klikk for å se mer</span>` : "")));
    div.addEventListener("mouseleave", hideTip);
    if (n.href) div.addEventListener("click", () => { hideTip(); htmx.ajax("GET", n.href, { target: "#tree", swap: "outerHTML" }); });
    return div;
  }));
}

// ---------- every kommune as a dot: money per person against population ----------
let kommuner;
function drawStrip(el) {
  kommuner ??= JSON.parse(document.getElementById("kommuner-data").textContent);
  const all = kommuner, selected = el.dataset.selected, avg = +el.dataset.average;
  const W = el.clientWidth || 800, H = 300, m = { l: 64, r: 12, t: 40, b: 46 };
  const [lo, hi] = d3.extent(all, k => k.pp);
  const [plo, phi] = d3.extent(all, k => k.pop);
  const x = d3.scaleLog().domain([lo * 0.95, hi * 1.05]).range([m.l, W - m.r]);
  const yScale = d3.scaleLog().domain([plo * 0.8, phi * 1.25]).range([H - m.b, m.t]);
  const y = k => yScale(k.pop);
  const svg = d3.create("svg").attr("viewBox", [0, 0, W, H]);
  const ticks = [60, 80, 100, 150, 200, 300, 500].map(v => v * 1000).filter(v => v > lo * 0.95 && v < hi * 1.05 && (W >= 500 || [100000, 200000, 500000].includes(v)));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).tickValues(ticks).tickFormat(v => nb.format(v / 1000) + " 000 kr").tickSizeOuter(0));
  const yTicks = [1000, 10000, 100000, 1000000].filter(v => v > plo * 0.8 && v < phi * 1.25);
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(yScale).tickValues(yTicks).tickFormat(v => nb.format(v)).tickSizeOuter(0));
  const label = (t, attrs) => { const el = svg.append("text").attr("class", "chart-note").attr("fill", cssVar("--text-muted")).text(t); for (const [k, v] of Object.entries(attrs)) el.attr(k, v); };
  label("Frie inntekter per innbygger →", { x: W - m.r, y: H - 8, "text-anchor": "end" });
  label("↑ Innbyggere", { x: 0, y: 12 });
  // "snitt" sits one line below the axis title, right of the line, so the two never meet on a narrow screen
  svg.append("line").attr("x1", x(avg)).attr("x2", x(avg)).attr("y1", m.t - 16).attr("y2", H - m.b).attr("stroke", cssVar("--text-muted"));
  svg.append("text").attr("x", x(avg) + 4).attr("y", m.t - 8).attr("class", "chart-note").attr("fill", cssVar("--text-muted")).text("snitt");
  const pick = k => {
    document.getElementById("kom").value = k.f ? `${k.n} (${k.f})` : k.n;
    htmx.ajax("GET", "/kommune?k=" + k.nr, { target: "#kommune-out", swap: "outerHTML" });
  };
  svg.append("g").selectAll("circle").data(all.filter(k => k.nr !== selected)).join("circle")
    .attr("class", "chart-mark").attr("cx", k => x(k.pp)).attr("cy", y).attr("r", 4)
    .attr("fill", cssVar("--other")).attr("fill-opacity", .55).style("cursor", "pointer")
    // An invisible stroke widens the hit area from 8 to 20 px, so a dot can be hit with a finger
    .attr("stroke", "transparent").attr("stroke-width", 12)
    .on("mousemove", (ev, k) => showTip(ev, `<b>${esc(k.n)}</b> (${esc(k.f ?? "")})<br>${kr(k.pp)} per innbygger<br>${nb.format(k.pop)} innbyggere`))
    .on("mouseleave", hideTip).on("click", (ev, k) => { hideTip(); pick(k); });
  const s = all.find(k => k.nr === selected);
  if (s) {
    const cx = x(s.pp), cy = y(s);
    svg.append("circle").attr("cx", cx).attr("cy", cy).attr("r", 8).attr("fill", cssVar("--accent")).attr("stroke", cssVar("--surface-1")).attr("stroke-width", 2);
    // Beside the dot, on the side with more room, so it stays clear of the labels above the plot
    const left = cx > (m.l + W - m.r) / 2;
    svg.append("text").attr("x", left ? cx - 13 : cx + 13).attr("y", cy).attr("dy", "0.35em").attr("text-anchor", left ? "end" : "start")
      .attr("class", "chart-label").attr("fill", cssVar("--text-primary"))
      .attr("paint-order", "stroke").attr("stroke", cssVar("--surface-1")).attr("stroke-width", 3).attr("stroke-linejoin", "round").text(s.n);
  }
  el.replaceChildren(svg.node());
}

// ---------- the oil fund over time: the budget share on /, the share spent on /oljefondet ----------
const FUND = {
  spend: { unit: v => nb1.format(v) + " %", axis: v => v + " %", tip: v => nb1.format(v) + " % av fondet", ref: "expected" },
  share: { unit: v => nb1.format(v) + " %", axis: v => v + " %", tip: v => nb1.format(v) + " % av utgiftene" },
};
function drawFund(el) {
  const key = el.dataset.key, c = FUND[key], all = JSON.parse(el.dataset.fund);
  const s = all.filter(d => d[key] != null).map(d => ({ ...d, value: d[key] })), last = s[s.length - 1];
  const W = el.clientWidth || 800, H = Math.max(180, Math.min(260, W * 0.3)), m = { l: 36, r: 16, t: 20, b: 28 };
  const x = d3.scaleLinear().domain(d3.extent(all, d => d.year)).range([m.l, W - m.r]);
  const top = d3.max(s, d => Math.max(d.value, c.ref ? d[c.ref] : 0));
  const y = d3.scaleLinear().domain([0, top * 1.1]).nice().range([H - m.b, m.t]);
  const svg = d3.create("svg").attr("viewBox", [0, 0, W, H]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).ticks(W < 500 ? 4 : 9).tickFormat(d3.format("d")).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(y).ticks(4).tickSize(-(W - m.l - m.r)).tickFormat(c.axis))
    .call(g => g.select(".domain").remove()).call(g => g.selectAll(".tick line").attr("stroke", cssVar("--hairline")));
  if (c.ref) {
    // A step: the expected return changes between two years, it does not slide
    const steps = s.flatMap((d, i) => i && s[i - 1][c.ref] !== d[c.ref] ? [[d.year, s[i - 1][c.ref]], [d.year, d[c.ref]]] : [[d.year, d[c.ref]]]);
    svg.append("path").datum(steps).attr("fill", "none").attr("stroke", cssVar("--text-muted")).attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "2 4").attr("d", d3.line().x(p => x(p[0])).y(p => y(p[1])));
    // Label the middle of the first level, clear of the end labels
    const level = s.filter(d => d[c.ref] === s[0][c.ref]), mid = level[Math.floor(level.length / 2)];
    svg.append("text").attr("x", x(mid.year)).attr("y", y(mid[c.ref]) - 8).attr("text-anchor", "middle").attr("class", "chart-note")
      .attr("fill", cssVar("--text-secondary")).text(`Forventet realavkastning, ${nb.format(mid[c.ref])} %`);
  }
  const line = d3.line().x(d => x(d.year)).y(d => y(d.value));
  const actual = s.filter(d => !d.forecast);
  svg.append("path").datum(actual).attr("fill", "none").attr("stroke", cssVar("--series-1")).attr("stroke-width", 2).attr("d", line);
  if (last.forecast) svg.append("path").datum([actual[actual.length - 1], last]).attr("fill", "none").attr("stroke", cssVar("--series-1"))
    .attr("stroke-width", 2).attr("stroke-dasharray", "4 4").attr("d", line);
  // End labels go on the side away from the line: below when the neighbouring point or the dashed level is higher,
  // kept above the x axis
  for (const [d, near, anchor, dx] of [[s[0], s[1], "start", 8], [last, actual[actual.length - (last.forecast ? 1 : 2)], "end", -8]]) {
    const below = near.value > d.value || (c.ref && d[c.ref] > d.value);
    svg.append("circle").attr("cx", x(d.year)).attr("cy", y(d.value)).attr("r", 5).attr("fill", cssVar("--series-1")).attr("stroke", cssVar("--surface-1")).attr("stroke-width", 2);
    svg.append("text").attr("x", x(d.year) + dx).attr("y", below ? Math.min(y(d.value) + 22, H - m.b - 6) : y(d.value) - 12).attr("text-anchor", anchor).attr("class", "chart-label")
      .attr("fill", cssVar("--text-primary")).text(`${d.year}: ${c.unit(d.value)}`);
  }
  const hover = svg.append("g").style("display", "none");
  hover.append("line").attr("y1", m.t).attr("y2", H - m.b).attr("stroke", cssVar("--text-muted"));
  hover.append("circle").attr("r", 4).attr("fill", cssVar("--series-1"));
  svg.append("rect").attr("class", "chart-mark").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
    .on("mousemove", ev => {
      const [mx] = d3.pointer(ev);
      const d = s.reduce((a, b) => Math.abs(x(b.year) - mx) < Math.abs(x(a.year) - mx) ? b : a);
      hover.style("display", null);
      hover.select("line").attr("x1", x(d.year)).attr("x2", x(d.year));
      hover.select("circle").attr("cx", x(d.year)).attr("cy", y(d.value));
      const ref = c.ref ? `<br>Forventet realavkastning: ${nb1.format(d[c.ref])} %` : "";
      showTip(ev, `<b>${d.year}</b>${d.forecast ? " (forslag)" : ""}<br>${c.tip(d.value)}${ref}`);
    })
    .on("mouseleave", () => { hover.style("display", "none"); hideTip(); });
  el.replaceChildren(svg.node());
}

const FUND_PARTS = [
  { key: "size", label: "Fondets verdi", color: "--text-primary", width: 2 },
  { key: "returns", label: "Avkastning", color: "--series-1", width: 1.5 },
  { key: "oil", label: "Olje inn", color: "--series-2", width: 1.5 },
  { key: "krone", label: "Kronekurs", color: "--series-4", width: 1.5 },
  { key: "withdraw", label: "Uttak", color: "--series-8", width: 1.5 },
];
function drawFundParts(el) {
  const s = JSON.parse(el.dataset.parts), last = s[s.length - 1];
  const W = el.clientWidth || 800, H = Math.max(240, Math.min(340, W * 0.4));
  const named = W >= 560;
  const textOf = c => named ? `${c.label}: ${nb.format(last[c.key])}` : nb.format(last[c.key]);
  const probeSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const probe = document.createElementNS("http://www.w3.org/2000/svg", "text");
  probe.setAttribute("class", "chart-label");
  probeSvg.append(probe);
  el.append(probeSvg);
  let labelW = 0;
  for (const c of FUND_PARTS) {
    probe.textContent = textOf(c);
    labelW = Math.max(labelW, probe.getComputedTextLength());
  }
  probeSvg.remove();
  const m = { l: 52, r: Math.ceil(Math.max(labelW, named ? 180 : 64)) + 20, t: 20, b: 28 };
  const x = d3.scaleLinear().domain(d3.extent(s, d => d.year)).range([m.l, W - m.r]);
  const lo = d3.min(s, d => d3.min(FUND_PARTS, c => d[c.key]));
  const hi = d3.max(s, d => d3.max(FUND_PARTS, c => d[c.key]));
  const y = d3.scaleLinear().domain([Math.min(0, lo) * 1.08, hi * 1.12]).nice().range([H - m.b, m.t]);
  const svg = d3.create("svg").attr("viewBox", [0, 0, W, H]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).ticks(W < 500 ? 4 : 9).tickFormat(d3.format("d")).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(v => nb.format(v)))
    .call(g => g.select(".domain").remove()).call(g => g.selectAll(".tick line").attr("stroke", cssVar("--hairline")));
  svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0))
    .attr("stroke", cssVar("--text-muted")).attr("stroke-width", 1);
  const line = c => d3.line().x(d => x(d.year)).y(d => y(d[c.key]));
  for (const c of FUND_PARTS) {
    svg.append("path").datum(s).attr("fill", "none").attr("stroke", cssVar(c.color)).attr("stroke-width", c.width).attr("d", line(c));
  }
  const gap = 16, loY = m.t + 8, hiY = H - m.b - 8;
  const labels = FUND_PARTS.map(c => ({ ...c, y: y(last[c.key]), text: textOf(c) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) labels[i].y = Math.max(labels[i].y, labels[i - 1].y + gap);
  if (labels.at(-1).y > hiY) {
    labels.at(-1).y = hiY;
    for (let i = labels.length - 2; i >= 0; i--) labels[i].y = Math.min(labels[i].y, labels[i + 1].y - gap);
  }
  if (labels[0].y < loY) {
    labels[0].y = loY;
    for (let i = 1; i < labels.length; i++) labels[i].y = Math.max(labels[i].y, labels[i - 1].y + gap);
  }
  for (const c of labels) {
    const fill = cssVar(c.color);
    svg.append("circle").attr("cx", x(last.year)).attr("cy", y(last[c.key])).attr("r", 4)
      .attr("fill", fill).attr("stroke", cssVar("--surface-1")).attr("stroke-width", 2);
    svg.append("text").attr("x", W - m.r + 10).attr("y", c.y).attr("dy", "0.35em")
      .attr("class", "chart-label").attr("fill", fill).text(c.text);
  }
  const hover = svg.append("g").style("display", "none");
  hover.append("line").attr("y1", m.t).attr("y2", H - m.b).attr("stroke", cssVar("--text-muted"));
  svg.append("rect").attr("class", "chart-mark").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
    .on("mousemove", ev => {
      const [mx] = d3.pointer(ev);
      const d = s.reduce((a, b) => Math.abs(x(b.year) - mx) < Math.abs(x(a.year) - mx) ? b : a);
      hover.style("display", null);
      hover.select("line").attr("x1", x(d.year)).attr("x2", x(d.year));
      showTip(ev, `<b>${d.year}</b>` + FUND_PARTS.map(c => `<br>${c.label}: ${nb.format(d[c.key])} mrd. kr`).join(""));
    })
    .on("mouseleave", () => { hover.style("display", "none"); hideTip(); });
  el.replaceChildren(svg.node());
}

// ---------- wiring ----------
function drawAll() {
  document.querySelectorAll(".treemap[data-nodes]").forEach(drawTreemap);
  document.querySelectorAll(".strip").forEach(drawStrip);
  document.querySelectorAll(".fund[data-key]").forEach(drawFund);
  document.querySelectorAll(".fund-parts").forEach(drawFundParts);
  document.dispatchEvent(new Event("charts:redraw"));
}

// Header menu: close on a pick, an outside click or Escape
document.addEventListener("click", ev => {
  const menu = document.querySelector("nav.top .more");
  if (menu?.open && (!menu.contains(ev.target) || ev.target.closest(".menu a"))) menu.open = false;
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape") document.querySelector("nav.top .more")?.removeAttribute("open");
});
// Phone menu sheet: a link to a section on the same page does not navigate, so close the sheet by hand
document.addEventListener("click", ev => {
  if (ev.target.closest("#nav-sheet a")) document.getElementById("nav-sheet").hidePopover?.();
});
let resizeTimer;
// Mobile browsers fire resize when the address bar hides; only a width change needs a redraw
let lastWidth = innerWidth;
addEventListener("resize", () => {
  if (innerWidth === lastWidth) return;
  lastWidth = innerWidth;
  clearTimeout(resizeTimer); resizeTimer = setTimeout(drawAll, 150);
});
document.addEventListener("htmx:afterSettle", drawAll);

const isDark = () => document.documentElement.dataset.theme === "dark" ||
  (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
document.addEventListener("DOMContentLoaded", () => {
  // Two toggles: the button in the desktop bar and the switch in the phone menu
  const toggles = document.querySelectorAll("[data-theme-toggle]");
  const label = () => toggles.forEach(b => b.hasAttribute("aria-pressed") ? b.setAttribute("aria-pressed", isDark()) : b.textContent = isDark() ? "Lys" : "Mørk");
  label();
  toggles.forEach(b => b.addEventListener("click", () => {
    document.documentElement.dataset.theme = isDark() ? "light" : "dark";
    localStorage.setItem("theme", document.documentElement.dataset.theme);
    label();
    drawAll();
  }));
  drawAll();
});
