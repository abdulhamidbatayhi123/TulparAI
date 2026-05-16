/**
 * TulparAI Anomaly Detection Dashboard — Application Logic
 */

const API_BASE = window.location.origin;
let allResults = [];
let currentFilter = "all";

const btnDemo      = document.getElementById("btn-run-demo");
const btnTheme     = document.getElementById("btn-theme");
const iconSun      = document.getElementById("icon-sun");
const iconMoon     = document.getElementById("icon-moon");
const resultsBody  = document.getElementById("results-body");
const detailPanel  = document.getElementById("detail-content");
const valTotal     = document.getElementById("val-total");
const valNormal    = document.getElementById("val-normal");
const valAnomaly   = document.getElementById("val-anomaly");
const valScore     = document.getElementById("val-score");
const scoreCanvas  = document.getElementById("score-chart");

function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("tulpar-theme", theme);
    iconSun.style.display  = theme === "dark" ? "block" : "none";
    iconMoon.style.display = theme === "light" ? "block" : "none";
}
btnTheme.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    setTheme(current === "dark" ? "light" : "dark");
});
setTheme(localStorage.getItem("tulpar-theme") || "dark");

btnDemo.addEventListener("click", runDemo);

async function runDemo() {
    btnDemo.disabled = true;
    btnDemo.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Running...';
    try {
        const res = await fetch(`${API_BASE}/anomaly/demo`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        allResults = await res.json();
        updateStats();
        renderTable();
        drawChart();
    } catch (err) {
        alert("Failed to run demo. Make sure the API is running.\n\n" + err.message);
        console.error(err);
    } finally {
        btnDemo.disabled = false;
        btnDemo.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2L14 8L4 14V2Z" fill="currentColor"/></svg> Run Demo';
    }
}

function updateStats() {
    const total   = allResults.length;
    const normal  = allResults.filter(r => !r.result.is_anomaly).length;
    const anomaly = total - normal;
    const avgScore = total ? (allResults.reduce((s, r) => s + r.result.anomaly_score, 0) / total).toFixed(1) : "—";
    animateCounter(valTotal, total);
    animateCounter(valNormal, normal);
    animateCounter(valAnomaly, anomaly);
    valScore.textContent = avgScore;
}

function animateCounter(el, target) {
    const duration = 600;
    const start = parseInt(el.textContent) || 0;
    const startTime = performance.now();
    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + (target - start) * eased);
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelector(".filter-btn.active").classList.remove("active");
        btn.classList.add("active");
        currentFilter = btn.dataset.filter;
        renderTable();
    });
});

function renderTable() {
    let data = allResults;
    if (currentFilter === "anomaly") data = data.filter(r => r.result.is_anomaly);
    if (currentFilter === "normal")  data = data.filter(r => !r.result.is_anomaly);
    if (!data.length) {
        resultsBody.innerHTML = `<tr class="empty-row"><td colspan="6"><div class="empty-state"><p>No results to display</p></div></td></tr>`;
        return;
    }
    resultsBody.innerHTML = data.map((r, i) => {
        const res = r.result;
        const isAnomaly = res.is_anomaly;
        const score = res.anomaly_score;
        const level = score < 30 ? "low" : score < 60 ? "medium" : "high";
        const statusClass = isAnomaly ? "status-anomaly" : "status-normal";
        const statusText  = isAnomaly ? "⚠ Anomaly" : "✓ Normal";
        const typeText    = res.anomaly_type ? formatType(res.anomaly_type) : "—";
        const sport       = r.profile.sport.charAt(0).toUpperCase() + r.profile.sport.slice(1);
        return `
        <tr class="animate-in" style="animation-delay:${i * 30}ms" data-index="${allResults.indexOf(r)}">
            <td><strong>${r.profile.name}</strong></td>
            <td>${sport}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>
                <div class="score-bar-wrap">
                    <div class="score-bar"><div class="score-bar-fill ${level}" style="width:${score}%"></div></div>
                    <span class="score-text">${score}</span>
                </div>
            </td>
            <td>${typeText}</td>
            <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis">${res.recommendation || "—"}</td>
        </tr>`;
    }).join("");
    resultsBody.querySelectorAll("tr").forEach(tr => {
        tr.addEventListener("click", () => {
            document.querySelectorAll("#results-table tr.selected").forEach(s => s.classList.remove("selected"));
            tr.classList.add("selected");
            showDetail(allResults[parseInt(tr.dataset.index)]);
        });
    });
}

function formatType(t) { return t.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()); }

function showDetail(r) {
    const res = r.result, prof = r.profile, log = r.log;
    const score = res.anomaly_score, isAnomaly = res.is_anomaly;
    const circumference = 2 * Math.PI * 50;
    const offset = circumference - (score / 100) * circumference;
    const gaugeColor = score < 30 ? "var(--green)" : score < 60 ? "var(--yellow)" : "var(--red)";
    detailPanel.innerHTML = `
        <div class="gauge-wrap"><div class="gauge">
            <svg viewBox="0 0 120 120"><circle class="gauge-bg" cx="60" cy="60" r="50"/><circle class="gauge-fill" cx="60" cy="60" r="50" stroke="${gaugeColor}" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"/></svg>
            <div class="gauge-value"><span class="gauge-number" style="color:${gaugeColor}">${score}</span><span class="gauge-label">Score</span></div>
        </div></div>
        <div class="detail-section"><div class="detail-section-title">Athlete</div>
            <div class="detail-row"><span class="label">Name</span><span class="value">${prof.name}</span></div>
            <div class="detail-row"><span class="label">Sport</span><span class="value">${prof.sport}</span></div>
            <div class="detail-row"><span class="label">Goal</span><span class="value">${prof.goal}</span></div>
            <div class="detail-row"><span class="label">Target Calories</span><span class="value">${prof.target_daily_calories} kcal</span></div>
        </div>
        <div class="detail-section"><div class="detail-section-title">Today's Log</div>
            <div class="detail-row"><span class="label">Calories</span><span class="value">${log.calories_eaten} kcal</span></div>
            <div class="detail-row"><span class="label">Protein</span><span class="value">${log.protein_g}g</span></div>
            <div class="detail-row"><span class="label">Carbs</span><span class="value">${log.carbs_g}g</span></div>
            <div class="detail-row"><span class="label">Fat</span><span class="value">${log.fat_g}g</span></div>
            <div class="detail-row"><span class="label">Training</span><span class="value">${log.training_duration_min} min @ ${log.training_intensity}/10</span></div>
            <div class="detail-row"><span class="label">Sleep</span><span class="value">${log.sleep_hours} hrs</span></div>
            <div class="detail-row"><span class="label">Hydration</span><span class="value">${log.hydration_liters} L</span></div>
        </div>
        ${res.anomaly_type ? `<div class="detail-section"><div class="detail-section-title">Anomaly Type</div><div style="font-weight:700;color:var(--red);margin-bottom:0.5rem">${formatType(res.anomaly_type)}</div></div>` : ""}
        <div class="detail-section"><div class="detail-section-title">Recommendation</div>
            <div class="detail-recommendation ${isAnomaly ? '' : 'normal-rec'}">${res.recommendation || "Everything looks good! Keep following your plan."}</div>
        </div>`;
}

function drawChart() {
    const ctx = scoreCanvas.getContext("2d");
    const W = scoreCanvas.width, H = scoreCanvas.height;
    const pad = { top: 20, right: 20, bottom: 40, left: 50 };
    ctx.clearRect(0, 0, W, H);
    if (!allResults.length) return;
    const scores = allResults.map(r => r.result.anomaly_score);
    const names  = allResults.map(r => r.profile.name.split(" ")[0]);
    const chartW = W - pad.left - pad.right, chartH = H - pad.top - pad.bottom;
    const barW = Math.min(30, (chartW / scores.length) * 0.7);
    const gap = (chartW - barW * scores.length) / (scores.length + 1);
    const maxScore = Math.max(100, ...scores);
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textColor = isDark ? "#9090a8" : "#5a5a72";
    const gridColor = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.06)";
    ctx.strokeStyle = gridColor; ctx.lineWidth = 1;
    for (let v = 0; v <= 100; v += 25) {
        const y = pad.top + chartH - (v / maxScore) * chartH;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
        ctx.fillStyle = textColor; ctx.font = "11px Inter"; ctx.textAlign = "right";
        ctx.fillText(v.toString(), pad.left - 8, y + 4);
    }
    scores.forEach((score, i) => {
        const x = pad.left + gap + i * (barW + gap);
        const barH = (score / maxScore) * chartH;
        const y = pad.top + chartH - barH;
        const grad = ctx.createLinearGradient(x, y, x, pad.top + chartH);
        if (score < 30) { grad.addColorStop(0, "#22c55e"); grad.addColorStop(1, "rgba(34,197,94,0.2)"); }
        else if (score < 60) { grad.addColorStop(0, "#eab308"); grad.addColorStop(1, "rgba(234,179,8,0.2)"); }
        else { grad.addColorStop(0, "#ef4444"); grad.addColorStop(1, "rgba(239,68,68,0.2)"); }
        const r = Math.min(4, barW / 2);
        ctx.fillStyle = grad; ctx.beginPath();
        ctx.moveTo(x + r, y); ctx.lineTo(x + barW - r, y);
        ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
        ctx.lineTo(x + barW, pad.top + chartH); ctx.lineTo(x, pad.top + chartH);
        ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.fill();
        ctx.fillStyle = textColor; ctx.font = "10px Inter"; ctx.textAlign = "center";
        ctx.save(); ctx.translate(x + barW / 2, pad.top + chartH + 14); ctx.rotate(-0.4);
        ctx.fillText(names[i], 0, 0); ctx.restore();
        ctx.fillStyle = isDark ? "#e8e8f0" : "#1a1a2e"; ctx.font = "bold 10px Inter"; ctx.textAlign = "center";
        ctx.fillText(score.toFixed(0), x + barW / 2, y - 6);
    });
    const threshY = pad.top + chartH - (50 / maxScore) * chartH;
    ctx.strokeStyle = "#A91101"; ctx.lineWidth = 2; ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(pad.left, threshY); ctx.lineTo(W - pad.right, threshY); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#A91101"; ctx.font = "bold 11px Inter"; ctx.textAlign = "left";
    ctx.fillText("Threshold", pad.left + 4, threshY - 6);
}
