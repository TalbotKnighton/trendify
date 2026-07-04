"use strict";
(() => {
  var g = "trendify:theme";
  function K() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function P() {
    let e = localStorage.getItem(g);
    return e === "light" || e === "dark" ? e : "system";
  }
  function U(e) {
    let t = e === "dark" || (e === "system" && K());
    document.documentElement.classList.toggle("dark", t);
  }
  function _(e) {
    (e === "system" ? localStorage.removeItem(g) : localStorage.setItem(g, e),
      U(e));
  }
  function w() {
    return {
      theme: P(),
      setTheme(e) {
        ((this.theme = e), _(e));
      },
    };
  }
  function b() {
    return {
      isFullscreen: !1,
      init() {
        document.addEventListener("fullscreenchange", () => {
          ((this.isFullscreen = document.fullscreenElement !== null),
            window.dispatchEvent(new Event("trendify:layout-changed")));
        });
      },
      toggle() {
        document.fullscreenElement
          ? document.exitFullscreen()
          : document.documentElement.requestFullscreen();
      },
    };
  }
  function T({
    storageKey: e,
    elementId: t,
    defaultWidth: n,
    minWidth: o,
    maxWidth: r,
  }) {
    let a = Number(localStorage.getItem(e));
    return {
      width: Number.isFinite(a) && a > 0 ? a : n,
      dragging: !1,
      startDrag(i) {
        (i.preventDefault(), (this.dragging = !0));
        let s = i.clientX,
          c = this.width,
          d = (p) => {
            let O = c + (p.clientX - s);
            this.width = Math.min(r, Math.max(o, O));
          },
          u = () => {
            ((this.dragging = !1),
              localStorage.setItem(e, String(this.width)),
              window.removeEventListener("mousemove", d),
              window.removeEventListener("mouseup", u));
          };
        (window.addEventListener("mousemove", d),
          window.addEventListener("mouseup", u));
      },
      fitToContent() {
        let i = document.getElementById(t);
        if (!i) return;
        let s = i.style.width;
        i.style.width = "max-content";
        let c = i.scrollWidth;
        ((i.style.width = s),
          (this.width = Math.min(r, Math.max(o, c))),
          localStorage.setItem(e, String(this.width)));
      },
    };
  }
  var D = 1;
  function v() {
    return {
      toasts: [],
      push(e, t = "info", n = 4e3) {
        let o = D++;
        (this.toasts.push({
          id: o,
          message: e,
          kind: t,
          timestamp: Date.now(),
          read: !1,
          visible: !0,
        }),
          n > 0 &&
            setTimeout(() => {
              let r = this.toasts.find((a) => a.id === o);
              r && (r.visible = !1);
            }, n));
      },
      dismiss(e) {
        let t = this.toasts.find((n) => n.id === e);
        t && (t.visible = !1);
      },
      clearAll() {
        this.toasts = [];
      },
      markAllRead() {
        this.toasts.forEach((e) => {
          e.read = !0;
        });
      },
      get unreadCount() {
        return this.toasts.filter((e) => !e.read).length;
      },
      timeAgo(e) {
        let t = Math.floor((Date.now() - e) / 1e3);
        if (t < 5) return "just now";
        if (t < 60) return `${t}s ago`;
        let n = Math.floor(t / 60);
        return n < 60 ? `${n}m ago` : `${Math.floor(n / 60)}h ago`;
      },
    };
  }
  function y({
    pingUrl: e,
    intervalMs: t,
    timeoutMs: n,
    onConnectionChange: o,
    onDbChanged: r,
  }) {
    let a = !0,
      l = null;
    async function i() {
      let c = new AbortController(),
        d = setTimeout(() => c.abort(), n);
      try {
        let u = await fetch(e, { signal: c.signal, cache: "no-store" });
        if (!u.ok) throw new Error(`ping failed: ${u.status}`);
        let p = await u.json();
        (a || ((a = !0), o(!0)),
          p.db_updated_at !== null &&
            (l !== null && p.db_updated_at !== l && r(),
            (l = p.db_updated_at)));
      } catch {
        a && ((a = !1), o(!1));
      } finally {
        clearTimeout(d);
      }
    }
    let s = setInterval(i, t);
    return (i(), () => clearInterval(s));
  }
  async function S(e) {
    if (navigator.clipboard?.writeText)
      try {
        return (await navigator.clipboard.writeText(e), !0);
      } catch {}
    try {
      let t = document.createElement("textarea");
      ((t.value = e),
        (t.style.position = "fixed"),
        (t.style.opacity = "0"),
        document.body.appendChild(t),
        t.focus(),
        t.select());
      let n = document.execCommand("copy");
      return (document.body.removeChild(t), n);
    } catch {
      return !1;
    }
  }
  var f = new Map();
  async function F(e) {
    let t = f.get(e);
    if (t !== void 0) return t;
    let n = await fetch(e);
    if (!n.ok) throw new Error(`Request failed: ${e} (${n.status})`);
    let o = await n.json();
    return (f.set(e, o), o);
  }
  function x(e, t) {
    let n = `/api/table?tag=${encodeURIComponent(JSON.stringify(e))}&view=${t}`;
    return F(n);
  }
  window.addEventListener("trendify:db-changed", () => f.clear());
  var E = "tag",
    C = "kinds",
    M = "view",
    W = ["melted", "pivot", "stats"];
  function V() {
    let e = new URLSearchParams(window.location.search),
      t = e.get(E);
    if (!t) return null;
    try {
      let n = JSON.parse(t),
        o = e.get(C),
        r = o ? o.split(",") : [];
      return { tag: n, recordKinds: r };
    } catch {
      return null;
    }
  }
  function A(e, t) {
    let n = new URLSearchParams(window.location.search);
    (n.set(E, JSON.stringify(e)), n.set(C, t.join(",")));
    let o = `${window.location.pathname}?${n.toString()}`;
    window.history.replaceState(null, "", o);
  }
  function L() {
    let e = new URLSearchParams(window.location.search).get(M);
    return W.includes(e ?? "") ? e : null;
  }
  function N(e) {
    let t = new URLSearchParams(window.location.search);
    t.set(M, e);
    let n = `${window.location.pathname}?${t.toString()}`;
    window.history.replaceState(null, "", n);
  }
  function m(e) {
    let t = localStorage.getItem(e);
    if (t === null) return null;
    try {
      return JSON.parse(t);
    } catch {
      return null;
    }
  }
  function h(e, t) {
    localStorage.setItem(e, JSON.stringify(t));
  }
  var J = 60,
    R = "trendify:table-page-length",
    H = 10;
  function z(e, t) {
    return `trendify:table-filters:${JSON.stringify(e)}:${t}`;
  }
  function q(e) {
    e.querySelectorAll("thead th").forEach((n) => {
      n.style.position = "relative";
      let o = document.createElement("span");
      ((o.className = "dt-col-resize-handle"),
        o.addEventListener("mousedown", (r) => {
          (r.preventDefault(), r.stopPropagation());
          let a = r.clientX,
            l = n.offsetWidth,
            i = (c) => {
              let d = Math.max(J, l + (c.clientX - a));
              n.style.width = `${d}px`;
            },
            s = () => {
              (window.removeEventListener("mousemove", i),
                window.removeEventListener("mouseup", s));
            };
          (window.addEventListener("mousemove", i),
            window.addEventListener("mouseup", s));
        }),
        n.appendChild(o));
    });
  }
  function G(e) {
    let t = m(e) ?? {},
      n = this;
    (n.columns().every(function () {
      let o = this,
        r = String(o.dataSrc()),
        a = t[r] ?? "",
        l = $(o.header());
      ($("<input>")
        .attr("type", "text")
        .attr("placeholder", "Filter")
        .addClass("dt-column-filter")
        .val(a)
        .on("click", (i) => i.stopPropagation())
        .on("keyup change clear", function () {
          let i = this.value;
          o.search() !== i && o.search(i).draw();
          let s = m(e) ?? {};
          (i ? (s[r] = i) : delete s[r], h(e, s));
        })
        .appendTo(l),
        a && o.search(a));
    }),
      n.draw());
  }
  function I() {
    return {
      view: "stats",
      unavailable: !1,
      requestId: 0,
      setView(e) {
        ((this.view = e), N(e));
      },
      init() {
        let e = L();
        (e && (this.view = e),
          this.$watch("view", () => this.render()),
          this.$watch("selectedTag", () => this.setView("stats")),
          this.render());
      },
      async render() {
        let e = this.selectedTag;
        if (e === null) return;
        let t = ++this.requestId,
          n = await x(e, this.view);
        if (t !== this.requestId) return;
        let o = this.$refs.table;
        if (
          ($.fn.DataTable.isDataTable(o) &&
            ($(o).DataTable().destroy(), (o.innerHTML = "")),
          (this.unavailable = !n.available),
          !n.available)
        )
          return;
        let r = z(e, this.view);
        $(o)
          .DataTable({
            data: n.rows,
            columns: n.columns.map((l) => ({ data: l, title: l })),
            autoWidth: !1,
            pageLength: m(R) ?? H,
            initComplete: function () {
              (G.call(this.api(), r), q(o));
            },
          })
          .on("length", (l, i, s) => {
            h(R, s);
          });
      },
    };
  }
  function X(e) {
    return `trendify:folder-open:${JSON.stringify(e)}`;
  }
  function j(e) {
    return e === null ? [] : Array.isArray(e) ? e.map(String) : [String(e)];
  }
  function k(e) {
    let t = X(e);
    return {
      open: !1,
      autoExpanded: !1,
      init() {
        let n = m(t);
        if (n !== null) {
          this.open = n;
          return;
        }
        let o = j(this.selectedTag);
        this.open = o.length > e.length && e.every((r, a) => r === o[a]);
      },
      toggle() {
        ((this.open = !this.open), h(t, this.open));
      },
    };
  }
  function B(e) {
    return Array.isArray(e) ? e.join(" / ") : String(e);
  }
  document.addEventListener("alpine:init", () => {
    (Alpine.data("themeSelector", w),
      Alpine.data("fullscreenToggle", b),
      Alpine.data("tableView", I),
      Alpine.data("sidebarNode", k),
      Alpine.data("appShell", () => ({
        sidebarOpen: !0,
        selectedTag: null,
        selectedRecordKinds: [],
        toggleSidebar() {
          this.sidebarOpen = !this.sidebarOpen;
        },
        ...T({
          storageKey: "trendify:sidebar-width",
          elementId: "sidebar-panel",
          defaultWidth: 288,
          minWidth: 200,
          maxWidth: 600,
        }),
        ...v(),
        connected: !0,
        init() {
          let e = V();
          (e &&
            ((this.selectedTag = e.tag),
            (this.selectedRecordKinds = e.recordKinds)),
            y({
              pingUrl: "/api/ping",
              intervalMs: 5e3,
              timeoutMs: 3e3,
              onConnectionChange: (t) => {
                ((this.connected = t),
                  this.push(
                    t ? "Reconnected to server" : "Lost connection to server",
                    t ? "success" : "error",
                  ));
              },
              onDbChanged: () => {
                (this.push("Database updated with new data", "info"),
                  window.dispatchEvent(new CustomEvent("trendify:db-changed")));
              },
            }));
        },
        onTagSelected(e) {
          ((this.selectedTag = e.tag),
            (this.selectedRecordKinds = e.recordKinds),
            A(e.tag, e.recordKinds),
            this.push(`Viewing ${B(e.tag)}`, "info", 2e3));
        },
        async copyDbPath(e) {
          let t = await S(e);
          this.push(
            t
              ? "Copied database path to clipboard"
              : "Could not copy to clipboard",
            t ? "success" : "error",
            2e3,
          );
        },
      })));
  });
})();
//# sourceMappingURL=main.js.map
