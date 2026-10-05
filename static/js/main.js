(function () {
  "use strict";
  document.documentElement.classList.remove("no-js");
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Header: transparent over hero, solid after scroll
  var header = $(".site-header");
  function onScroll() { if (header) header.classList.toggle("is-solid", window.scrollY > 40); }
  onScroll(); window.addEventListener("scroll", onScroll, { passive: true });

  // Mobile menu
  var toggle = $(".menu-toggle");
  if (toggle) toggle.addEventListener("click", function () {
    var open = document.body.classList.toggle("menu-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  $$(".main-nav a").forEach(function (a) {
    a.addEventListener("click", function () { document.body.classList.remove("menu-open"); });
  });

  // Reveal on scroll
  var reveals = $$(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else { reveals.forEach(function (el) { el.classList.add("is-in"); }); }

  // Tabs (contact page)
  $$("[data-tabs]").forEach(function (wrap) {
    var tabs = $$("[data-tab]", wrap), panels = $$("[data-panel]", wrap);
    function show(name) {
      tabs.forEach(function (t) { t.classList.toggle("is-active", t.dataset.tab === name); });
      panels.forEach(function (p) { p.hidden = p.dataset.panel !== name; });
    }
    tabs.forEach(function (t) { t.addEventListener("click", function () { show(t.dataset.tab); history.replaceState(null, "", "#" + t.dataset.tab); }); });
    var h = location.hash.replace("#", "");
    if (h && tabs.some(function (t) { return t.dataset.tab === h; })) show(h);
  });

  // Jump between contact tabs from inside a panel
  $$("[data-goto-tab]").forEach(function (b) {
    b.addEventListener("click", function () {
      var t = $('.tab[data-tab="' + b.dataset.gotoTab + '"]'); if (t) t.click();
      if (b.dataset.fill) { var f = document.getElementById(b.dataset.fill); if (f) { f.value = b.dataset.value; f.focus(); } }
    });
  });

  // Works index on the homepage: hover / focus swaps the preview image
  $$("[data-works-index]").forEach(function (wrap) {
    var links = $$("[data-img]", wrap);
    function show(l) {
      links.forEach(function (x) { x.classList.toggle("is-on", x === l); });
      $$(".wi-img img", wrap).forEach(function (i) { i.classList.toggle("is-on", i.id === l.dataset.img); });
    }
    links.forEach(function (l) { ["mouseenter", "focus"].forEach(function (ev) { l.addEventListener(ev, function () { show(l); }); }); });
  });

  // Gallery filter
  $$("[data-filter-group]").forEach(function (group) {
    var btns = $$("[data-filter]", group), items = $$("[data-cat]", group.parentNode);
    function apply(slug) {
      btns.forEach(function (b) { var on = b.dataset.filter === slug; b.classList.toggle("is-active", on); b.setAttribute("aria-pressed", String(on)); });
      items.forEach(function (it) { it.classList.toggle("is-hidden", slug !== "all" && it.dataset.cat !== slug); });
      var empty = $("[data-filter-empty]", group.parentNode);
      if (empty) empty.hidden = items.some(function (it) { return !it.classList.contains("is-hidden"); });
    }
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        apply(b.dataset.filter);
        history.replaceState(null, "", b.dataset.filter === "all" ? location.pathname : "?category=" + encodeURIComponent(b.dataset.filter));
      });
    });
    var q = new URLSearchParams(location.search).get("category");
    if (q && btns.some(function (b) { return b.dataset.filter === q; })) apply(q);
  });

  // Lightbox
  var lb, lbMedia, lbCap, lbCount, current = [], idx = 0;
  function build() {
    lb = document.createElement("div"); lb.className = "lb"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-modal", "true");
    lb.innerHTML = '<span class="lb__count"></span><button class="lb__btn lb__close" aria-label="بستن">×</button>' +
      '<button class="lb__btn lb__prev" aria-label="بعدی">›</button><button class="lb__btn lb__next" aria-label="قبلی">‹</button>' +
      '<div class="lb__media"></div><p class="lb__cap"></p>';
    document.body.appendChild(lb);
    lbMedia = $(".lb__media", lb); lbCap = $(".lb__cap", lb); lbCount = $(".lb__count", lb);
    $(".lb__close", lb).onclick = close; $(".lb__prev", lb).onclick = function () { step(1); }; $(".lb__next", lb).onclick = function () { step(-1); };
    lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
  }
  function render() {
    var el = current[idx], href = el.getAttribute("href"), isVideo = el.dataset.type === "video";
    lbMedia.innerHTML = "";
    var m = document.createElement(isVideo ? "video" : "img");
    if (isVideo) { m.src = href; m.controls = true; m.autoplay = true; } else { m.src = href; m.alt = el.dataset.alt || ""; }
    lbMedia.appendChild(m);
    lbCap.textContent = el.dataset.caption || "";
    lbCount.textContent = (idx + 1) + " / " + current.length;
  }
  var opener = null;
  function open(list, i) { if (!lb) build(); opener = document.activeElement; current = list; idx = i; render(); lb.classList.add("is-open"); document.body.style.overflow = "hidden"; $(".lb__close", lb).focus(); }
  function close() { lb.classList.remove("is-open"); lbMedia.innerHTML = ""; document.body.style.overflow = ""; if (opener) opener.focus(); }
  function step(d) { idx = (idx + d + current.length) % current.length; render(); }
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a[data-lightbox]"); if (!a) return;
    e.preventDefault();
    var g = a.dataset.lightbox;
    var list = $$('a[data-lightbox="' + g + '"]').filter(function (x) { return !x.classList.contains("is-hidden") && x.offsetParent !== null; });
    open(list, Math.max(0, list.indexOf(a)));
  });
  document.addEventListener("keydown", function (e) {
    if (!lb || !lb.classList.contains("is-open")) return;
    if (e.key === "Tab") { var f = $$("button", lb); var first = f[0], last = f[f.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); } }
    if (e.key === "Escape") close(); if (e.key === "ArrowLeft") step(1); if (e.key === "ArrowRight") step(-1);
  });
  var sx = null;
  document.addEventListener("touchstart", function (e) { if (lb && lb.classList.contains("is-open")) sx = e.touches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", function (e) {
    if (sx === null) return; var dx = e.changedTouches[0].clientX - sx; sx = null;
    if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1);
  });

  // Article TOC highlight
  var toc = $$(".toc a");
  if (toc.length && "IntersectionObserver" in window) {
    var map = {}; toc.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var so = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { toc.forEach(function (a) { a.classList.remove("is-active"); }); var a = map[e.target.id]; if (a) a.classList.add("is-active"); } });
    }, { rootMargin: "-20% 0px -70% 0px" });
    $$(".article-body h2").forEach(function (h) { if (h.id) so.observe(h); });
  }
})();
