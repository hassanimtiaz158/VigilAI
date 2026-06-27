import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../config";

const DOMAINS = [
  {
    value: "construction",
    icon: "\uD83C\uDFD7",
    label: "Construction",
    color: "#fb923c",
    rgb: "251,146,60",
    desc: "PPE compliance, zone violations, and worker safety near heavy machinery.",
    tags: ["Helmet", "Safety vest", "Zone breach"],
    critical: 3,
  },
  {
    value: "school",
    icon: "\uD83C\uDFEB",
    label: "School",
    color: "#60a5fa",
    rgb: "96,165,250",
    desc: "Weapon detection, unauthorized access, and crowd density monitoring on campus.",
    tags: ["Weapons", "Crowd", "Access"],
    critical: 1,
  },
  {
    value: "elderly",
    icon: "\uD83D\uDC74",
    label: "Elderly care",
    color: "#a78bfa",
    rgb: "167,139,250",
    desc: "Fall detection, prolonged stillness alerts, and wandering prevention for residents.",
    tags: ["Fall detect", "Stillness", "Wandering"],
    critical: 2,
  },
  {
    value: "child",
    icon: "\uD83D\uDC76",
    label: "Child safety",
    color: "#34d399",
    rgb: "52,211,153",
    desc: "Unattended child detection, restricted zone entry, and fall monitoring in care facilities.",
    tags: ["Unattended", "Zone entry", "Falls"],
    critical: 0,
  },
  {
    value: "public",
    icon: "\uD83C\uDF06",
    label: "Public space",
    color: "#fbbf24",
    rgb: "251,191,36",
    desc: "Unattended bag alerts, crowd anomaly detection, and loitering in transit hubs.",
    tags: ["Unattended bag", "Crowd", "Loitering"],
    critical: 1,
  },
];

export default function DomainSelectionPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const revealRefs = useRef([]);
  const domainsRef = useRef(null);
  const scrolledDown = useRef(false);

  useEffect(() => {
    const els = revealRefs.current.filter(Boolean);
    if (!els.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("revealed");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    function handleWheel(e) {
      if (scrolledDown.current) return;
      if (e.deltaY > 20) {
        scrolledDown.current = true;
        domainsRef.current?.scrollIntoView({ behavior: "smooth" });
      }
    }
    function handleScroll() {
      if (window.scrollY > 100) scrolledDown.current = true;
      setShowScrollTop(window.scrollY > 400);
    }
    window.addEventListener("wheel", handleWheel, { passive: true });
    window.addEventListener("scroll", handleScroll, { passive: true });

    if (window.location.hash === "#domains") {
      setTimeout(() => {
        domainsRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }

    return () => {
      window.removeEventListener("wheel", handleWheel);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  function scrollToDomains() {
    scrolledDown.current = true;
    domainsRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function addRevealRef(el) {
    if (el && !revealRefs.current.includes(el)) {
      revealRefs.current.push(el);
    }
  }

  async function handleSelect(domain) {
    if (loading) return;
    setSelected(domain);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/domain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      navigate("/dashboard", { state: { selectedDomain: domain } });
    } catch (err) {
      console.error("[VigilAI] domain switch failed", err);
      setError("Failed to connect to server. Is the backend running?");
      setLoading(false);
    }
  }

  function handleSelectAll() {
    handleSelect("construction");
  }

  function handleLaunch() {
    if (selected) handleSelect(selected);
  }

  const selectedDomain = DOMAINS.find((d) => d.value === selected);

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0 }
        body { background: #060d18; color: #e2eaf8; font-family: system-ui, -apple-system, sans-serif; min-height: 100vh }

        .nav { display: flex; align-items: center; justify-content: space-between; padding: 0 32px; height: 56px; border-bottom: 1px solid #182338 }
        .nav-brand { display: flex; align-items: center; gap: 10px }
        .nav-icon { width: 34px; height: 34px; border: 1px solid rgba(244,63,63,0.4); border-radius: 8px; display: flex; align-items: center; justify-content: center; background: rgba(244,63,63,0.08) }
        .shield-svg { width: 16px; height: 16px; fill: none; stroke: #f43f3f; stroke-width: 2; stroke-linejoin: round }
        .nav-name { font-size: 17px; font-weight: 700; letter-spacing: -0.5px }
        .nav-name em { color: #f43f3f; font-style: normal }
        .nav-right { display: flex; align-items: center; gap: 10px }
        .nav-pill { display: flex; align-items: center; gap: 5px; background: rgba(244,63,63,0.1); border: 1px solid rgba(244,63,63,0.3); border-radius: 20px; padding: 4px 12px; font-size: 11px; font-weight: 700; color: #f43f3f; letter-spacing: 1px }
        .pulse { width: 6px; height: 6px; border-radius: 50%; background: #f43f3f; animation: p 1.4s infinite }
        @keyframes p { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.65)} }
        .nav-ver { font-size: 11px; color: #4a607a }

        .hero { text-align: center; padding: 52px 32px 40px }
        .hero-tag { display: inline-flex; align-items: center; gap: 6px; background: rgba(96,165,250,0.08); border: 1px solid rgba(96,165,250,0.2); border-radius: 20px; padding: 5px 14px; font-size: 11px; font-weight: 600; color: #60a5fa; letter-spacing: .5px; margin-bottom: 20px }
        .hero h1 { font-size: 42px; font-weight: 800; letter-spacing: -1.5px; line-height: 1.1; margin-bottom: 14px }
        .hero h1 span { color: #f43f3f }
        .hero p { font-size: 15px; color: #8aa0c0; max-width: 480px; margin: 0 auto 32px; line-height: 1.6 }
        .hero-stats { display: flex; align-items: center; justify-content: center; gap: 32px }
        .h-stat { text-align: center }
        .h-stat-val { font-size: 22px; font-weight: 700 }
        .h-stat-lbl { font-size: 10px; color: #4a607a; text-transform: uppercase; letter-spacing: .7px; margin-top: 3px }
        .hero-div { width: 1px; height: 32px; background: #182338 }

        .section-lbl { text-align: center; margin: 0 0 20px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #4a607a; font-weight: 600 }

        .domains { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; padding: 0 24px; max-width: 960px; margin: 0 auto }
        .d-card { background: #0c1526; border: 1px solid #182338; border-radius: 12px; padding: 22px 20px; cursor: pointer; transition: all .18s; position: relative; overflow: hidden }
        .d-card:hover { border-color: var(--ac); transform: translateY(-2px) }
        .d-card.selected { border-color: var(--ac); background: rgba(var(--acr),0.06) }
        .d-card-top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 14px }
        .d-icon-wrap { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; background: rgba(var(--acr),0.1); border: 1px solid rgba(var(--acr),0.2) }
        .d-check { width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid #182338; display: flex; align-items: center; justify-content: center; transition: all .15s; flex-shrink: 0 }
        .d-card.selected .d-check { background: var(--ac); border-color: var(--ac) }
        .d-check svg { width: 10px; height: 10px; fill: none; stroke: #060d18; stroke-width: 2.5; opacity: 0; transition: opacity .15s }
        .d-card.selected .d-check svg { opacity: 1 }
        .d-name { font-size: 14px; font-weight: 700; color: #e2eaf8; margin-bottom: 5px }
        .d-desc { font-size: 11px; color: #6a80a0; line-height: 1.5; margin-bottom: 14px }
        .d-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 14px }
        .d-tag { font-size: 9px; font-weight: 600; letter-spacing: .4px; padding: 2px 7px; border-radius: 10px; background: rgba(var(--acr),0.1); color: var(--ac); border: 1px solid rgba(var(--acr),0.2) }
        .d-footer { display: flex; align-items: center; justify-content: space-between }
        .d-alert-count { font-size: 10px; color: #4a607a }
        .d-alert-count b { color: var(--ac) }
        .d-select-btn { font-size: 10px; font-weight: 700; color: var(--ac); letter-spacing: .3px; padding: 4px 10px; border: 1px solid rgba(var(--acr),0.3); border-radius: 6px; background: transparent; cursor: pointer; transition: all .15s }
        .d-select-btn:hover { background: rgba(var(--acr),0.1) }
        .d-critical-bar { position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--ac); opacity: 0; transition: opacity .2s }
        .d-card.has-critical .d-critical-bar { opacity: 1; animation: crit 2s ease-in-out infinite }
        @keyframes crit { 0%,100%{opacity:.6} 50%{opacity:1} }

        .all-btn-wrap { padding: 20px 24px 0; max-width: 960px; margin: 0 auto }
        .all-btn { width: 100%; padding: 14px; border-radius: 10px; border: 1px solid rgba(96,165,250,0.3); background: rgba(96,165,250,0.06); color: #60a5fa; font-size: 13px; font-weight: 700; letter-spacing: .3px; cursor: pointer; transition: all .15s; display: flex; align-items: center; justify-content: center; gap: 8px }
        .all-btn:hover { background: rgba(96,165,250,0.12); border-color: rgba(96,165,250,0.5) }

        .launch-wrap { padding: 20px 24px 0; max-width: 960px; margin: 0 auto }
        .launch-btn { width: 100%; padding: 16px; border-radius: 10px; background: #f43f3f; border: none; color: #fff; font-size: 14px; font-weight: 800; letter-spacing: .3px; cursor: pointer; transition: all .15s; display: flex; align-items: center; justify-content: center; gap: 8px; opacity: .35; pointer-events: none }
        .launch-btn.ready { opacity: 1; pointer-events: all }
        .launch-btn.ready:hover { background: #e53535; transform: translateY(-1px) }
        .launch-hint { text-align: center; margin-top: 10px; font-size: 11px; color: #4a607a }

        .loading-overlay { display: none; position: fixed; inset: 0; background: #060d18; flex-direction: column; align-items: center; justify-content: center; gap: 20px; z-index: 999 }
        .loading-overlay.active { display: flex }
        .loading-ring { width: 40px; height: 40px; border: 2px solid #182338; border-top-color: #f43f3f; border-radius: 50%; animation: spin .8s linear infinite }
        @keyframes spin { to { transform: rotate(360deg) } }
        .loading-text { font-size: 13px; color: #8aa0c0 }
        .loading-domain { color: #e2eaf8; font-weight: 700 }

        .footer-bar { margin-top: 40px; padding: 16px 32px; border-top: 1px solid #182338; display: flex; align-items: center; justify-content: space-between }
        .footer-txt { font-size: 11px; color: #4a607a }
        .footer-model { font-size: 11px; color: #4a607a; display: flex; align-items: center; gap: 6px }
        .footer-dot { width: 5px; height: 5px; border-radius: 50%; background: #34d399 }

        .sr { opacity: 0; transform: translateY(18px); transition: opacity .5s ease, transform .5s ease }
        .sr.revealed { opacity: 1; transform: translateY(0) }
        .sr-d1 { transition-delay: .08s }
        .sr-d2 { transition-delay: .16s }
        .sr-d3 { transition-delay: .24s }
        .sr-d4 { transition-delay: .32s }
        .sr-d5 { transition-delay: .40s }

        .scroll-arrow { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-top: 36px; cursor: pointer; color: #4a607a; animation: bob 2s ease-in-out infinite }
        .scroll-arrow span { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600 }
        @keyframes bob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(6px)} }

        .scroll-top { position: fixed; bottom: 28px; right: 28px; width: 40px; height: 40px; border-radius: 10px; background: #0c1526; border: 1px solid #182338; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #8aa0c0; z-index: 50; opacity: 0; transform: translateY(10px); transition: all .25s ease; pointer-events: none }
        .scroll-top.visible { opacity: 1; transform: translateY(0); pointer-events: all }
        .scroll-top:hover { border-color: #60a5fa; color: #60a5fa }
      `}</style>

      {/* Nav */}
      <nav className="nav">
        <div className="nav-brand">
          <div className="nav-icon">
            <svg className="shield-svg" viewBox="0 0 24 24"><path d="M12 3L4 7v5c0 4.5 3.3 8.7 8 9.9C17.7 20.7 21 16.5 21 12V7z" /></svg>
          </div>
          <span className="nav-name">Vigil<em>AI</em></span>
        </div>
        <div className="nav-right">
          <div className="nav-pill"><div className="pulse"></div>SYSTEM READY</div>
          <span className="nav-ver">v2.1.0</span>
        </div>
      </nav>

      {/* Hero */}
      <div className="hero">
        <div ref={addRevealRef} className="hero-tag sr">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2"><path d="M12 3L4 7v5c0 4.5 3.3 8.7 8 9.9C17.7 20.7 21 16.5 21 12V7z" /></svg>
          AI-powered safety monitoring
        </div>
        <h1 ref={addRevealRef} className="sr sr-d1">The safety camera<br/>that <span>understands</span></h1>
        <p ref={addRevealRef} className="sr sr-d2">Select your monitoring domain to activate context-aware AI detection, real-time incident reasoning, and intelligent alerts.</p>
        <div ref={addRevealRef} className="hero-stats sr sr-d3">
          <div className="h-stat"><div className="h-stat-val" style={{ color: "#f43f3f" }}>3</div><div className="h-stat-lbl">Active threats</div></div>
          <div className="hero-div"></div>
          <div className="h-stat"><div className="h-stat-val" style={{ color: "#34d399" }}>1.6s</div><div className="h-stat-lbl">Avg response</div></div>
          <div className="hero-div"></div>
          <div className="h-stat"><div className="h-stat-val" style={{ color: "#60a5fa" }}>5</div><div className="h-stat-lbl">Domains live</div></div>
          <div className="hero-div"></div>
          <div className="h-stat"><div className="h-stat-val" style={{ color: "#a78bfa" }}>-31%</div><div className="h-stat-lbl">False positives</div></div>
        </div>
        <div className="scroll-arrow" onClick={scrollToDomains}>
          <span>Scroll down</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 13l5 5 5-5"/><path d="M7 6l5 5 5-5"/></svg>
        </div>
      </div>

      {/* Section label */}
      <div ref={addRevealRef} className="section-lbl sr">Choose monitoring domain</div>

      {/* Domain cards */}
      <div ref={domainsRef} className="domains">
        {DOMAINS.map((d, i) => {
          const isSelected = selected === d.value;
          return (
            <div
              key={d.value}
              ref={addRevealRef}
              className={`d-card sr sr-d${Math.min(i + 1, 5)}${isSelected ? " selected" : ""}${d.critical > 0 ? " has-critical" : ""}`}
              style={{ "--ac": d.color, "--acr": d.rgb }}
              onClick={() => handleSelect(d.value)}
            >
              <div className="d-critical-bar"></div>
              <div className="d-card-top">
                <div className="d-icon-wrap">{d.icon}</div>
                <div className="d-check">
                  <svg viewBox="0 0 12 10"><polyline points="1,5 4,8 11,1" /></svg>
                </div>
              </div>
              <div className="d-name">{d.label}</div>
              <div className="d-desc">{d.desc}</div>
              <div className="d-tags">
                {d.tags.map((t) => (
                  <span key={t} className="d-tag">{t}</span>
                ))}
              </div>
              <div className="d-footer">
                <span className="d-alert-count"><b>{d.critical} critical</b> active</span>
                <button className="d-select-btn">Select</button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Monitor All */}
      <div ref={addRevealRef} className="all-btn-wrap sr sr-d3">
        <button className="all-btn" onClick={handleSelectAll}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>
          Monitor all domains simultaneously
        </button>
      </div>

      {/* Launch */}
      <div ref={addRevealRef} className="launch-wrap sr sr-d4">
        <button className={`launch-btn${selected ? " ready" : ""}`} onClick={handleLaunch}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5"><polygon points="5,3 19,12 5,21" /></svg>
          {selected ? `Launch ${selectedDomain?.label || "monitoring"}` : "Select a domain to continue"}
        </button>
        <div className="launch-hint">
          {selected ? `${selectedDomain?.icon} ${selectedDomain?.label} domain selected` : "Choose one domain above or monitor all"}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          maxWidth: 960, margin: "16px auto 0", padding: "10px 20px",
          background: "rgba(244,63,63,0.08)", border: "1px solid rgba(244,63,63,0.25)",
          borderRadius: 8, fontSize: 12, color: "#f87171", textAlign: "center",
        }}>
          {error}
        </div>
      )}

      {/* Footer */}
      <div ref={addRevealRef} className="footer-bar sr sr-d5">
        <span className="footer-txt">VigilAI · FutureHacks 2026 · Built by Hasan Ali</span>
        <div className="footer-model"><div className="footer-dot"></div>LLaMA 3.3 70B · YOLOv8n · MediaPipe · Groq</div>
      </div>

      {/* Scroll to top */}
      <button className={`scroll-top${showScrollTop ? " visible" : ""}`} onClick={scrollToTop}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 13l5-5 5 5"/><path d="M7 6l5-5 5 5"/></svg>
      </button>

      {/* Loading overlay */}
      <div className={`loading-overlay${loading ? " active" : ""}`}>
        <div className="nav-icon" style={{ width: 48, height: 48, borderRadius: 12 }}>
          <svg className="shield-svg" viewBox="0 0 24 24" style={{ width: 22, height: 22 }}><path d="M12 3L4 7v5c0 4.5 3.3 8.7 8 9.9C17.7 20.7 21 16.5 21 12V7z" /></svg>
        </div>
        <div className="loading-ring"></div>
        <div className="loading-text">Initializing <span className="loading-domain">{selectedDomain?.label || ""}</span> monitoring...</div>
        <div style={{ fontSize: 11, color: "#4a607a", marginTop: 4 }}>Loading YOLOv8 · Groq LLaMA 3.3 · WebSocket</div>
      </div>
    </>
  );
}
