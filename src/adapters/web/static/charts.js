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
  const digits = el => (el.value || "").replace(/[^\d]/g, "") || "0";
  const params = {
    meg: [...form.querySelectorAll("[data-persona]:checked")].map(c => c.value).join(","),
    barn: [...form.querySelectorAll("[data-kid]")].map(digits).join(","),
    lonn: [...form.querySelectorAll('[data-money="lonn"]')].map(digits).join(","),
    pensjon: [...form.querySelectorAll('[data-money="pensjon"]')].map(digits).join(","),
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
  }
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
function drawStrip(el) {
  const all = JSON.parse(el.dataset.kommuner), selected = el.dataset.selected, avg = +el.dataset.average;
  const W = el.clientWidth || 800, H = 300, m = { l: 64, r: 12, t: 26, b: 46 };
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
  const label = (t, attrs) => { const el = svg.append("text").attr("font-size", 12).attr("fill", cssVar("--text-muted")).text(t); for (const [k, v] of Object.entries(attrs)) el.attr(k, v); };
  label("Frie inntekter per innbygger →", { x: W - m.r, y: H - 8, "text-anchor": "end" });
  label("↑ Innbyggere", { x: 0, y: 12 });
  svg.append("line").attr("x1", x(avg)).attr("x2", x(avg)).attr("y1", m.t - 8).attr("y2", H - m.b).attr("stroke", cssVar("--text-muted"));
  svg.append("text").attr("x", x(avg)).attr("y", m.t - 12).attr("text-anchor", "middle").attr("font-size", 12).attr("fill", cssVar("--text-muted")).text("snitt");
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
    svg.append("text").attr("x", cx).attr("y", cy - 13).attr("text-anchor", cx > W - 80 ? "end" : cx < 80 ? "start" : "middle")
      .attr("font-weight", 650).attr("font-size", 13).attr("fill", cssVar("--text-primary")).text(s.n);
  }
  el.replaceChildren(svg.node());
}

// ---------- oil fund share over time ----------
function drawFund(el) {
  const s = JSON.parse(el.dataset.fund), last = s[s.length - 1];
  const W = el.clientWidth || 800, H = Math.max(240, Math.min(360, W * 0.4)), m = { l: 36, r: 16, t: 20, b: 28 };
  const x = d3.scaleLinear().domain(d3.extent(s, d => d.year)).range([m.l, W - m.r]);
  const y = d3.scaleLinear().domain([0, d3.max(s, d => d.value) * 1.1]).nice().range([H - m.b, m.t]);
  const svg = d3.create("svg").attr("viewBox", [0, 0, W, H]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).ticks(W < 500 ? 4 : 9).tickFormat(d3.format("d")).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(v => v + " %"))
    .call(g => g.select(".domain").remove()).call(g => g.selectAll(".tick line").attr("stroke", cssVar("--hairline")));
  const line = d3.line().x(d => x(d.year)).y(d => y(d.value));
  const actual = s.filter(d => !d.forecast);
  svg.append("path").datum(actual).attr("fill", "none").attr("stroke", cssVar("--series-1")).attr("stroke-width", 2).attr("d", line);
  svg.append("path").datum([actual[actual.length - 1], last]).attr("fill", "none").attr("stroke", cssVar("--series-1"))
    .attr("stroke-width", 2).attr("stroke-dasharray", "4 4").attr("d", line);
  svg.append("circle").attr("cx", x(last.year)).attr("cy", y(last.value)).attr("r", 5).attr("fill", cssVar("--series-1")).attr("stroke", cssVar("--surface-1")).attr("stroke-width", 2);
  svg.append("text").attr("x", x(last.year) - 8).attr("y", y(last.value) - 12).attr("text-anchor", "end").attr("font-size", 13).attr("font-weight", 650)
    .attr("fill", cssVar("--text-primary")).text(`${last.year}: ${nb1.format(last.value)} %`);
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
      showTip(ev, `<b>${d.year}</b>${d.forecast ? " (forslag)" : ""}<br>${nb1.format(d.value)} % av utgiftene`);
    })
    .on("mouseleave", () => { hover.style("display", "none"); hideTip(); });
  el.replaceChildren(svg.node());
}

// ---------- wiring ----------
function drawAll() {
  document.querySelectorAll(".treemap[data-nodes]").forEach(drawTreemap);
  document.querySelectorAll(".strip[data-kommuner]").forEach(drawStrip);
  document.querySelectorAll(".fund[data-fund]").forEach(drawFund);
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
  const btn = document.getElementById("theme");
  btn.textContent = isDark() ? "Lys" : "Mørk";
  btn.addEventListener("click", () => {
    document.documentElement.dataset.theme = isDark() ? "light" : "dark";
    localStorage.setItem("theme", document.documentElement.dataset.theme);
    btn.textContent = isDark() ? "Lys" : "Mørk";
    drawAll();
  });
  drawAll();
});
