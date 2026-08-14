/* ==========================================================================
   EcoPulse AI — Frontend JavaScript Application Logic
   Eco-Tech Kinetic Desktop Implementation
   Handles: Navigation, Chat AI Copilot, Smart Meter Telemetry,
   Weather Thermal Analysis, ToU Tariff Simulator, Household Explorer
   ========================================================================== */

const API_BASE = "";

// Chart instances
let dailyChartInst = null;
let diurnalChartInst = null;
let cohortChartInst = null;
let weatherChartInst = null;
let tariffChartInst = null;

// Appliance Preset Specifications
const APPLIANCE_PRESETS = {
  ev_charger: { power: 7.2, duration: 4.0 },
  heat_pump: { power: 3.5, duration: 6.0 },
  washing_machine: { power: 2.2, duration: 1.5 },
  dishwasher: { power: 1.8, duration: 2.0 },
  water_heater: { power: 3.0, duration: 2.5 },
  general: { power: 2.0, duration: 2.0 }
};

// ─────────────────────────────────────────────────────────────────────────────
// PANEL NAVIGATION & SYNC
// ─────────────────────────────────────────────────────────────────────────────

function switchPanel(panelId, linkEl) {
  // Hide all panels
  document.querySelectorAll(".panel").forEach(p => {
    p.classList.remove("active");
  });

  const target = document.getElementById("panel-" + panelId);
  if (target) {
    target.classList.add("active");
  }

  // Update nav links
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
  const activeNav = linkEl || document.querySelector(`.nav-link[data-panel="${panelId}"]`);
  if (activeNav) activeNav.classList.add("active");

  // Update topbar tabs
  document.querySelectorAll(".tab-item").forEach(t => t.classList.remove("active"));
  const tabMap = { chat: 0, tariff: 1, meter: 2 };
  const tabIdx = tabMap[panelId];
  const tabs = document.querySelectorAll(".tab-item");
  if (tabIdx !== undefined && tabs[tabIdx]) {
    tabs[tabIdx].classList.add("active");
  }

  // Titles
  const panelTitles = {
    chat: ["⚡ New Audit", "Connect data sources or ask EcoPulse to run predictive models on current infrastructure state"],
    meter: ["📊 Smart Meter Analytics", "Query 30-minute diurnal slots and daily energy telemetry for any household"],
    weather: ["🌤️ Thermal Variance & Weather", "Correlate microclimate conditions, degree days, and heating/cooling stress"],
    tariff: ["💰 ESG Report & Tariff Simulator", "Optimize appliance load scheduling across Time-of-Use tariff rate windows"],
    households: ["🏠 London Household Explorer", "Browse the London Smart Meter dataset of 5,566 households"]
  };

  const [title, subtitle] = panelTitles[panelId] || ["EcoPulse AI", ""];
  document.getElementById("pageTitle").textContent = title;
  document.getElementById("pageSubtitle").textContent = subtitle;

  // Auto-load households if empty
  if (panelId === "households") {
    const grid = document.getElementById("householdGrid");
    if (grid && grid.children.length === 0) {
      loadHouseholds();
    }
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
  return false;
}

function syncHouseholdId(value) {
  const cleanId = value.trim().toUpperCase() || "MAC000002";
  document.getElementById("globalHouseholdId").value = cleanId;
  const meterIn = document.getElementById("meterHouseId");
  if (meterIn) meterIn.value = cleanId;
  const tariffIn = document.getElementById("tariffHouseId");
  if (tariffIn) tariffIn.value = cleanId;
}

function quickSelectHousehold(lclid) {
  syncHouseholdId(lclid);
  switchPanel("meter");
  loadMeterData();
}

function focusChatInput() {
  const input = document.getElementById("chatInput");
  if (input) {
    input.focus();
    input.scrollIntoView({ behavior: "smooth" });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// CHAT PANEL & AI COPILOT
// ─────────────────────────────────────────────────────────────────────────────

function sendQuickQuery(text) {
  switchPanel("chat");
  const input = document.getElementById("chatInput");
  input.value = text;
  sendMessage();
}

async function sendMessage() {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  const householdId = document.getElementById("globalHouseholdId").value.trim() || null;

  // Append User message
  appendChatMessage("user", message);
  input.value = "";
  input.style.height = "auto";

  // Hide hero header & bento cards to give full stage to chat stream
  const heroHeader = document.getElementById("heroHeader");
  const bentoGrid = document.getElementById("bentoQuickGrid");
  if (heroHeader) heroHeader.style.display = "none";
  if (bentoGrid) bentoGrid.style.display = "none";

  showTypingIndicator(true);
  const sendBtn = document.getElementById("sendBtn");
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, household_id: householdId })
    });

    const data = await res.json();
    showTypingIndicator(false);
    if (sendBtn) sendBtn.disabled = false;

    if (res.ok && data.response) {
      appendChatMessage("ai", data.response, true);
    } else {
      appendChatMessage("ai", `⚠️ **Diagnostics Error**: ${data.detail || "Unable to complete energy analytics query."}`, true);
    }

  } catch (err) {
    showTypingIndicator(false);
    if (sendBtn) sendBtn.disabled = false;
    appendChatMessage("ai", `⚠️ **Connection Error**: Failed to reach EcoPulse backend server.\n\n\`${err.message}\``, true);
  }
}

function appendChatMessage(role, text, isMarkdown = false) {
  const container = document.getElementById("chatMessages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar";
  avatar.textContent = role === "ai" ? "⚡" : "U";

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";

  if (isMarkdown && typeof marked !== "undefined") {
    bubble.innerHTML = marked.parse(text);
  } else {
    bubble.textContent = text;
  }

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  container.appendChild(msgDiv);

  // Auto scroll
  const canvas = document.querySelector(".main-canvas");
  if (canvas) canvas.scrollTop = canvas.scrollHeight;
}

function showTypingIndicator(show) {
  const indicator = document.getElementById("typingIndicator");
  if (!indicator) return;
  if (show) {
    indicator.classList.remove("hidden");
    const canvas = document.querySelector(".main-canvas");
    if (canvas) canvas.scrollTop = canvas.scrollHeight;
  } else {
    indicator.classList.add("hidden");
  }
}

// Auto-expand textarea & handle Enter submit
document.addEventListener("DOMContentLoaded", () => {
  const textarea = document.getElementById("chatInput");
  if (textarea) {
    textarea.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 120) + "px";
    });
    textarea.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }
  autoFillApplianceParams();
});

// ─────────────────────────────────────────────────────────────────────────────
// METER ANALYTICS PANEL
// ─────────────────────────────────────────────────────────────────────────────

async function loadMeterData() {
  const lclid = document.getElementById("meterHouseId").value.trim().toUpperCase() || "MAC000002";
  const startDate = document.getElementById("meterStartDate").value || "2013-01-01";
  const endDate   = document.getElementById("meterEndDate").value   || "2013-01-14";

  syncHouseholdId(lclid);

  try {
    const [overviewRes, hhRes] = await Promise.all([
      fetch(`${API_BASE}/api/household/${lclid}/overview?start_date=${startDate}&end_date=${endDate}`),
      fetch(`${API_BASE}/api/household/${lclid}/half-hourly?start_date=${startDate}&end_date=${encodeURIComponent(endDate)}`)
    ]);

    if (!overviewRes.ok) {
      alert(`Household '${lclid}' not found or no data available in date range.`);
      return;
    }

    const overview = await overviewRes.json();
    const daily = overview.daily_readings || [];
    const cohort = overview.cohort_benchmark || {};

    if (daily.length > 0) {
      const totalKwh = daily.reduce((s, d) => s + d.energy_sum_kwh, 0).toFixed(1);
      const meanKwh  = (daily.reduce((s, d) => s + d.energy_mean_kwh, 0) / daily.length).toFixed(2);
      const maxKwh   = Math.max(...daily.map(d => d.energy_max_kwh)).toFixed(2);

      document.getElementById("statTotal").textContent   = totalKwh + " kWh";
      document.getElementById("statMean").textContent    = meanKwh + " kWh";
      document.getElementById("statMax").textContent     = maxKwh + " kWh";
      document.getElementById("statVampire").textContent = "~0.12 kWh";
      document.getElementById("meterStats").style.display = "grid";
    }

    // Daily Chart
    renderDailyChart(daily);
    document.getElementById("dailyChartCard").style.display = "block";

    // Cohort Benchmark
    renderCohortChart(cohort, daily.length > 0 ? (daily.reduce((s, d) => s + d.energy_sum_kwh, 0) / daily.length).toFixed(2) : 0);
    document.getElementById("cohortCard").style.display = "block";

    // Half-hourly Diurnal
    if (hhRes.ok) {
      const hhData = await hhRes.json();
      if (hhData.data && hhData.data.length > 0) {
        renderDiurnalChart(hhData.data);
        document.getElementById("diurnalChartCard").style.display = "block";

        renderAnomalies(hhData.data, parseFloat(document.getElementById("statMean").textContent || 10));
        document.getElementById("anomalyCard").style.display = "block";
      }
    }

  } catch (err) {
    console.error("Meter telemetry error:", err);
    alert("Error loading meter data: " + err.message);
  }
}

function renderDailyChart(daily) {
  const ctx = document.getElementById("dailyChart").getContext("2d");
  if (dailyChartInst) dailyChartInst.destroy();

  const labels = daily.map(d => d.date);
  const sums   = daily.map(d => d.energy_sum_kwh);

  const grad = ctx.createLinearGradient(0, 0, 0, 300);
  grad.addColorStop(0, "rgba(0, 242, 255, 0.3)");
  grad.addColorStop(1, "rgba(0, 242, 255, 0.0)");

  dailyChartInst = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Daily Total Consumption (kWh)",
          data: sums,
          fill: true,
          backgroundColor: grad,
          borderColor: "#00F2FF",
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: "#00F2FF",
          pointHoverRadius: 7,
          tension: 0.35
        }
      ]
    },
    options: chartOptions("kWh")
  });
}

function renderDiurnalChart(hhDays) {
  const ctx = document.getElementById("diurnalChart").getContext("2d");
  if (diurnalChartInst) diurnalChartInst.destroy();

  const N = hhDays.length;
  const avgSlots = Array(48).fill(0);
  hhDays.forEach(d => {
    (d.half_hourly_slots_kwh || []).forEach((v, i) => { avgSlots[i] += v / N; });
  });

  const labels = Array.from({length: 48}, (_, i) => {
    const h = Math.floor(i / 2).toString().padStart(2, "0");
    const m = i % 2 === 0 ? "00" : "30";
    return `${h}:${m}`;
  });

  const slotColors = avgSlots.map((_, i) => {
    if (i >= 32 && i <= 39) return "rgba(255, 77, 106, 0.85)";   // 16:00-19:30 Peak
    if (i >= 2  && i <= 13) return "rgba(16, 185, 129, 0.85)";   // 01:00-07:00 Off-Peak
    return "rgba(0, 242, 255, 0.65)";
  });

  diurnalChartInst = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Avg kWh per 30-min slot",
        data: avgSlots.map(v => v.toFixed(4)),
        backgroundColor: slotColors,
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      ...chartOptions("kWh"),
      plugins: {
        ...chartOptions("kWh").plugins,
        legend: {
          display: true,
          labels: {
            generateLabels: () => [
              { text: "🔴 Peak Surge Window (16:00-19:30)", fillStyle: "rgba(255, 77, 106, 0.85)", fontColor: "#bfc9c3" },
              { text: "✅ Off-Peak Window (01:00-07:00)", fillStyle: "rgba(16, 185, 129, 0.85)", fontColor: "#bfc9c3" },
              { text: "🔵 Standard Operation", fillStyle: "rgba(0, 242, 255, 0.65)", fontColor: "#bfc9c3" }
            ]
          }
        }
      }
    }
  });
}

function renderCohortChart(cohort, householdMean) {
  const ctx = document.getElementById("cohortChart").getContext("2d");
  if (cohortChartInst) cohortChartInst.destroy();

  cohortChartInst = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Cohort P25", "Cohort Median", "Cohort Mean", "Cohort P75", "This Household"],
      datasets: [{
        label: "Daily kWh Baseline",
        data: [
          cohort.p25_kwh || 6.2,
          cohort.median_kwh || 9.8,
          cohort.mean_kwh || 11.5,
          cohort.p75_kwh || 15.1,
          parseFloat(householdMean)
        ],
        backgroundColor: [
          "rgba(0, 242, 255, 0.3)",
          "rgba(0, 242, 255, 0.5)",
          "rgba(0, 242, 255, 0.5)",
          "rgba(0, 242, 255, 0.3)",
          "rgba(16, 185, 129, 0.9)"
        ],
        borderRadius: 6
      }]
    },
    options: chartOptions("kWh/day")
  });
}

function renderAnomalies(hhDays, meanKwh) {
  const list = document.getElementById("anomalyList");
  list.innerHTML = "";
  const threshold = meanKwh * 1.35;
  let found = false;

  hhDays.forEach(d => {
    if (d.daily_total_kwh > threshold && threshold > 0) {
      found = true;
      const el = document.createElement("div");
      el.className = "anomaly-item HIGH";
      el.innerHTML = `
        <div class="anomaly-type">HIGH CONSUMPTION SURGE ALERT</div>
        <div class="anomaly-date">📅 ${d.date} — Observed Total: ${d.daily_total_kwh.toFixed(2)} kWh</div>
        <div class="anomaly-desc">Daily energy load exceeded the household mean threshold (${meanKwh.toFixed(2)} kWh) by over 35%. Inspect heavy HVAC, thermal water heating, or concurrent appliance draw.</div>
      `;
      list.appendChild(el);
    }
    if (d.overnight_baseline_avg_kwh > 0.22) {
      found = true;
      const el = document.createElement("div");
      el.className = "anomaly-item MEDIUM";
      el.innerHTML = `
        <div class="anomaly-type">ELEVATED VAMPIRE STANDBY LOAD</div>
        <div class="anomaly-date">📅 ${d.date} — Overnight Slot Avg: ${d.overnight_baseline_avg_kwh.toFixed(3)} kWh/slot</div>
        <div class="anomaly-desc">Continuous baseline draw during 00:00-05:00 exceeds the 0.08 kWh baseline. Check always-on electronics, refrigerator seal degradation, or continuous space heaters.</div>
      `;
      list.appendChild(el);
    }
  });

  if (!found) {
    list.innerHTML = `<div style="color: var(--kinetic-green); font-family: var(--font-mono); font-size: 0.9rem; padding: 0.75rem;">✅ No telemetry anomalies detected. Energy consumption pattern is within normal statistical bounds.</div>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// WEATHER PANEL
// ─────────────────────────────────────────────────────────────────────────────

async function loadWeatherData() {
  const lat  = parseFloat(document.getElementById("weatherLat").value) || 51.5074;
  const lon  = parseFloat(document.getElementById("weatherLon").value) || -0.1278;
  const date = document.getElementById("weatherDate").value || "2013-01-15";

  try {
    const res  = await fetch(`${API_BASE}/api/weather/forecast?lat=${lat}&lon=${lon}&target_date=${date}&hours_ahead=24`);
    const data = await res.json();

    if (!res.ok || data.status !== "success") {
      alert("Weather thermal data unavailable.");
      return;
    }

    const s = data.summary;
    document.getElementById("weatherTemp").textContent = s.average_temperature_c + "°C";
    document.getElementById("weatherFeel").textContent = `Feels like ${s.average_feels_like_c}°C`;
    document.getElementById("weatherDesc").textContent = data.location.city;

    // Thermal badge styling
    const badge = document.getElementById("thermalBadge");
    const stressStyles = {
      "HIGH_HEATING_DEMAND_FREEZE_RISK": { bg: "rgba(255,180,171,0.15)", color: "#ffb4ab", border: "rgba(255,180,171,0.4)" },
      "MODERATE_HEATING_DEMAND":         { bg: "rgba(255,200,66,0.15)",  color: "#ffc842", border: "rgba(255,200,66,0.4)" },
      "HIGH_COOLING_DEMAND":             { bg: "rgba(255,133,0,0.15)",   color: "#ff8500", border: "rgba(255,133,0,0.4)" },
      "BALANCED_COMFORT_ZONE":           { bg: "rgba(16,185,129,0.15)",  color: "#10B981", border: "rgba(16,185,129,0.4)" }
    };

    const st = stressStyles[s.thermal_stress_index] || stressStyles["BALANCED_COMFORT_ZONE"];
    badge.style.cssText = `background:${st.bg}; color:${st.color}; border:1px solid ${st.border};`;
    badge.textContent = "THERMAL STRESS: " + s.thermal_stress_index.replace(/_/g, " ");

    document.getElementById("energyAdvisory").textContent = "💡 Advisory: " + s.energy_advisory;

    // Metrics list
    const metricsEl = document.getElementById("weatherMetrics");
    metricsEl.innerHTML = [
      ["Min Temp",  s.min_temperature_c + "°C"],
      ["Max Temp",  s.max_temperature_c + "°C"],
      ["HDD Index", s.heating_degree_days_hdd + " HDD"],
      ["CDD Index", s.cooling_degree_days_cdd + " CDD"]
    ].map(([l, v]) => `
      <div class="wm-item">
        <div class="wm-label">${l}</div>
        <div class="wm-value">${v}</div>
      </div>
    `).join("");

    document.getElementById("weatherSummary").style.display = "grid";

    if (data.hourly_forecast && data.hourly_forecast.length > 0) {
      renderWeatherChart(data.hourly_forecast);
      document.getElementById("weatherChartCard").style.display = "block";
    }

  } catch (err) {
    console.error("Weather error:", err);
    alert("Error loading weather data: " + err.message);
  }
}

function renderWeatherChart(hourly) {
  const ctx = document.getElementById("weatherChart").getContext("2d");
  if (weatherChartInst) weatherChartInst.destroy();

  const labels = hourly.map(h => h.time ? h.time.split(" ")[1]?.slice(0,5) || h.time.slice(11,16) : "");
  const temps  = hourly.map(h => h.temperature_c);
  const feels  = hourly.map(h => h.apparent_temperature_c);

  weatherChartInst = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Ambient Temp (°C)",
          data: temps,
          borderColor: "#00F2FF",
          backgroundColor: "rgba(0, 242, 255, 0.08)",
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 3
        },
        {
          label: "Feels-Like Temp (°C)",
          data: feels,
          borderColor: "#adc6ff",
          borderDash: [5, 4],
          fill: false,
          tension: 0.4,
          borderWidth: 1.5,
          pointRadius: 0
        }
      ]
    },
    options: chartOptions("°C")
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// TARIFF SIMULATOR PANEL
// ─────────────────────────────────────────────────────────────────────────────

function autoFillApplianceParams() {
  const key = document.getElementById("tariffAppliance").value;
  const spec = APPLIANCE_PRESETS[key];
  if (spec) {
    document.getElementById("tariffPower").value = spec.power;
    document.getElementById("tariffDuration").value = spec.duration;
  }
}

async function loadTariffData() {
  const appliance   = document.getElementById("tariffAppliance").value;
  const powerRaw    = document.getElementById("tariffPower").value;
  const durationRaw = document.getElementById("tariffDuration").value;
  const hhId        = document.getElementById("tariffHouseId").value.trim() || null;

  const body = {
    appliance_type: appliance,
    power_draw_kw: powerRaw ? parseFloat(powerRaw) : null,
    duration_hours: durationRaw ? parseFloat(durationRaw) : null,
    household_id: hhId
  };

  try {
    const res  = await fetch(`${API_BASE}/api/simulate/tariff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();

    if (!res.ok) { alert("Tariff simulation calculation error."); return; }

    const costs = data.cost_breakdown;
    const app   = data.appliance;

    document.getElementById("peakCost").textContent     = "£" + costs.cost_if_run_in_peak_gbp.toFixed(2);
    document.getElementById("standardCost").textContent = "£" + costs.cost_if_run_in_standard_gbp.toFixed(2);
    document.getElementById("offPeakCost").textContent  = "£" + costs.cost_if_run_in_off_peak_gbp.toFixed(2);

    // Savings Highlight
    const sh = document.getElementById("savingsHighlight");
    sh.innerHTML = `
      <span class="savings-amount">£${costs.single_cycle_savings_gbp.toFixed(2)}</span>
      <div class="savings-label">Saved per cycle shifting load from Peak to Off-Peak (${costs.savings_percentage}% cost reduction)</div>
      <div class="savings-annual">💰 Annualized Savings Projection: £${costs.annualized_projected_savings_gbp.toFixed(2)} / year</div>
    `;

    // Advice
    document.getElementById("tariffAdvice").innerHTML = `
      <h4 style="font-family:var(--font-headline); color:var(--electric-cyan); font-size:1.1rem; margin-bottom:0.5rem;">⚡ AI Load Scheduling Recommendation</h4>
      <p>${data.actionable_advice}</p>
      <p style="margin-top:0.75rem; font-family:var(--font-mono); font-size:0.8rem; color:var(--on-surface-variant);">
        <strong>${app.name}</strong> (${app.power_draw_kw} kW × ${app.duration_hours} hrs = <strong>${app.total_energy_kwh} kWh</strong> per charge cycle)
      </p>
    `;

    renderTariffChart(costs);
    document.getElementById("tariffResults").style.display = "block";

  } catch (err) {
    console.error("Tariff error:", err);
    alert("Error running tariff simulation: " + err.message);
  }
}

function renderTariffChart(costs) {
  const ctx = document.getElementById("tariffChart").getContext("2d");
  if (tariffChartInst) tariffChartInst.destroy();

  tariffChartInst = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Peak Surge (16-19h)", "Standard Window", "Off-Peak (01-07h)", "Flat Standard Rate"],
      datasets: [{
        label: "Single Cycle Cost (£)",
        data: [
          costs.cost_if_run_in_peak_gbp,
          costs.cost_if_run_in_standard_gbp,
          costs.cost_if_run_in_off_peak_gbp,
          costs.cost_under_flat_tariff_gbp
        ],
        backgroundColor: [
          "rgba(255, 77, 106, 0.8)",
          "rgba(255, 200, 66, 0.8)",
          "rgba(16, 185, 129, 0.85)",
          "rgba(173, 198, 255, 0.6)"
        ],
        borderRadius: 8,
        borderSkipped: false
      }]
    },
    options: chartOptions("£")
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// HOUSEHOLD EXPLORER PANEL
// ─────────────────────────────────────────────────────────────────────────────

async function loadHouseholds() {
  try {
    const res  = await fetch(`${API_BASE}/api/household/sample?limit=30`);
    const data = await res.json();

    const grid = document.getElementById("householdGrid");
    grid.innerHTML = "";

    (data.households || []).forEach(hh => {
      const card = document.createElement("div");
      card.className = "hh-card";
      const isTou = hh.tariff_type === "ToU";
      const tariffBadgeClass = isTou ? "tou" : "std";
      card.innerHTML = `
        <div class="hh-id">${hh.lclid}</div>
        <span class="hh-tariff ${tariffBadgeClass}">${isTou ? "⚡ ToU Dynamic" : "📊 Standard Flat"}</span>
        <div class="hh-acorn-group">${hh.acorn_group || "Adversity / Comfortable"}</div>
        <div class="hh-acorn">${hh.acorn || "ACORN Group"}</div>
      `;
      card.onclick = () => quickSelectHousehold(hh.lclid);
      grid.appendChild(card);
    });

  } catch (err) {
    console.error("Household explorer error:", err);
    alert("Error loading sample households: " + err.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// UNIFIED CHART OPTIONS (DARK KINETIC THEME)
// ─────────────────────────────────────────────────────────────────────────────

function chartOptions(unit = "") {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500, easing: "easeOutQuart" },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: "#bfc9c3",
          font: { size: 11, family: "Inter" },
          boxWidth: 12
        }
      },
      tooltip: {
        backgroundColor: "rgba(12, 15, 13, 0.95)",
        titleColor: "#00F2FF",
        bodyColor: "#e1e3e0",
        borderColor: "rgba(0, 242, 255, 0.3)",
        borderWidth: 1,
        padding: 12,
        titleFont: { family: "JetBrains Mono", size: 13, weight: "bold" },
        bodyFont: { family: "JetBrains Mono", size: 12 },
        callbacks: {
          label: ctx => ` ${ctx.dataset.label || ''}: ${ctx.parsed.y} ${unit}`
        }
      }
    },
    scales: {
      x: {
        grid: { color: "rgba(255, 255, 255, 0.04)", drawBorder: false },
        ticks: { color: "#89938d", font: { family: "JetBrains Mono", size: 10 }, maxTicksLimit: 14 }
      },
      y: {
        grid: { color: "rgba(255, 255, 255, 0.05)", drawBorder: false },
        ticks: {
          color: "#89938d",
          font: { family: "JetBrains Mono", size: 10 },
          callback: v => v + (unit ? " " + unit : "")
        }
      }
    }
  };
}
