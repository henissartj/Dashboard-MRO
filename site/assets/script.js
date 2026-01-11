const state = {
  filter: "all",
  query: "",
  catFilter: "all",
  commands: []
};

const elCount = document.getElementById("cmdCount");
const elGrid = document.getElementById("cmdGrid");
const elSearch = document.getElementById("cmdSearch");
const catSelect = document.getElementById("catSelect");

const tabAll = document.getElementById("tabAll");
const tabPrefix = document.getElementById("tabPrefix");
const tabSlash = document.getElementById("tabSlash");

function setTab(filter) {
  state.filter = filter;
  tabAll.setAttribute("aria-pressed", filter === "all");
  tabPrefix.setAttribute("aria-pressed", filter === "prefix");
  tabSlash.setAttribute("aria-pressed", filter === "slash");
  render();
}

tabAll.addEventListener("click", () => setTab("all"));
tabPrefix.addEventListener("click", () => setTab("prefix"));
tabSlash.addEventListener("click", () => setTab("slash"));

elSearch.addEventListener("input", (e) => {
  state.query = (e.target.value || "").trim().toLowerCase();
  render();
});

if (catSelect) {
  catSelect.addEventListener("change", (e) => {
    state.catFilter = e.target.value;
    render();
  });
}

function matches(cmd) {
  if (state.filter !== "all" && cmd.type !== state.filter) return false;
  if (state.catFilter !== "all" && (cmd.category || "Autre") !== state.catFilter) return false;
  if (!state.query) return true;
  const hay = [
    cmd.name,
    cmd.type,
    cmd.description || "",
    ...(cmd.aliases || [])
  ].join(" ").toLowerCase();
  return hay.includes(state.query);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function render() {
  const items = state.commands.filter(matches);
  elCount.textContent = `${items.length} commande(s) affichée(s) • ${state.commands.length} au total`;

  if (!items.length) {
    elGrid.innerHTML = `<div class="cmd" style="grid-column:1/-1"><div class="cmd-top"><div class="cmd-name">Rien trouvé</div><div class="cmd-kind">Essaie un autre mot</div></div><div class="cmd-desc">Le quartier a fouillé partout, y’a rien.</div></div>`;
    return;
  }

  // Group by category
  const groups = {};
  items.forEach(cmd => {
      const cat = cmd.category || "Autre";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(cmd);
  });

  const sortedCats = Object.keys(groups).sort((a, b) => {
       if (a === "Général") return -1;
       if (b === "Général") return 1;
       return a.localeCompare(b);
  });

  let html = "";
  sortedCats.forEach(cat => {
      html += `<h3 class="category-header">${escapeHtml(cat)}</h3>`;
      html += groups[cat].map(cmd => {
          const aliases = (cmd.aliases || []).slice(0, 12);
          const aliasHtml = aliases.length
            ? `<div class="cmd-aliases">${aliases.map(a => `<span class="chip">${escapeHtml(a)}</span>`).join("")}</div>`
            : "";
          const desc = cmd.description ? escapeHtml(cmd.description) : "—";
          const kind = cmd.type === "slash" ? "slash" : "préfixe";
          
          const displayName = cmd.type === "slash" ? "/" + cmd.name : "+" + cmd.name;
          const usageHtml = cmd.usage ? `<div class="cmd-usage">${escapeHtml(cmd.usage)}</div>` : "";

          return `
            <div class="cmd">
              <div class="cmd-top">
                <div class="cmd-name">${escapeHtml(displayName)}</div>
                <div class="cmd-kind">${kind}</div>
              </div>
              <div class="cmd-desc">${desc}</div>
              ${usageHtml}
              ${aliasHtml}
            </div>
          `;
      }).join("");
  });
  
  elGrid.innerHTML = html;
  
  // Scroll Reveal & Click Copy
  const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
          if (entry.isIntersecting) {
              entry.target.classList.add('active');
              observer.unobserve(entry.target);
          }
      });
  }, { threshold: 0.1 });

  document.querySelectorAll('.cmd').forEach(el => {
      el.classList.add('reveal');
      observer.observe(el);
      
      el.addEventListener('click', () => {
          const nameEl = el.querySelector('.cmd-name');
          let text = nameEl.innerText;
          // text already contains + or /
          
          navigator.clipboard.writeText(text).then(() => {
              showToast(`Commande copiée : ${text}`);
          });
      });
  });
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "show";
  setTimeout(() => { t.className = t.className.replace("show", ""); }, 3000);
}

async function initCommands() {
  // Skeleton
  elGrid.innerHTML = Array(6).fill(0).map(() => `
    <div class="cmd" style="cursor:default">
      <div class="cmd-top">
        <div class="cmd-name" style="width:100px;height:20px;background:rgba(255,255,255,0.1);border-radius:4px"></div>
        <div class="cmd-kind" style="width:40px;height:12px;background:rgba(255,255,255,0.1);border-radius:4px"></div>
      </div>
      <div class="cmd-desc" style="margin-top:10px;height:14px;background:rgba(255,255,255,0.1);border-radius:4px;width:80%"></div>
    </div>
  `).join("");

  try {
    const resp = await fetch("/api/commands", { cache: "no-store" });
    if (!resp.ok) throw new Error("bad_status");
    const data = await resp.json();
    state.commands = Array.isArray(data.commands) ? data.commands : [];
    
    // Populate categories
    if (catSelect) {
      const cats = new Set(state.commands.map(c => c.category || "Autre"));
      const sorted = [...cats].sort();
      // Reset options but keep "All"
      catSelect.innerHTML = '<option value="all">Toutes les catégories</option>';
      sorted.forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat;
        catSelect.appendChild(opt);
      });
    }
    
    render();
  } catch (e) {
    elCount.textContent = "Impossible de charger les commandes.";
    elGrid.innerHTML = `<div class="cmd"><div class="cmd-top"><div class="cmd-name">Erreur</div><div class="cmd-kind">API</div></div><div class="cmd-desc">Le serveur a refusé de parler. Recharge la page.</div></div>`;
  }
}

async function fetchStats() {
  try {
      const r = await fetch("/api/stats");
      const d = await r.json();
      animateValue("statUsers", 0, d.users, 2000);
      animateValue("statMoney", 0, d.money, 2000);
      animateValue("statServers", 0, d.servers || 0, 2000);
  } catch(e) {}
}

function animateValue(id, start, end, duration) {
  const obj = document.getElementById(id);
  if (!obj) return;
  let startTimestamp = null;
  const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const val = Math.floor(progress * (end - start) + start);
      obj.textContent = val.toLocaleString();
      if (progress < 1) {
          window.requestAnimationFrame(step);
      }
  };
  window.requestAnimationFrame(step);
}

const btnTop = document.getElementById("backToTop");
if (btnTop) {
    window.addEventListener("scroll", () => {
        if (window.scrollY > 300) btnTop.classList.add("visible");
        else btnTop.classList.remove("visible");
    });
    btnTop.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    initCommands();
    fetchStats();
    // initLeaderboard(); // Removed
    // Start polling every 10 seconds
    setInterval(fetchStats, 10000);
});

// Modal Logic
const modal = document.getElementById("serversModal");
const btnServers = document.getElementById("btnServers");
const spanClose = document.getElementsByClassName("modal-close")[0];
const modalBackdrop = document.querySelector(".modal-backdrop");

if (btnServers && modal) {
    btnServers.onclick = function() {
        modal.classList.add("active");
    }
    
    const closeModal = () => {
        modal.classList.remove("active");
    }

    if (spanClose) spanClose.onclick = closeModal;
    if (modalBackdrop) modalBackdrop.onclick = closeModal;
    
    window.onclick = function(event) {
        if (event.target == modal) {
            closeModal();
        }
    }
}

// --- Leaderboard Logic (Real) ---
async function initLeaderboard() {
    const el = document.getElementById("leaderboardList");
    if (!el) return;

    try {
        const res = await fetch("/api/leaderboard");
        if (!res.ok) throw new Error("API Error");
        const data = await res.json();

        if (data.length === 0) {
            el.innerHTML = '<div class="lb-item">Aucune donnée disponible</div>';
            return;
        }

        el.innerHTML = data.map((u, i) => {
            const rank = i + 1;
            return `
            <div class="lb-item" data-rank="${rank}">
                <div class="lb-rank">#${rank}</div>
                <div class="lb-avatar"><img src="${u.avatar}" alt=""></div>
                <div class="lb-info">
                    <div class="lb-name">${u.name}</div>
                    <div class="lb-detail">Citoyen</div>
                </div>
                <div class="lb-val">${formatMoney(u.balance)} $</div>
            </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Leaderboard fail:", e);
        el.innerHTML = '<div class="lb-item">Erreur de chargement</div>';
    }
}

function formatMoney(n) {
    if (n >= 1e9) return (n / 1e9).toFixed(1) + "Mds";
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    return n.toLocaleString();
}

// --- Typing Effect ---
function initTyping() {
    const el = document.querySelector(".hero p");
    if (!el) return;
    const txt = el.innerText;
    el.innerText = "";
    
    let i = 0;
    function type() {
        if (i < txt.length) {
            el.innerText += txt.charAt(i);
            i++;
            setTimeout(type, 30);
        }
    }
    type();
}

// FreeFazer Button Logic
const freeFazerBtn = document.getElementById("freeFazerBtn");
if (freeFazerBtn) {
    freeFazerBtn.addEventListener("click", () => {
        const text = "#FREEFAZER";
        navigator.clipboard.writeText(text).then(() => {
            showToast("#FREEFAZER copié !");
            
            // Temporary animation speedup on click
            freeFazerBtn.style.animation = "none";
            // Force reflow
            void freeFazerBtn.offsetWidth;
            freeFazerBtn.style.animation = "mega-pulse 0.5s ease-in-out";
            
            setTimeout(() => {
                freeFazerBtn.style.animation = ""; // Reset to CSS default
            }, 500);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            showToast("Erreur lors de la copie");
        });
    });
}
