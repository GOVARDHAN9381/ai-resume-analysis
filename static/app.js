/* ================================================================
   ResumeAI  —  App JavaScript (Full Feature Set)
   SPA routing, API calls, animations, charts, advanced AI features
   ================================================================ */

'use strict';

// ⚠️ CHANGE THIS to your deployed Render URL once your backend is hosted
const API_BASE_URL = "https://ai-resume-analysis-wzya.onrender.com";

// ─── Keep-Alive Heartbeat ─────────────────────
// Pings the backend every 10 minutes so Render never cold-starts
(function keepAlive() {
  const INTERVAL_MS = 10 * 60 * 1000; // 10 minutes
  async function ping() {
    try {
      await fetch(API_BASE_URL + '/ping');
      console.debug('[KeepAlive] Backend pinged ✅');
    } catch (_) {
      console.debug('[KeepAlive] Ping failed — backend may be waking up.');
    }
  }
  ping(); // ping immediately on page load
  setInterval(ping, INTERVAL_MS);
})();

// ─── JD Templates ────────────────────────────
const JD_TEMPLATES = {
  swe: `We are looking for a Senior Software Engineer to build and scale our web applications.\n\nRequirements:\n- 5+ years of experience in Software Engineering.\n- Strong proficiency in Python, React, Node.js, and TypeScript.\n- Experience with Docker, Kubernetes, and AWS cloud platforms.\n- Solid understanding of Git, CI/CD, SQL, and Microservices design.`,
  ds: `We are looking for a Senior Data Scientist to drive machine learning projects.\n\nRequirements:\n- 4+ years of experience in Data Science & AI.\n- Proficient in Python, SQL, and Machine Learning libraries (Scikit-Learn, Pandas, NumPy).\n- Experience in Deep Learning, NLP, and BERT models using PyTorch or TensorFlow.\n- Experience building LLMs, data pipelines, and utilizing Apache Spark.`,
  pm: `We are looking for an experienced Product Manager to lead our SaaS growth.\n\nRequirements:\n- 3+ years of experience in Product Management.\n- Expertise in Agile, Scrum, Jira, and writing PRDs.\n- Skilled in Product Analytics, A/B Testing, User Research, and Figma.\n- Ability to define Product Roadmaps and translate metrics into data-driven decisions.`,
  mkt: `Join us as a Digital Marketing Manager.\n\nRequirements:\n- Experience in SEO, SEM, Content Strategy, and Social Media Marketing.\n- Proficient with Google Analytics, HubSpot CRM, and Salesforce.\n- Proven track record in copywriting, email campaigns, and B2B Sales lead generation.`,
  fin: `We are seeking a Senior Financial Analyst for corporate finance.\n\nRequirements:\n- 5+ years of experience in Finance & Accounting.\n- Expert in Financial Analysis, advanced Excel, VBA, and financial modeling.\n- Experience in auditing, GAAP compliance, budgeting, and risk assessment.`
};

// ─── State ────────────────────────────────────
let _datasetInfo   = null;
let _screenResults = [];
let _currentPage   = 'home';
let _lastResumeText = '';
let _lastJdText     = '';
let _lastScreenTop  = [];

// ─── Particle System ─────────────────────────
(function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  const ctx    = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  window.addEventListener('resize', resize);
  resize();

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x     = Math.random() * W;
      this.y     = Math.random() * H;
      this.r     = Math.random() * 1.5 + 0.3;
      this.vx    = (Math.random() - 0.5) * 0.25;
      this.vy    = (Math.random() - 0.5) * 0.25;
      this.alpha = Math.random() * 0.5 + 0.1;
      this.color = Math.random() > 0.5 ? '0,245,255' : '124,58,237';
    }
    update() {
      this.x += this.vx; this.y += this.vy;
      if (this.x < 0 || this.x > W || this.y < 0 || this.y > H) this.reset();
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${this.color},${this.alpha})`;
      ctx.fill();
    }
  }

  for (let i = 0; i < 120; i++) particles.push(new Particle());

  function connectParticles() {
    const dist = 120;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < dist) {
          ctx.beginPath();
          ctx.strokeStyle = `rgba(0,245,255,${0.06 * (1 - d / dist)})`;
          ctx.lineWidth = 0.5;
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
  }

  function animate() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => { p.update(); p.draw(); });
    connectParticles();
    requestAnimationFrame(animate);
  }
  animate();
})();

// ─── Page Routing ─────────────────────────────
function showPage(page) {
  document.querySelectorAll('.page').forEach(p  => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

  const el = document.getElementById(`page-${page}`);
  if (el) el.classList.add('active');
  document.querySelectorAll(`[data-page="${page}"]`).forEach(l => l.classList.add('active'));

  _currentPage = page;
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (page === 'analytics') loadAnalytics();
  if (page === 'metrics')   loadMetrics();
  if (page === 'screen')    populateCategoryFilter();
}

// ─── Dataset Info ─────────────────────────────
async function fetchDatasetInfo(retries = 5) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(API_BASE_URL + '/api/dataset-info', { signal: AbortSignal.timeout(15000) });
      if (res.ok) {
        _datasetInfo = await res.json();
        updateStatusBar();
        updateHeroStats();
        return;
      }
    } catch(e) {
      console.warn(`Dataset info attempt ${i+1} failed:`, e.message);
      if (i < retries - 1) await new Promise(r => setTimeout(r, 4000)); // wait 4s before retry
    }
  }
  console.warn('Could not fetch dataset info after retries.');
}

function updateStatusBar() {
  const dot   = document.querySelector('.status-dot');
  const label = document.getElementById('status-label');
  if (_datasetInfo && _datasetInfo.loaded) {
    dot.className   = 'status-dot active';
    label.textContent = `${_datasetInfo.total.toLocaleString()} Candidates`;
  } else {
    dot.className   = 'status-dot inactive';
    label.textContent = 'No Dataset';
  }
}

function updateHeroStats() {
  if (!_datasetInfo || !_datasetInfo.loaded) return;
  animateCount('stat-total', '.pill-val', _datasetInfo.total, '');
  animateCount('stat-avg',   '.pill-val', _datasetInfo.avg_exp, '');
  animateCount('stat-cats',  '.pill-val', Object.keys(_datasetInfo.categories || {}).length, '');
}

function animateCount(containerId, selector, target, suffix) {
  const el = document.querySelector(`#${containerId} ${selector}`);
  if (!el) return;
  const duration = 1200, start = 0, startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const ease     = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(start + (target - start) * ease) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ─── Upload ───────────────────────────────────
(function initUpload() {
  const zone  = document.getElementById('upload-zone');
  const input = document.getElementById('csv-file-input');

  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop',      e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleCsvUpload(file);
  });
  input.addEventListener('change', () => { if (input.files[0]) handleCsvUpload(input.files[0]); });
})();

async function wakeUpBackend(msgEl) {
  // Ping the backend and wait for it to wake up (Render free tier cold start)
  const MAX_WAIT = 90000; // 90 seconds max
  const start = Date.now();
  if (msgEl) msgEl.textContent = '⏳ Waking up backend (may take ~30s on first use)...';
  while (Date.now() - start < MAX_WAIT) {
    try {
      const r = await fetch(API_BASE_URL + '/ping', { signal: AbortSignal.timeout(8000) });
      if (r.ok) {
        if (msgEl) msgEl.textContent = '✅ Backend ready! Uploading...';
        return true;
      }
    } catch (_) {}
    await new Promise(r => setTimeout(r, 3000));
  }
  return false;
}

async function handleCsvUpload(file) {
  if (!file.name.toLowerCase().endsWith('.csv')) { showToast('Please upload a .csv file.', 'error'); return; }

  const prog   = document.getElementById('upload-progress');
  const fill   = document.getElementById('progress-fill');
  const msg    = document.getElementById('upload-status-msg');
  const result = document.getElementById('upload-result');
  result.classList.add('hidden');
  prog.classList.remove('hidden');
  fill.style.width = '5%';

  // Step 1: Wake up the backend first
  const alive = await wakeUpBackend(msg);
  if (!alive) {
    prog.classList.add('hidden');
    showToast('Backend is taking too long to wake up. Please try again in 30 seconds.', 'error');
    return;
  }

  // Step 2: Animate progress while uploading
  let pct = 10;
  const interval = setInterval(() => {
    pct = Math.min(pct + Math.random() * 12, 85);
    fill.style.width = pct + '%';
  }, 200);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res  = await fetch(API_BASE_URL + '/api/upload-dataset', { method: 'POST', body: formData });
    const data = await res.json();
    clearInterval(interval);
    fill.style.width = '90%';

    if (!res.ok) {
      prog.classList.add('hidden');
      showToast(data.detail || 'Upload failed.', 'error');
      return;
    }

    // Step 3: Poll /api/dataset-status until background processing is done
    msg.textContent = `⏳ Processing ${data.total?.toLocaleString() || ''} candidates in background...`;
    let pollAttempts = 0;
    let lastStatus   = null;
    const MAX_POLLS  = 120; // up to 4 minutes (120 × 2s)
    await new Promise(resolve => {
      const pollId = setInterval(async () => {
        pollAttempts++;
        try {
          const statusRes = await fetch(API_BASE_URL + '/api/dataset-status');
          const status = await statusRes.json();
          lastStatus = status;
          const loaded = status.current_loaded || 0;
          const total  = status.total_uploaded || data.total || 0;
          const pctDone = total > 0 ? Math.min(90 + Math.round((loaded / total) * 9), 99) : 95;
          fill.style.width = pctDone + '%';
          msg.textContent = `⏳ Processing… ${loaded.toLocaleString()} / ${total.toLocaleString()} candidates loaded`;

          if (status.ready || !status.running || pollAttempts >= MAX_POLLS) {
            clearInterval(pollId);
            resolve();
          }
        } catch (_) {
          if (pollAttempts >= MAX_POLLS) { clearInterval(pollId); resolve(); }
        }
      }, 2000);
    });

    fill.style.width = '100%';
    await new Promise(r => setTimeout(r, 300));
    prog.classList.add('hidden');

    // Show warning if Supabase sync had an issue (data still works in-session)
    if (lastStatus?.error && lastStatus.error.includes('Supabase sync failed')) {
      showToast('⚠️ Dataset loaded in memory. Supabase sync had an issue — screening still works this session.', 'error');
    }

    const loadedCount = lastStatus?.current_loaded || data.total || 0;
    const successMsg  = `✅ Successfully loaded ${loadedCount.toLocaleString()} candidates.`;
    document.getElementById('upload-success-title').textContent = 'Dataset Loaded!';
    document.getElementById('upload-success-msg').textContent   = successMsg;
    result.classList.remove('hidden');
    showToast(successMsg, 'success');

    // Step 4: Refresh dataset info NOW that processing is complete
    _datasetInfo = null; // clear cache so it re-fetches fresh data
    await fetchDatasetInfo();
    populateCategoryFilter();
  } catch(e) {
    clearInterval(interval);
    prog.classList.add('hidden');
    showToast('Upload error: ' + e.message, 'error');
  }
}


// ─── Analytics ────────────────────────────────
async function loadAnalytics() {
  if (!_datasetInfo) await fetchDatasetInfo();

  const noData  = document.getElementById('analytics-no-data');
  const content = document.getElementById('analytics-content');

  if (!_datasetInfo || !_datasetInfo.loaded) {
    noData.classList.remove('hidden');
    content.classList.add('hidden');
    return;
  }

  noData.classList.add('hidden');
  content.classList.remove('hidden');

  document.getElementById('m-total').textContent = _datasetInfo.total.toLocaleString();
  document.getElementById('m-exp').textContent   = _datasetInfo.avg_exp + ' yrs';
  document.getElementById('m-cats').textContent  = Object.keys(_datasetInfo.categories || {}).length;

  // Category chart
  const cats       = _datasetInfo.categories || {};
  const catMax     = Math.max(...Object.values(cats), 1);
  const catContainer = document.getElementById('cat-chart');
  catContainer.innerHTML = '';
  Object.entries(cats).sort((a, b) => b[1] - a[1]).slice(0, 10).forEach(([label, count], i) => {
    const pct = (count / catMax * 100).toFixed(1);
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `<span class="bar-label">${label}</span>
      <div class="bar-track"><div class="bar-fill" style="width:0%;transition-delay:${i*0.1}s" data-target="${pct}"></div></div>
      <span class="bar-count">${count.toLocaleString()}</span>`;
    catContainer.appendChild(row);
  });

  // Experience bands
  const bands        = _datasetInfo.exp_bands || {};
  const expMax       = Math.max(...Object.values(bands), 1);
  const expContainer = document.getElementById('exp-chart');
  expContainer.innerHTML = '';
  const expColors = ['#00f5ff','#7c3aed','#f472b6','#10b981','#fbbf24'];
  Object.entries(bands).forEach(([label, count], i) => {
    const pct = (count / expMax * 100).toFixed(1);
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `<span class="bar-label">${label}</span>
      <div class="bar-track"><div class="bar-fill" style="width:0%;background:linear-gradient(90deg,${expColors[i]},${expColors[(i+1)%expColors.length]});transition-delay:${i*0.1}s" data-target="${pct}"></div></div>
      <span class="bar-count">${count.toLocaleString()}</span>`;
    expContainer.appendChild(row);
  });

  // Animate bars
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('.bar-fill[data-target]').forEach(bar => {
      bar.style.width = bar.dataset.target + '%';
    });
  }));
}

// ─── Advanced Analytics ───────────────────────
async function loadAdvancedAnalytics() {
  const btn = document.getElementById('load-adv-btn');
  btn.disabled = true;
  btn.textContent = 'Loading...';
  showLoader('Loading advanced analytics...');

  try {
    const res  = await fetch(API_BASE_URL + '/api/advanced-analytics');
    const data = await res.json();
    hideLoader();

    if (!data.available) { showToast('No dataset available.', 'error'); return; }

    const grid = document.getElementById('adv-analytics-grid');
    grid.classList.remove('hidden');
    grid.style.display = 'grid';

    // Top skills chart
    const skillsContainer = document.getElementById('skills-chart');
    skillsContainer.innerHTML = '';
    const skills = data.top_skills || {};
    const skillMax = Math.max(...Object.values(skills), 1);
    Object.entries(skills).forEach(([skill, count], i) => {
      const pct = (count / skillMax * 100).toFixed(1);
      const row = document.createElement('div');
      row.className = 'bar-row';
      row.innerHTML = `<span class="bar-label">${skill}</span>
        <div class="bar-track"><div class="bar-fill" style="width:0%;background:linear-gradient(90deg,#f472b6,#7c3aed);transition-delay:${i*0.07}s" data-target="${pct}"></div></div>
        <span class="bar-count">${count}</span>`;
      skillsContainer.appendChild(row);
    });

    // Hiring funnel
    const funnelContainer = document.getElementById('funnel-chart');
    funnelContainer.innerHTML = '';
    const funnel = data.hiring_funnel || {};
    const funnelMax = Math.max(...Object.values(funnel), 1);
    Object.entries(funnel).forEach(([stage, count], i) => {
      const pct = (count / funnelMax * 100).toFixed(1);
      const colors = ['#00f5ff','#7c3aed','#f472b6','#10b981','#fbbf24'];
      const row = document.createElement('div');
      row.className = 'funnel-bar';
      row.innerHTML = `<span class="funnel-label">${stage}</span>
        <div class="bar-track" style="flex:1"><div class="bar-fill" style="width:0%;height:100%;background:${colors[i]};transition-delay:${i*0.1}s" data-target="${pct}"></div></div>
        <span class="funnel-count">${count.toLocaleString()}</span>`;
      funnelContainer.appendChild(row);
    });

    // Category avg experience
    const catExpContainer = document.getElementById('cat-exp-chart');
    catExpContainer.innerHTML = '';
    const catExp = data.category_avg_experience || {};
    const catExpMax = Math.max(...Object.values(catExp), 1);
    Object.entries(catExp).forEach(([cat, avg], i) => {
      const pct = (avg / catExpMax * 100).toFixed(1);
      const row = document.createElement('div');
      row.className = 'bar-row';
      row.innerHTML = `<span class="bar-label">${cat}</span>
        <div class="bar-track"><div class="bar-fill" style="width:0%;transition-delay:${i*0.1}s" data-target="${pct}"></div></div>
        <span class="bar-count">${avg} yrs</span>`;
      catExpContainer.appendChild(row);
    });

    // Animate all new bars
    requestAnimationFrame(() => requestAnimationFrame(() => {
      document.querySelectorAll('.bar-fill[data-target]').forEach(bar => {
        bar.style.width = bar.dataset.target + '%';
      });
    }));

    btn.textContent = 'Advanced Analytics Loaded';
    showToast('Advanced analytics loaded!', 'success');
  } catch(e) {
    hideLoader();
    btn.disabled = false;
    btn.textContent = 'Load Advanced Analytics';
    showToast('Error loading analytics: ' + e.message, 'error');
  }
}

// ─── Category Filter ──────────────────────────
async function populateCategoryFilter() {
  if (!_datasetInfo) await fetchDatasetInfo();
  const select = document.getElementById('cat-filter');
  if (!select) return;
  const cats = _datasetInfo ? Object.keys(_datasetInfo.categories || {}) : [];
  select.innerHTML = '<option value="All">All Categories</option>';
  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    select.appendChild(opt);
  });
}

// ─── JD Templates ─────────────────────────────
function applyJdTemplate()       { const v = document.getElementById('jd-template').value;       if (v && JD_TEMPLATES[v]) document.getElementById('jd-input').value = JD_TEMPLATES[v]; }
function applyResumeJdTemplate() { const v = document.getElementById('resume-jd-template').value; if (v && JD_TEMPLATES[v]) document.getElementById('resume-jd-input').value = JD_TEMPLATES[v]; }
function applyAtsJdTemplate()   { const v = document.getElementById('ats-jd-template').value;   if (v && JD_TEMPLATES[v]) document.getElementById('ats-jd-input').value = JD_TEMPLATES[v]; }
function applyIqJdTemplate()    { const v = document.getElementById('iq-jd-template').value;    if (v && JD_TEMPLATES[v]) document.getElementById('iq-jd-input').value = JD_TEMPLATES[v]; }

// ─── Screening ────────────────────────────────
async function runScreening() {
  const jd = document.getElementById('jd-input').value.trim();
  if (!jd) { showToast('Please enter a job description.', 'error'); return; }

  const btn = document.getElementById('screen-btn');
  btn.innerHTML = '<div class="spinner"></div> Processing...';
  btn.disabled  = true;
  showLoader('Running NLP & BERT Screening...');

  try {
    const res  = await fetch(API_BASE_URL + '/api/screen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_description: jd,
        algorithm:       document.getElementById('algo-select').value,
        filter_category: document.getElementById('cat-filter').value,
        min_exp:         parseInt(document.getElementById('exp-slider').value),
        max_results:     parseInt(document.getElementById('max-results').value),
      })
    });
    const data = await res.json();
    hideLoader();
    if (!res.ok) { showToast(data.detail, 'error'); return; }

    _screenResults = data.results;
    _lastScreenTop = data.results;
    renderLeaderboard(data);
    showToast(`Screened ${data.total_screened.toLocaleString()} candidates in ${data.time_seconds}s`, 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>&#128640;</span> Screen Candidates';
    btn.disabled  = false;
  }
}

// First renderLeaderboard removed (duplicate definition).
function exportCSV() {
  if (!_screenResults.length) return;
  const headers = Object.keys(_screenResults[0]).join(',');
  const rows    = _screenResults.map(r => Object.values(r).map(v => `"${String(v).replace(/"/g,'""')}"`).join(','));
  const blob    = new Blob([headers + '\n' + rows.join('\n')], { type: 'text/csv' });
  const a       = document.createElement('a');
  a.href        = URL.createObjectURL(blob);
  a.download    = 'resume_screened_results.csv';
  a.click();
}

async function notifyCandidates() {
  const top = _lastScreenTop.slice(0, 5);
  if (!top.length) { showToast('Run a screening first.', 'error'); return; }
  const jdTitle = document.getElementById('jd-input').value.trim().split('\n')[0].slice(0, 60) || 'Open Position';

  showLoader('Sending notifications...');
  try {
    const res  = await fetch(API_BASE_URL + '/api/notify-candidates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidates: top, job_title: jdTitle })
    });
    const data = await res.json();
    hideLoader();

    const container = document.getElementById('notify-result');
    container.classList.remove('hidden');
    container.innerHTML = `
      <div class="notify-result-card">
        <div style="font-weight:700;margin-bottom:0.5rem;">&#128231; ${data.message}</div>
        ${data.sent.map(s => `<div class="notify-sent-item">&#9989; <strong>${s.name}</strong> &lt;${s.email}&gt;</div>`).join('')}
      </div>`;
    showToast(data.message, 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  }
}

// ─── Single Resume ────────────────────────────
function switchResumeTab(tab) {
  document.querySelectorAll('#page-resume .tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (i === 0 && tab === 'paste') || (i === 1 && tab === 'upload'));
  });
  document.getElementById('resume-paste-tab').classList.toggle('hidden', tab !== 'paste');
  document.getElementById('resume-upload-tab').classList.toggle('hidden', tab !== 'upload');
}

function loadResumeFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('resume-file-preview').value = ev.target.result;
    document.getElementById('resume-text-input').value   = ev.target.result;
  };
  reader.readAsText(file);
}

async function analyzeResume() {
  const pasteText  = document.getElementById('resume-text-input').value.trim();
  const previewTxt = document.getElementById('resume-file-preview').value.trim();
  const resumeText = pasteText || previewTxt;
  const jdText     = document.getElementById('resume-jd-input').value.trim();
  if (!resumeText) { showToast('Please provide resume text.', 'error'); return; }

  _lastResumeText = resumeText;
  _lastJdText     = jdText;

  const btn = document.getElementById('analyze-btn');
  btn.innerHTML = '<div class="spinner"></div> Analyzing...';
  btn.disabled  = true;
  showLoader('Analyzing resume with NLP & ML...');

  try {
    const res  = await fetch(API_BASE_URL + '/api/analyze-resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText, job_description: jdText })
    });
    const data = await res.json();
    hideLoader();
    if (!res.ok) { showToast(data.detail, 'error'); return; }
    renderResumeResults(data);
    showToast('Resume analyzed successfully!', 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>&#128302;</span> Analyze Resume';
    btn.disabled  = false;
  }
}

function renderResumeResults(data) {
  const p = data.parsed;
  document.getElementById('parsed-grid').innerHTML = `
    <div class="parsed-item"><span>Name:</span> ${p.name}</div>
    <div class="parsed-item"><span>Email:</span> ${p.email}</div>
    <div class="parsed-item"><span>Phone:</span> ${p.phone}</div>
    <div class="parsed-item"><span>Experience:</span> ${p.experience_years} years</div>
    <div class="parsed-item" style="grid-column:1/-1"><span>Education:</span> ${p.education}</div>`;

  document.getElementById('ml-predictions').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
      <div class="glass-card" style="padding:1rem;text-align:center;">
        <div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:0.4rem;">Random Forest</div>
        <div style="font-weight:700;color:var(--cyan);margin-bottom:0.3rem;">${data.rf_category}</div>
        <div style="font-size:0.82rem;color:var(--text-secondary)">${data.rf_confidence}% confidence</div>
        <div class="score-bar-mini" style="margin-top:0.5rem;"><div class="score-bar-fill" data-target="${data.rf_confidence}" style="width:0%;background:linear-gradient(90deg,#10b981,#00f5ff)"></div></div>
      </div>
      <div class="glass-card" style="padding:1rem;text-align:center;">
        <div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:0.4rem;">Gradient Boost</div>
        <div style="font-weight:700;color:#a78bfa;margin-bottom:0.3rem;">${data.gb_category}</div>
        <div style="font-size:0.82rem;color:var(--text-secondary)">${data.gb_confidence}% confidence</div>
        <div class="score-bar-mini" style="margin-top:0.5rem;"><div class="score-bar-fill" data-target="${data.gb_confidence}" style="width:0%;background:linear-gradient(90deg,#fbbf24,#f472b6)"></div></div>
      </div>
    </div>`;

  const matchCard = document.getElementById('match-score-card');
  if (data.match_scores) {
    const ms       = data.match_scores;
    const recClass = data.recommendation === 'Highly Recommended' ? 'badge-high'
                   : data.recommendation === 'Consider for Interview' ? 'badge-consider' : 'badge-not';
    const recText  = data.recommendation === 'Highly Recommended' ? 'Highly Recommended'
                   : data.recommendation === 'Consider for Interview' ? 'Consider for Interview' : 'Not a Fit';

    matchCard.innerHTML = `
      <h3>&#128202; Match Score</h3>
      <div class="score-ring-container">
        <div class="score-ring">
          <svg viewBox="0 0 120 120">
            <defs><linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#00f5ff"/>
              <stop offset="100%" stop-color="#7c3aed"/>
            </linearGradient></defs>
            <circle class="score-ring-bg" cx="60" cy="60" r="52"/>
            <circle class="score-ring-fill" cx="60" cy="60" r="52"
              stroke-dasharray="${2*Math.PI*52}" stroke-dashoffset="${2*Math.PI*52*(1-ms.hybrid/100)}"/>
          </svg>
          <div class="score-ring-text">
            <span class="score-ring-val">${ms.hybrid}%</span>
            <span class="score-ring-sub">Hybrid</span>
          </div>
        </div>
        <span class="badge ${recClass}">${recText}</span>
      </div>
      <div class="score-bars">
        ${scoreBarRow('Semantic (BERT/TF-IDF)', ms.semantic, '#00f5ff')}
        ${scoreBarRow('Keyword Skills Match',   ms.keyword,  '#7c3aed')}
      </div>
      <div style="margin-top:1rem">
        <div style="font-size:0.82rem;color:var(--text-secondary);margin-bottom:0.4rem">Matched Skills</div>
        <div>${(ms.matched_skills||[]).map(s=>`<span class="skill-pill skill-matched">${s}</span>`).join('') || '<span style="color:var(--text-muted)">None</span>'}</div>
        <div style="font-size:0.82rem;color:var(--text-secondary);margin:0.6rem 0 0.4rem">Missing Skills</div>
        <div>${(ms.missing_skills||[]).map(s=>`<span class="skill-pill skill-missing">${s}</span>`).join('') || '<span style="color:var(--text-muted)">None</span>'}</div>
      </div>`;
    matchCard.classList.remove('hidden');
  } else {
    matchCard.innerHTML = '<h3>&#128202; Match Score</h3><p style="color:var(--text-secondary);font-size:0.88rem">No job description provided. Add one to see a match score.</p>';
  }

  const skills = p.skills || [];
  document.getElementById('extracted-skills').innerHTML = skills.length
    ? skills.map(s => `<span class="skill-pill skill-matched">${s}</span>`).join('')
    : '<span style="color:var(--text-secondary)">No skills identified.</span>';

  document.getElementById('resume-results').classList.remove('hidden');

  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('.score-bar-fill[data-target]').forEach(bar => {
      bar.style.transition = 'width 1s ease';
      bar.style.width = bar.dataset.target + '%';
    });
  }));
}

function scoreBarRow(label, value, color) {
  return `
    <div class="score-bar-row">
      <div class="score-bar-header">
        <span class="score-bar-label">${label}</span>
        <span class="score-bar-value" style="color:${color}">${value}%</span>
      </div>
      <div class="bar-track"><div class="bar-fill" data-target="${value}" style="width:0%;background:linear-gradient(90deg,${color},var(--purple))"></div></div>
    </div>`;
}

// ─── AI Summary ───────────────────────────────
async function generateSummary() {
  if (!_lastResumeText) { showToast('Analyze a resume first.', 'error'); return; }
  showLoader('Generating AI profile summary...');
  try {
    const res  = await fetch(API_BASE_URL + '/api/resume-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: _lastResumeText, job_description: _lastJdText })
    });
    const data = await res.json();
    hideLoader();

    document.getElementById('ai-summary-content').innerHTML = `
      <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,var(--cyan),var(--purple));display:flex;align-items:center;justify-content:center;font-size:1.1rem;">&#128100;</div>
        <div>
          <div style="font-weight:700;">${data.candidate_name}</div>
          <div style="font-size:0.82rem;color:var(--text-secondary);">${data.level} • ${data.domain} • ${data.experience_years} yrs exp</div>
        </div>
        <div style="margin-left:auto;text-align:right;">
          <div style="font-size:0.75rem;color:var(--text-muted)">ML Confidence</div>
          <div style="font-weight:700;color:var(--cyan);">${data.ml_confidence}%</div>
        </div>
      </div>
      <div class="summary-text">${data.summary}</div>
      <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:0.4rem;">Key Strengths</div>
      <div class="summary-strengths">${(data.strengths || []).map(s => `<span class="strength-tag">${s}</span>`).join('')}</div>
      <div style="font-size:0.8rem;color:var(--text-secondary);margin:0.75rem 0 0.4rem;">Top Skills</div>
      <div>${(data.top_skills || []).map(s => `<span class="skill-pill skill-matched">${s}</span>`).join('')}</div>`;
    showToast('AI summary generated!', 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  }
}

// ─── XAI Explain ──────────────────────────────
async function explainRecommendation() {
  if (!_lastResumeText) { showToast('Analyze a resume first.', 'error'); return; }
  if (!_lastJdText) { showToast('Please include a job description for XAI analysis.', 'error'); return; }
  showLoader('Generating explainable AI reasoning...');
  try {
    const res  = await fetch(API_BASE_URL + '/api/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: _lastResumeText, job_description: _lastJdText })
    });
    const data = await res.json();
    hideLoader();

    const verdictClass = data.verdict === 'Highly Recommended' ? 'badge-high'
                       : data.verdict === 'Consider for Interview' ? 'badge-consider' : 'badge-not';

    document.getElementById('xai-content').innerHTML = `
      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;">
        <div>
          <div style="font-size:2.5rem;font-weight:900;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;">${data.hybrid_score}%</div>
          <div style="font-size:0.8rem;color:var(--text-muted)">Hybrid Match Score</div>
        </div>
        <span class="badge ${verdictClass}" style="font-size:0.9rem;padding:0.35rem 1rem;">${data.verdict}</span>
        <div style="margin-left:auto;font-size:0.82rem;color:var(--text-secondary);max-width:220px;">${data.verdict_reason}</div>
      </div>
      <div style="font-size:0.82rem;color:var(--text-secondary);margin-bottom:0.5rem;font-weight:600;">Decision Factors</div>
      ${(data.factors || []).map(f => `
        <div class="xai-factor ${f.impact === 'POSITIVE' ? 'xai-positive' : 'xai-negative'}">
          <div class="xai-factor-icon">${f.icon}</div>
          <div style="flex:1">
            <div class="xai-factor-name">${f.factor}</div>
            <div class="xai-factor-detail">${f.detail}</div>
          </div>
          <div class="xai-weight">+${f.weight}pts</div>
        </div>`).join('')}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-top:0.75rem;font-size:0.82rem;">
        <div style="background:rgba(255,255,255,0.03);padding:0.6rem;border-radius:var(--radius-sm);">
          <div style="color:var(--text-muted)">Semantic Score</div>
          <div style="font-weight:700;color:var(--cyan);">${data.semantic_score}%</div>
        </div>
        <div style="background:rgba(255,255,255,0.03);padding:0.6rem;border-radius:var(--radius-sm);">
          <div style="color:var(--text-muted)">Keyword Score</div>
          <div style="font-weight:700;color:#a78bfa;">${data.keyword_score}%</div>
        </div>
        <div style="background:rgba(255,255,255,0.03);padding:0.6rem;border-radius:var(--radius-sm);">
          <div style="color:var(--text-muted)">Skill Coverage</div>
          <div style="font-weight:700;color:var(--green);">${data.skill_coverage}%</div>
        </div>
        <div style="background:rgba(255,255,255,0.03);padding:0.6rem;border-radius:var(--radius-sm);">
          <div style="color:var(--text-muted)">Missing Skills</div>
          <div style="font-weight:700;color:var(--red);">${(data.missing_skills || []).length}</div>
        </div>
      </div>`;
    showToast('XAI reasoning generated!', 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  }
}

// ─── ATS Score Page ───────────────────────────
function switchAtsTab(tab) {
  document.querySelectorAll('#page-ats .tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (i === 0 && tab === 'paste') || (i === 1 && tab === 'upload'));
  });
  document.getElementById('ats-paste-tab').classList.toggle('hidden', tab !== 'paste');
  document.getElementById('ats-upload-tab').classList.toggle('hidden', tab !== 'upload');
}

function loadAtsFile(e) {
  const file = e.target.files[0]; if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('ats-file-preview').value = ev.target.result;
    document.getElementById('ats-resume-input').value = ev.target.result;
  };
  reader.readAsText(file);
}

async function runAtsScore() {
  const pasteText  = document.getElementById('ats-resume-input').value.trim();
  const previewTxt = document.getElementById('ats-file-preview') ? document.getElementById('ats-file-preview').value.trim() : '';
  const resumeText = pasteText || previewTxt;
  const jdText     = document.getElementById('ats-jd-input').value.trim();
  if (!resumeText) { showToast('Please provide resume text.', 'error'); return; }

  const btn = document.getElementById('ats-btn');
  btn.innerHTML = '<div class="spinner"></div> Calculating...';
  btn.disabled  = true;
  showLoader('Calculating ATS compatibility score...');

  try {
    const res  = await fetch(API_BASE_URL + '/api/ats-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText, job_description: jdText })
    });
    const data = await res.json();
    hideLoader();
    renderAtsResults(data);
    showToast(`ATS Score: ${data.percentage}% (${data.grade})`, 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>&#128203;</span> Calculate ATS Score';
    btn.disabled  = false;
  }
}

function renderAtsResults(data) {
  const results = document.getElementById('ats-results');
  const gradeColors = { 'A+': '#10b981', A: '#00f5ff', B: '#7c3aed', C: '#fbbf24', D: '#ef4444' };
  const col = gradeColors[data.grade] || data.grade_color;

  document.getElementById('ats-grade-ring').innerHTML = `
    <div class="ats-score-circle" style="border-color:${col};box-shadow:0 0 30px ${col}33;">
      <div class="ats-score-number" style="color:${col}">${data.percentage}%</div>
      <div class="ats-score-grade" style="color:${col}">${data.grade}</div>
    </div>
    <div class="ats-score-label">ATS COMPATIBILITY</div>`;

  document.getElementById('ats-recommendation').textContent = data.recommendation;

  const breakdownEl = document.getElementById('ats-breakdown');
  breakdownEl.innerHTML = '';
  Object.entries(data.breakdown).forEach(([name, item]) => {
    const pct      = (item.score / item.max * 100).toFixed(0);
    const statusCls = item.ok ? 'criterion-ok' : item.score > 0 ? 'criterion-warn' : 'criterion-fail';
    const el = document.createElement('div');
    el.className = 'ats-criterion';
    el.innerHTML = `
      <div class="ats-criterion-header">
        <div class="ats-criterion-name ${statusCls}">${item.ok ? '&#9989;' : '&#9888;'} ${name}</div>
        <div class="ats-criterion-score ${statusCls}">${item.score}/${item.max}</div>
      </div>
      <div class="bar-track" style="height:6px"><div class="bar-fill" style="width:0%;height:100%;background:${item.ok?'var(--green)':'var(--yellow)'}" data-target="${pct}"></div></div>
      <div class="ats-criterion-status">${item.status}</div>
      <div class="ats-criterion-tip">${item.tip}</div>`;
    breakdownEl.appendChild(el);
  });

  results.classList.remove('hidden');
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('#ats-breakdown .bar-fill[data-target]').forEach(b => { b.style.width = b.dataset.target + '%'; });
  }));
}

// ─── Interview Questions Page ──────────────────
async function runInterviewQuestions() {
  const resumeText = document.getElementById('iq-resume-input').value.trim();
  const jdText     = document.getElementById('iq-jd-input').value.trim();
  if (!resumeText) { showToast('Please provide resume text.', 'error'); return; }

  const btn = document.getElementById('iq-btn');
  btn.innerHTML = '<div class="spinner"></div> Generating...';
  btn.disabled  = true;
  showLoader('Generating targeted interview questions...');

  try {
    const res  = await fetch(API_BASE_URL + '/api/interview-questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText, job_description: jdText })
    });
    const data = await res.json();
    hideLoader();
    renderInterviewQuestions(data);
    showToast(`Generated ${data.total_questions} interview questions!`, 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>&#127919;</span> Generate Interview Questions';
    btn.disabled  = false;
  }
}

function renderInterviewQuestions(data) {
  const results = document.getElementById('iq-results');

  document.getElementById('iq-summary').innerHTML = `
    <div class="iq-stat"><div class="iq-stat-val">${data.total_questions}</div><div class="iq-stat-label">Questions</div></div>
    <div class="iq-stat"><div class="iq-stat-val">${data.questions.length}</div><div class="iq-stat-label">Categories</div></div>
    <div class="iq-stat"><div class="iq-stat-val">${data.skills_analyzed}</div><div class="iq-stat-label">Skills Analyzed</div></div>
    <div style="margin-left:auto;font-size:0.82rem;color:var(--text-secondary);">Questions are tailored to the candidate's skill level and matched job requirements.</div>`;

  const listEl = document.getElementById('iq-questions-list');
  listEl.innerHTML = '';
  data.questions.forEach((cat, i) => {
    const card = document.createElement('div');
    card.className = 'iq-category-card';
    card.style.animationDelay = `${i * 0.08}s`;
    card.innerHTML = `
      <div class="iq-category-header">
        <div class="iq-category-name">${cat.category}</div>
        <div class="iq-difficulty">${cat.difficulty}</div>
      </div>
      <div class="iq-skill-tag">${cat.skill_matched}</div>
      ${cat.questions.map(q => `<div class="iq-question">${q}</div>`).join('')}`;
    listEl.appendChild(card);
  });

  results.classList.remove('hidden');
}

// ─── Fraud Detection Page ─────────────────────
async function runFraudDetect() {
  const resumeText = document.getElementById('fraud-resume-input').value.trim();
  if (!resumeText) { showToast('Please provide resume text.', 'error'); return; }

  const btn = document.getElementById('fraud-btn');
  btn.innerHTML = '<div class="spinner"></div> Analyzing...';
  btn.disabled  = true;
  showLoader('Running fraud & anomaly detection...');

  try {
    const res  = await fetch(API_BASE_URL + '/api/fraud-detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText })
    });
    const data = await res.json();
    hideLoader();
    renderFraudResults(data);
    showToast(`Risk Level: ${data.risk_level}`, data.risk_score >= 50 ? 'error' : 'info');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>&#128737;</span> Run Fraud Analysis';
    btn.disabled  = false;
  }
}

function renderFraudResults(data) {
  const results   = document.getElementById('fraud-results');
  const scoreMain = document.getElementById('fraud-score-main');
  const riskColor = data.risk_color || (data.risk_score >= 50 ? '#ef4444' : data.risk_score >= 25 ? '#fbbf24' : '#10b981');

  scoreMain.innerHTML = `
    <div class="fraud-risk-badge" style="color:${riskColor};border-color:${riskColor};background:${riskColor}22;">${data.risk_level}</div>
    <div class="fraud-risk-score" style="color:${riskColor}">${data.risk_score}<span style="font-size:1.5rem">/100</span></div>
    <div class="fraud-risk-label">Fraud Risk Score</div>
    <div style="margin-top:1rem;">
      <div class="bar-track" style="height:8px;border-radius:999px;overflow:hidden;max-width:200px;margin:0 auto;">
        <div class="bar-fill" style="width:0%;height:100%;background:${riskColor};border-radius:999px;" data-target="${data.risk_score}"></div>
      </div>
    </div>
    <div style="margin-top:0.75rem;font-size:0.82rem;color:var(--text-secondary);">${data.flags_count} flag(s) detected</div>`;

  const flagsEl = document.getElementById('fraud-flags-list');
  flagsEl.innerHTML = '';
  if (data.flags && data.flags.length > 0) {
    data.flags.forEach((flag, i) => {
      const el = document.createElement('div');
      el.className = `fraud-flag-card ${flag.severity}`;
      el.style.animationDelay = `${i * 0.08}s`;
      el.innerHTML = `
        <div class="fraud-flag-icon">${flag.icon}</div>
        <div style="flex:1">
          <div class="fraud-flag-title">${flag.type}<span class="fraud-severity sev-${flag.severity}">${flag.severity}</span></div>
          <div class="fraud-flag-detail">${flag.detail}</div>
        </div>`;
      flagsEl.appendChild(el);
    });
  } else {
    flagsEl.innerHTML = '<div class="fraud-flag-card" style="border-color:rgba(16,185,129,0.3);"><div class="fraud-flag-icon">&#9989;</div><div style="flex:1"><div class="fraud-flag-title">No Flags Detected</div><div class="fraud-flag-detail">Resume appears authentic with no anomaly indicators.</div></div></div>';
  }

  const recEl = document.getElementById('fraud-recommendation');
  recEl.classList.remove('hidden');
  recEl.innerHTML = `<strong>HR Recommendation:</strong> ${data.recommendation}`;

  results.classList.remove('hidden');
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('#fraud-results .bar-fill[data-target]').forEach(b => {
      b.style.transition = 'width 1s ease';
      b.style.width = b.dataset.target + '%';
    });
  }));
}

// ─── Job Recommendations Page ─────────────────
async function runJobRecommendations() {
  const resumeText = document.getElementById('jobs-resume-input').value.trim();
  const jdText     = document.getElementById('jobs-jd-input').value.trim();
  if (!resumeText) { showToast('Please provide resume text.', 'error'); return; }

  const btn = document.getElementById('jobs-btn');
  btn.innerHTML = '<div class="spinner"></div> Loading...';
  btn.disabled  = true;
  showLoader('Generating job recommendations...');

  try {
    // Run both API calls in parallel
    const [jobRes, langRes] = await Promise.all([
      fetch(API_BASE_URL + '/api/job-recommendations', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resumeText, job_description: jdText })
      }),
      fetch(API_BASE_URL + '/api/detect-language', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resumeText })
      })
    ]);

    const jobData  = await jobRes.json();
    const langData = await langRes.json();
    hideLoader();

    renderJobRecommendations(jobData, langData);
    showToast(`Found ${jobData.recommendations.length} job matches!`, 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>&#128188;</span> Get Job Recommendations';
    btn.disabled  = false;
  }
}

function renderJobRecommendations(data, langData) {
  const results = document.getElementById('jobs-results');

  // Profile card
  document.getElementById('jobs-profile-card').innerHTML = `
    <div class="jobs-profile-header">
      <div class="jobs-profile-avatar">&#128100;</div>
      <div>
        <div class="jobs-profile-name">${data.candidate_category} Professional</div>
        <div class="jobs-profile-meta">${data.experience_years} years experience &bull; ML Confidence: ${data.ml_confidence}%</div>
      </div>
      <div style="margin-left:auto;text-align:right;">
        <div style="font-size:0.75rem;color:var(--text-muted)">Category</div>
        <div style="font-weight:700;color:var(--cyan);">${data.candidate_category}</div>
      </div>
    </div>`;

  // Job list
  const listEl = document.getElementById('jobs-list');
  listEl.innerHTML = `<div style="font-size:0.82rem;color:var(--text-secondary);margin:1rem 0 0.5rem;font-weight:600;">Recommended Job Titles</div>`;
  data.recommendations.forEach((job, i) => {
    const el = document.createElement('div');
    el.className = 'job-rec-card';
    el.style.animationDelay = `${i * 0.07}s`;
    el.innerHTML = `
      <div class="job-rank-circle">#${i+1}</div>
      <div class="job-rec-info">
        <div class="job-rec-title">${job.title}</div>
        <div class="job-rec-companies">${(job.companies || []).join(' &bull; ')}</div>
      </div>
      <span class="job-level-badge">${job.level}</span>
      <div class="job-rec-match">${job.match}%</div>`;
    listEl.appendChild(el);
  });

  // Language detection card
  const langEl = document.getElementById('lang-detect-card');
  langEl.classList.remove('hidden');
  langEl.innerHTML = `
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
      <div>
        <div style="font-size:1.5rem">${langData.flag}</div>
      </div>
      <div>
        <div style="font-weight:700;">${langData.language} Detected</div>
        <div style="font-size:0.82rem;color:var(--text-secondary);">${langData.processing_note}</div>
      </div>
      <div style="margin-left:auto;text-align:right;">
        <div style="font-size:0.75rem;color:var(--text-muted)">Confidence</div>
        <div style="font-weight:700;color:var(--cyan);">${langData.confidence}%</div>
      </div>
      ${langData.translation_needed ? '<span class="badge badge-consider">Translation Recommended</span>' : '<span class="badge badge-high">English Resume</span>'}
    </div>`;

  results.classList.remove('hidden');
}

// ─── ML Metrics ───────────────────────────────
async function loadMetrics() {
  try {
    const res  = await fetch(API_BASE_URL + '/api/model-metrics');
    const data = await res.json();

    const noData  = document.getElementById('metrics-no-data');
    const content = document.getElementById('metrics-content');

    if (!data.available) {
      noData.classList.remove('hidden');
      content.classList.add('hidden');
      return;
    }

    noData.classList.add('hidden');
    content.classList.remove('hidden');

    const rf = data.rf, gb = data.gb;
    document.getElementById('rf-accuracy').textContent = (rf.accuracy * 100).toFixed(2) + '%';
    document.getElementById('gb-accuracy').textContent = (gb.accuracy * 100).toFixed(2) + '%';
    document.getElementById('rf-time').textContent = `Training: ${rf.train_time_seconds.toFixed(2)}s`;
    document.getElementById('gb-time').textContent = `Training: ${gb.train_time_seconds.toFixed(2)}s`;

    renderClassificationReport('rf-report', rf.report);
    renderClassificationReport('gb-report', gb.report);
    renderConfusionMatrix('rf-matrix', rf.confusion_matrix, data.categories);
    renderConfusionMatrix('gb-matrix', gb.confusion_matrix, data.categories);
  } catch(e) { console.warn('Could not load metrics:', e); }
}

function renderClassificationReport(containerId, report) {
  const el   = document.getElementById(containerId);
  const keys = Object.keys(report).filter(k => !['accuracy','macro avg','weighted avg'].includes(k)).concat(['macro avg','weighted avg']);
  el.innerHTML = `
    <table>
      <thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1-Score</th><th>Support</th></tr></thead>
      <tbody>
        ${keys.filter(k => report[k]).map(k => `
          <tr>
            <td>${k}</td>
            <td>${(report[k].precision*100||0).toFixed(1)}%</td>
            <td>${(report[k].recall*100||0).toFixed(1)}%</td>
            <td>${(report[k]['f1-score']*100||0).toFixed(1)}%</td>
            <td>${report[k].support||'—'}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderConfusionMatrix(containerId, matrix, categories) {
  const el = document.getElementById(containerId);
  if (!matrix || !categories) return;
  el.innerHTML = `
    <table>
      <thead><tr><th></th>${categories.map(c=>`<th>${c}</th>`).join('')}</tr></thead>
      <tbody>
        ${matrix.map((row, i) => `<tr><th>${categories[i]}</th>${row.map((v,j)=>`<td class="${i===j?'diag':''}">${v}</td>`).join('')}</tr>`).join('')}
      </tbody>
    </table>`;
}

function switchMetricsTab(tab) {
  ['rf','gb'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`metrics-tab-${t}`).classList.toggle('hidden', t !== tab);
  });
}

// ─── Loader & Toast ───────────────────────────
function showLoader(text = 'Processing...') {
  document.getElementById('loader-text').textContent = text;
  document.getElementById('loading-overlay').classList.remove('hidden');
}
function hideLoader() { document.getElementById('loading-overlay').classList.add('hidden'); }

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast     = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ─── Init ─────────────────────────────────────
fetchDatasetInfo();

// ─── Animate Count helper (used by updateHeroStats) ──────
function animateCount(containerId, selector, target, suffix) {
  const el = document.querySelector(`#${containerId} ${selector}`);
  if (!el) return;
  const start = 0;
  const duration = 1200;
  const startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(start + (target - start) * ease) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ─── Upload ───────────────────────────────────
(function initUpload() {
  const zone  = document.getElementById('upload-zone');
  const input = document.getElementById('csv-file-input');

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleCsvUpload(file);
  });

  input.addEventListener('change', () => {
    if (input.files[0]) handleCsvUpload(input.files[0]);
  });
})();

async function handleCsvUpload(file) {
  if (!file.name.endsWith('.csv')) {
    showToast('Please upload a .csv file.', 'error');
    return;
  }

  // Show progress
  const prog = document.getElementById('upload-progress');
  const fill = document.getElementById('progress-fill');
  const msg  = document.getElementById('upload-status-msg');
  const result = document.getElementById('upload-result');
  result.classList.add('hidden');
  prog.classList.remove('hidden');

  // Animate progress bar
  let pct = 0;
  const interval = setInterval(() => {
    pct = Math.min(pct + Math.random() * 15, 85);
    fill.style.width = pct + '%';
  }, 150);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res  = await fetch(API_BASE_URL + '/api/upload-dataset', { method: 'POST', body: formData });
    const data = await res.json();

    clearInterval(interval);
    fill.style.width = '100%';

    await new Promise(r => setTimeout(r, 400));
    prog.classList.add('hidden');

    if (!res.ok) {
      showToast(data.detail || 'Upload failed.', 'error');
      return;
    }

    document.getElementById('upload-success-title').textContent = '✅ Dataset Loaded!';
    document.getElementById('upload-success-msg').textContent   = data.message;
    result.classList.remove('hidden');
    showToast(data.message, 'success');

    // Refresh dataset info globally
    await fetchDatasetInfo();
    populateCategoryFilter();
  } catch(e) {
    clearInterval(interval);
    prog.classList.add('hidden');
    showToast('Upload error: ' + e.message, 'error');
  }
}

// ─── Analytics ────────────────────────────────
async function loadAnalytics() {
  if (!_datasetInfo) await fetchDatasetInfo();

  const noData = document.getElementById('analytics-no-data');
  const content = document.getElementById('analytics-content');

  if (!_datasetInfo || !_datasetInfo.loaded) {
    noData.classList.remove('hidden');
    content.classList.add('hidden');
    return;
  }

  noData.classList.add('hidden');
  content.classList.remove('hidden');

  // Animate metric counters
  animateCount('m-total', '', _datasetInfo.total, '');
  document.getElementById('m-total').textContent = _datasetInfo.total.toLocaleString();
  document.getElementById('m-exp').textContent   = _datasetInfo.avg_exp + ' yrs';
  document.getElementById('m-cats').textContent  = Object.keys(_datasetInfo.categories || {}).length;

  // Category chart
  const cats = _datasetInfo.categories || {};
  const catMax = Math.max(...Object.values(cats), 1);
  const catContainer = document.getElementById('cat-chart');
  catContainer.innerHTML = '';
  Object.entries(cats).sort((a, b) => b[1] - a[1]).slice(0, 10).forEach(([label, count], i) => {
    const pct = (count / catMax * 100).toFixed(1);
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <span class="bar-label">${label}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:0%;transition-delay:${i*0.1}s" data-target="${pct}"></div>
      </div>
      <span class="bar-count">${count.toLocaleString()}</span>`;
    catContainer.appendChild(row);
  });

  // Experience bands chart
  const bands = _datasetInfo.exp_bands || {};
  const expMax = Math.max(...Object.values(bands), 1);
  const expContainer = document.getElementById('exp-chart');
  expContainer.innerHTML = '';
  const expColors = ['#00f5ff','#7c3aed','#f472b6','#10b981','#fbbf24'];
  Object.entries(bands).forEach(([label, count], i) => {
    const pct = (count / expMax * 100).toFixed(1);
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <span class="bar-label">${label}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width:0%;background:linear-gradient(90deg,${expColors[i]},${expColors[(i+1)%expColors.length]});transition-delay:${i*0.1}s" data-target="${pct}"></div>
      </div>
      <span class="bar-count">${count.toLocaleString()}</span>`;
    expContainer.appendChild(row);
  });

  // Animate bars after a tick
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.querySelectorAll('.bar-fill[data-target]').forEach(bar => {
        bar.style.width = bar.dataset.target + '%';
      });
    });
  });
}

// ─── Category Filter ──────────────────────────
async function populateCategoryFilter() {
  if (!_datasetInfo) await fetchDatasetInfo();
  const select = document.getElementById('cat-filter');
  if (!select) return;
  const cats = _datasetInfo ? Object.keys(_datasetInfo.categories || {}) : [];
  select.innerHTML = '<option value="All">All Categories</option>';
  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    select.appendChild(opt);
  });
}

// ─── JD Templates ─────────────────────────────
function applyJdTemplate() {
  const val = document.getElementById('jd-template').value;
  if (val && JD_TEMPLATES[val]) document.getElementById('jd-input').value = JD_TEMPLATES[val];
}
function applyResumeJdTemplate() {
  const val = document.getElementById('resume-jd-template').value;
  if (val && JD_TEMPLATES[val]) document.getElementById('resume-jd-input').value = JD_TEMPLATES[val];
}

// ─── Screening ────────────────────────────────
async function runScreening() {
  const jd = document.getElementById('jd-input').value.trim();
  if (!jd) { showToast('Please enter a job description.', 'error'); return; }

  const btn = document.getElementById('screen-btn');
  btn.innerHTML = '<div class="spinner"></div> Processing...';
  btn.disabled = true;

  showLoader('Running NLP & BERT Screening...');

  try {
    const res = await fetch(API_BASE_URL + '/api/screen', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_description: jd,
        algorithm: document.getElementById('algo-select').value,
        filter_category: document.getElementById('cat-filter').value,
        min_exp: parseInt(document.getElementById('exp-slider').value),
        max_results: parseInt(document.getElementById('max-results').value),
      })
    });
    const data = await res.json();
    hideLoader();

    if (!res.ok) { showToast(data.detail, 'error'); return; }

    _screenResults = data.results;
    renderLeaderboard(data);
    showToast(`✅ Screened ${data.total_screened.toLocaleString()} candidates in ${data.time_seconds}s`, 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>🚀</span> Screen Candidates';
    btn.disabled = false;
  }
}

function renderLeaderboard(data) {
  const wrapper = document.getElementById('screen-results');
  const header  = document.getElementById('results-header');
  const board   = document.getElementById('leaderboard');

  const bertNote = data.used_bert
    ? '🤖 BERT semantic embeddings used'
    : '📊 TF-IDF cosine similarity used (BERT fallback)';

  header.innerHTML = `
    <strong>Top ${data.results.length}</strong> of ${data.total_screened.toLocaleString()} candidates screened in
    <strong>${data.time_seconds}s</strong> &nbsp;|&nbsp; ${bertNote}`;

  board.innerHTML = '';

  data.results.forEach((c, i) => {
    const badgeClass = c.recommendation === 'Highly Recommended'    ? 'badge-high'
                     : c.recommendation === 'Consider for Interview' ? 'badge-consider'
                     : 'badge-not';
    const badgeText = c.recommendation === 'Highly Recommended'    ? '🟢 Highly Recommended'
                    : c.recommendation === 'Consider for Interview' ? '🟡 Consider'
                    : '🔴 Not a Fit';

    const matchedSkillsHtml = (c.matched_skills || []).slice(0, 4)
      .map(s => `<span class="skill-pill skill-matched">${s}</span>`).join('');
    const missingSkillsHtml = (c.missing_skills || []).slice(0, 4)
      .map(s => `<span class="skill-pill skill-missing">${s}</span>`).join('');

    const card = document.createElement('div');
    card.className = 'candidate-card';
    card.style.animationDelay = `${i * 0.05}s`;
    card.dataset.candidateIdx = i;

    const isRec = _hrShortlist.some(h => h.email === c.email && h.name === c.name);
    const recBtnId = `rec-hr-btn-${i}`;

    card.innerHTML = `
      <div class="candidate-header">
        <div class="rank-badge">#${i+1}</div>
        <div class="candidate-name">${c.name}</div>
        <div class="candidate-score">${c.score}%</div>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="score-bar-mini">
        <div class="score-bar-fill" style="width:0%" data-target="${c.score}"></div>
      </div>
      <div class="candidate-meta">
        <span>📧 ${c.email || '—'}</span>
        <span>📅 ${c.experience_years} yrs exp</span>
        <span>🏷️ ${c.category}</span>
        <span>🎓 ${c.education_degree || '—'}</span>
      </div>
      ${matchedSkillsHtml || missingSkillsHtml ? `
      <div style="margin-top:0.5rem;">
        ${matchedSkillsHtml}${missingSkillsHtml}
      </div>` : ''}
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.6rem;">
        <button id="${recBtnId}" class="btn-recommend-hr ${isRec ? 'recommended' : ''}" onclick="toggleHrRecommend(${i})">
          ${isRec ? '✅ Recommended to HR' : '📋 Recommend to HR'}
        </button>
        <span data-hr-added-tag style="font-size:0.74rem;color:var(--green);">${isRec ? 'Added to shortlist' : ''}</span>
      </div>`;
    board.appendChild(card);
  });

  wrapper.classList.remove('hidden');

  // Animate score bars
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('.score-bar-fill[data-target]').forEach(bar => {
      bar.style.transition = 'width 1s cubic-bezier(0.4,0,0.2,1)';
      bar.style.width = bar.dataset.target + '%';
    });
  }));
}

function exportCSV() {
  if (!_screenResults.length) return;
  const headers = Object.keys(_screenResults[0]).join(',');
  const rows = _screenResults.map(r => Object.values(r).map(v => `"${String(v).replace(/"/g,'""')}"`).join(','));
  const blob = new Blob([headers + '\n' + rows.join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'resume_screened_results.csv';
  a.click();
}

// ─── Single Resume ────────────────────────────
function switchResumeTab(tab) {
  document.querySelectorAll('#page-resume .tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (i === 0 && tab === 'paste') || (i === 1 && tab === 'upload'));
  });
  document.getElementById('resume-paste-tab').classList.toggle('hidden', tab !== 'paste');
  document.getElementById('resume-upload-tab').classList.toggle('hidden', tab !== 'upload');
}

function loadResumeFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('resume-file-preview').value = ev.target.result;
    document.getElementById('resume-text-input').value   = ev.target.result;
  };
  reader.readAsText(file);
}

async function analyzeResume() {
  const pasteText  = document.getElementById('resume-text-input').value.trim();
  const previewTxt = document.getElementById('resume-file-preview').value.trim();
  const resumeText = pasteText || previewTxt;
  const jdText     = document.getElementById('resume-jd-input').value.trim();

  if (!resumeText) { showToast('Please provide resume text.', 'error'); return; }

  const btn = document.getElementById('analyze-btn');
  btn.innerHTML = '<div class="spinner"></div> Analyzing...';
  btn.disabled = true;
  showLoader('Analyzing resume with NLP & ML...');

  try {
    const res = await fetch(API_BASE_URL + '/api/analyze-resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: resumeText, job_description: jdText })
    });
    const data = await res.json();
    hideLoader();

    if (!res.ok) { showToast(data.detail, 'error'); return; }

    renderResumeResults(data);
    showToast('✅ Resume analyzed successfully!', 'success');
  } catch(e) {
    hideLoader();
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.innerHTML = '<span>🔮</span> Analyze Resume';
    btn.disabled = false;
  }
}

function renderResumeResults(data) {
  const p = data.parsed;

  // Parsed grid
  document.getElementById('parsed-grid').innerHTML = `
    <div class="parsed-item"><span>Name:</span> ${p.name}</div>
    <div class="parsed-item"><span>Email:</span> ${p.email}</div>
    <div class="parsed-item"><span>Phone:</span> ${p.phone}</div>
    <div class="parsed-item"><span>Experience:</span> ${p.experience_years} years</div>
    <div class="parsed-item" style="grid-column:1/-1"><span>Education:</span> ${p.education}</div>`;

  // ML predictions
  document.getElementById('ml-predictions').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
      <div class="glass-card" style="padding:1rem;text-align:center;">
        <div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:0.4rem;">🌲 Random Forest</div>
        <div style="font-weight:700;color:var(--cyan);margin-bottom:0.3rem;">${data.rf_category}</div>
        <div style="font-size:0.82rem;color:var(--text-secondary)">${data.rf_confidence}% confidence</div>
        <div class="score-bar-mini" style="margin-top:0.5rem;"><div class="score-bar-fill" data-target="${data.rf_confidence}" style="width:0%;background:linear-gradient(90deg,#10b981,#00f5ff)"></div></div>
      </div>
      <div class="glass-card" style="padding:1rem;text-align:center;">
        <div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:0.4rem;">⚡ Gradient Boost</div>
        <div style="font-weight:700;color:#a78bfa;margin-bottom:0.3rem;">${data.gb_category}</div>
        <div style="font-size:0.82rem;color:var(--text-secondary)">${data.gb_confidence}% confidence</div>
        <div class="score-bar-mini" style="margin-top:0.5rem;"><div class="score-bar-fill" data-target="${data.gb_confidence}" style="width:0%;background:linear-gradient(90deg,#fbbf24,#f472b6)"></div></div>
      </div>
    </div>`;

  // Match scores
  const matchCard = document.getElementById('match-score-card');
  if (data.match_scores) {
    const ms = data.match_scores;
    const recClass = data.recommendation === 'Highly Recommended' ? 'badge-high'
                   : data.recommendation === 'Consider for Interview' ? 'badge-consider' : 'badge-not';
    const recText = data.recommendation === 'Highly Recommended' ? '🟢 Highly Recommended'
                  : data.recommendation === 'Consider for Interview' ? '🟡 Consider for Interview' : '🔴 Not a Fit';

    matchCard.innerHTML = `
      <h3>📊 Match Score</h3>
      <div class="score-ring-container">
        <div class="score-ring">
          <svg viewBox="0 0 120 120">
            <defs>
              <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#00f5ff"/>
                <stop offset="100%" stop-color="#7c3aed"/>
              </linearGradient>
            </defs>
            <circle class="score-ring-bg" cx="60" cy="60" r="52"/>
            <circle class="score-ring-fill" cx="60" cy="60" r="52"
              stroke-dasharray="${2*Math.PI*52}" stroke-dashoffset="${2*Math.PI*52*(1-ms.hybrid/100)}"/>
          </svg>
          <div class="score-ring-text">
            <span class="score-ring-val">${ms.hybrid}%</span>
            <span class="score-ring-sub">Hybrid</span>
          </div>
        </div>
        <span class="badge ${recClass}">${recText}</span>
      </div>
      <div class="score-bars">
        ${scoreBarRow('Semantic (BERT/TF-IDF)', ms.semantic, '#00f5ff')}
        ${scoreBarRow('Keyword Skills Match',    ms.keyword,  '#7c3aed')}
      </div>
      <div style="margin-top:1rem">
        <div style="font-size:0.82rem;color:var(--text-secondary);margin-bottom:0.4rem">✅ Matched Skills</div>
        <div>${(ms.matched_skills||[]).map(s=>`<span class="skill-pill skill-matched">${s}</span>`).join('') || '<span style="color:var(--text-muted)">None</span>'}</div>
        <div style="font-size:0.82rem;color:var(--text-secondary);margin:0.6rem 0 0.4rem">❌ Missing Skills</div>
        <div>${(ms.missing_skills||[]).map(s=>`<span class="skill-pill skill-missing">${s}</span>`).join('') || '<span style="color:var(--text-muted)">None</span>'}</div>
      </div>`;
    matchCard.classList.remove('hidden');
  } else {
    matchCard.innerHTML = '<h3>📊 Match Score</h3><p style="color:var(--text-secondary);font-size:0.88rem">No job description provided. Add one to see a match score.</p>';
  }

  // Extracted skills
  const skills = p.skills || [];
  document.getElementById('extracted-skills').innerHTML = skills.length
    ? skills.map(s => `<span class="skill-pill skill-matched">${s}</span>`).join('')
    : '<span style="color:var(--text-secondary)">No skills identified.</span>';

  document.getElementById('resume-results').classList.remove('hidden');

  // Animate mini bars
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('.score-bar-fill[data-target]').forEach(bar => {
      bar.style.transition = 'width 1s ease';
      bar.style.width = bar.dataset.target + '%';
    });
  }));
}

function scoreBarRow(label, value, color) {
  return `
    <div class="score-bar-row">
      <div class="score-bar-header">
        <span class="score-bar-label">${label}</span>
        <span class="score-bar-value" style="color:${color}">${value}%</span>
      </div>
      <div class="bar-track"><div class="bar-fill" data-target="${value}" style="width:0%;background:linear-gradient(90deg,${color},var(--purple))"></div></div>
    </div>`;
}

// ─── ML Metrics ───────────────────────────────
async function loadMetrics() {
  try {
    const res  = await fetch(API_BASE_URL + '/api/model-metrics');
    const data = await res.json();

    const noData  = document.getElementById('metrics-no-data');
    const content = document.getElementById('metrics-content');

    if (!data.available) {
      noData.classList.remove('hidden');
      content.classList.add('hidden');
      return;
    }

    noData.classList.add('hidden');
    content.classList.remove('hidden');

    const rf = data.rf;
    const gb = data.gb;

    document.getElementById('rf-accuracy').textContent = (rf.accuracy * 100).toFixed(2) + '%';
    document.getElementById('gb-accuracy').textContent = (gb.accuracy * 100).toFixed(2) + '%';
    document.getElementById('rf-time').textContent = `⏱ Training: ${rf.train_time_seconds.toFixed(2)}s`;
    document.getElementById('gb-time').textContent = `⏱ Training: ${gb.train_time_seconds.toFixed(2)}s`;

    renderClassificationReport('rf-report', rf.report);
    renderClassificationReport('gb-report', gb.report);
    renderConfusionMatrix('rf-matrix', rf.confusion_matrix, data.categories);
    renderConfusionMatrix('gb-matrix', gb.confusion_matrix, data.categories);
  } catch(e) {
    console.warn('Could not load metrics:', e);
  }
}

function renderClassificationReport(containerId, report) {
  const el = document.getElementById(containerId);
  const keys = Object.keys(report).filter(k => !['accuracy','macro avg','weighted avg'].includes(k)).concat(['macro avg','weighted avg']);
  el.innerHTML = `
    <table>
      <thead><tr>
        <th>Class</th><th>Precision</th><th>Recall</th><th>F1-Score</th><th>Support</th>
      </tr></thead>
      <tbody>
        ${keys.filter(k => report[k]).map(k => `
          <tr>
            <td>${k}</td>
            <td>${(report[k].precision*100||0).toFixed(1)}%</td>
            <td>${(report[k].recall*100||0).toFixed(1)}%</td>
            <td>${(report[k]['f1-score']*100||0).toFixed(1)}%</td>
            <td>${report[k].support||'—'}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderConfusionMatrix(containerId, matrix, categories) {
  const el = document.getElementById(containerId);
  if (!matrix || !categories) return;
  el.innerHTML = `
    <table>
      <thead><tr><th></th>${categories.map(c=>`<th>${c}</th>`).join('')}</tr></thead>
      <tbody>
        ${matrix.map((row, i) => `<tr><th>${categories[i]}</th>${row.map((v,j)=>`<td class="${i===j?'diag':''}">${v}</td>`).join('')}</tr>`).join('')}
      </tbody>
    </table>`;
}

function switchMetricsTab(tab) {
  ['rf','gb'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`metrics-tab-${t}`).classList.toggle('hidden', t !== tab);
  });
}

// ─── Loader & Toast ───────────────────────────
function showLoader(text = 'Processing...') {
  document.getElementById('loader-text').textContent = text;
  document.getElementById('loading-overlay').classList.remove('hidden');
}
function hideLoader() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ═══════════════════════════════════════════════════════
// MODULE 3 — Recommend to HR
// Manages the HR shortlist, slide-over panel, report & CSV
// ═══════════════════════════════════════════════════════

let _hrShortlist   = [];   // Array of {candidate, note, rank, addedAt}
let _hrReportData  = null; // Last generated report for download

// ── Toggle a candidate into/out of HR shortlist ──────────
function toggleHrRecommend(cardIdx) {
  const c = _screenResults[cardIdx];
  if (!c) return;

  const existIdx = _hrShortlist.findIndex(h => h.email === c.email && h.name === c.name);
  if (existIdx >= 0) {
    // Remove
    _hrShortlist.splice(existIdx, 1);
    showToast(`${c.name} removed from HR shortlist.`, 'info');
  } else {
    // Add
    _hrShortlist.push({
      candidate: { ...c },
      note: '',
      rank: cardIdx + 1,
      addedAt: new Date().toLocaleTimeString()
    });
    showToast(`✅ ${c.name} recommended to HR!`, 'success');
  }

  updateHrBadge();
  refreshLeaderboardHrButtons();
  renderHrCandidateList();
}

// ── Refresh Recommend buttons on all cards (after add/remove) ─
function refreshLeaderboardHrButtons() {
  _screenResults.forEach((c, i) => {
    const btn = document.getElementById(`rec-hr-btn-${i}`);
    if (!btn) return;
    const isRec = _hrShortlist.some(h => h.email === c.email && h.name === c.name);
    btn.className = `btn-recommend-hr ${isRec ? 'recommended' : ''}`;
    btn.textContent = isRec ? '✅ Recommended to HR' : '📋 Recommend to HR';
    const card = btn.closest('.candidate-card');
    if (card) {
      const tag = card.querySelector('[data-hr-added-tag]');
      if (tag) tag.textContent = isRec ? 'Added to shortlist' : '';
    }
  });
}

// ── Update floating badge visibility and count ────────────
function updateHrBadge() {
  const badge  = document.getElementById('hr-shortlist-badge');
  const count  = document.getElementById('hr-badge-count');
  const sendBtn = document.getElementById('send-to-hr-btn');
  const n = _hrShortlist.length;
  badge.style.display  = n > 0 ? 'flex' : 'none';
  count.textContent    = n;
  if (sendBtn) sendBtn.disabled = n === 0;
  document.getElementById('hr-shortlist-count').textContent = n;
  // Also update the HR page count text
  const pageCount = document.getElementById('hr-page-count');
  if (pageCount) {
    pageCount.textContent = n > 0
      ? `${n} candidate(s) in shortlist — ready to send to HR.`
      : 'No candidates added yet. Run a screening first.';
  }
}

// ── Render HR candidate list in side panel ────────────────
function renderHrCandidateList() {
  const list   = document.getElementById('hr-candidates-list');
  const empty  = document.getElementById('hr-empty-state');
  const jdEl   = document.getElementById('hr-jd-title-display');
  const jdInput = document.getElementById('jd-input');

  if (jdEl && jdInput) {
    const jd = jdInput.value.trim();
    jdEl.textContent = jd ? jd.split('\n')[0].slice(0, 55) + (jd.length > 55 ? '...' : '') : 'General Position';
  }

  if (_hrShortlist.length === 0) {
    list.innerHTML = '';
    if (empty) list.appendChild(empty);
    empty.style.display = 'flex';
    return;
  }
  if (empty) empty.style.display = 'none';

  // Keep only non-empty-state children, rebuild
  const existingItems = list.querySelectorAll('.hr-candidate-item');
  existingItems.forEach(el => el.remove());

  _hrShortlist.forEach((item, i) => {
    const c    = item.candidate;
    const el   = document.createElement('div');
    el.className = 'hr-candidate-item';
    el.innerHTML = `
      <div class="hr-rank-orb">#${item.rank}</div>
      <div style="flex:1;min-width:0">
        <div class="hr-cand-name">${c.name}</div>
        <div class="hr-cand-meta">${c.email || '—'} &bull; ${c.experience_years} yrs &bull; ${c.category}</div>
        <div class="hr-cand-meta" style="margin-top:0.15rem;">
          <span class="badge ${c.recommendation === 'Highly Recommended' ? 'badge-high' : c.recommendation === 'Consider for Interview' ? 'badge-consider' : 'badge-not'}" style="font-size:0.7rem;padding:0.1rem 0.45rem;">${c.recommendation || '—'}</span>
          &nbsp;<span style="color:var(--text-muted);font-size:0.74rem;">Added ${item.addedAt}</span>
        </div>
        <textarea class="hr-note-input" rows="2" placeholder="Add recruiter note (optional)..."
          onchange="_hrShortlist[${i}].note = this.value">${item.note}</textarea>
      </div>
      <div class="hr-cand-score">${c.score}%</div>
      <button class="hr-remove-btn" onclick="removeFromHrShortlist(${i})" title="Remove">✕</button>`;
    list.appendChild(el);
  });
}

// ── Remove individual item ────────────────────────────────
function removeFromHrShortlist(idx) {
  const name = _hrShortlist[idx]?.candidate?.name || 'Candidate';
  _hrShortlist.splice(idx, 1);
  updateHrBadge();
  renderHrCandidateList();
  refreshLeaderboardHrButtons();
  showToast(`${name} removed.`, 'info');
}

// ── Clear full shortlist ──────────────────────────────────
function clearHrShortlist() {
  if (!_hrShortlist.length) return;
  _hrShortlist = [];
  updateHrBadge();
  renderHrCandidateList();
  refreshLeaderboardHrButtons();
  showToast('HR shortlist cleared.', 'info');
}

// ── Open / close HR panel ─────────────────────────────────
function openHrPanel() {
  renderHrCandidateList();
  const overlay = document.getElementById('hr-panel-overlay');
  const panel   = document.getElementById('hr-panel');
  overlay.style.display = 'flex';
  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    panel.classList.add('slide-in');
  });
}

function closeHrPanel() {
  const overlay = document.getElementById('hr-panel-overlay');
  const panel   = document.getElementById('hr-panel');
  overlay.classList.remove('visible');
  panel.classList.remove('slide-in');
  setTimeout(() => { overlay.style.display = 'none'; }, 300);
}

// ── Send to HR — API call + show report ──────────────────
async function sendToHR() {
  if (!_hrShortlist.length) {
    showToast('Add at least one candidate to the shortlist first.', 'error');
    return;
  }

  const btn = document.getElementById('send-to-hr-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Sending...';

  const jdText   = document.getElementById('jd-input')?.value.trim() || '';
  const jdTitle  = jdText ? jdText.split('\n')[0].slice(0, 80) : 'General Position';

  const payload = {
    candidates: _hrShortlist.map((item, i) => ({
      rank:         item.rank,
      name:         item.candidate.name,
      email:        item.candidate.email || '—',
      score:        item.candidate.score,
      experience_years: item.candidate.experience_years,
      category:     item.candidate.category,
      education:    item.candidate.education_degree || '—',
      recommendation: item.candidate.recommendation || '—',
      matched_skills: item.candidate.matched_skills || [],
      missing_skills: item.candidate.missing_skills || [],
      note:         item.note || ''
    })),
    job_title:    jdTitle,
    job_description: jdText
  };

  try {
    const res  = await fetch(API_BASE_URL + '/api/recommend-to-hr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    _hrReportData = { ...data, payload };
    closeHrPanel();
    showHrReport(data, payload);
    showToast(`✅ ${_hrShortlist.length} candidates sent to HR successfully!`, 'success');
  } catch(e) {
    showToast('Error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '📤 Send to HR';
  }
}

// ── Render HR Report Modal ────────────────────────────────
function showHrReport(data, payload) {
  const modal   = document.getElementById('hr-report-modal');
  const body    = document.getElementById('hr-report-body');
  const tsEl    = document.getElementById('hr-report-timestamp');
  tsEl.textContent = `Generated: ${new Date().toLocaleString()} | Ref: ${data.report_id}`;

  const avgScore = payload.candidates.reduce((s,c) => s + c.score, 0) / payload.candidates.length;
  const highRec  = payload.candidates.filter(c => c.recommendation === 'Highly Recommended').length;
  const withNotes = payload.candidates.filter(c => c.note).length;

  body.innerHTML = `
    <div class="hr-success-banner">
      <span style="font-size:1.5rem;">🎉</span>
      <div>
        <strong>${data.message}</strong>
        <div style="font-size:0.78rem;color:var(--text-secondary);margin-top:0.15rem;">HR team notified • Report ID: ${data.report_id}</div>
      </div>
    </div>

    <div class="hr-report-section">
      <h4>📊 Shortlist Summary</h4>
      <div class="hr-report-stat-row">
        <div class="hr-report-stat">
          <div class="hr-report-stat-val">${payload.candidates.length}</div>
          <div class="hr-report-stat-label">Candidates</div>
        </div>
        <div class="hr-report-stat">
          <div class="hr-report-stat-val">${avgScore.toFixed(1)}%</div>
          <div class="hr-report-stat-label">Avg Match Score</div>
        </div>
        <div class="hr-report-stat">
          <div class="hr-report-stat-val">${highRec}</div>
          <div class="hr-report-stat-label">Highly Recommended</div>
        </div>
      </div>
      <div style="font-size:0.82rem;color:var(--text-secondary);margin-top:0.25rem;">
        📄 Position: <strong style="color:var(--text-primary);">${payload.job_title}</strong>
        &nbsp;•&nbsp; ${withNotes} recruiter note(s) attached
      </div>
    </div>

    <div class="hr-report-section">
      <h4>👥 Recommended Candidates</h4>
      ${payload.candidates.map((c, i) => {
        const recClass = c.recommendation === 'Highly Recommended' ? 'badge-high'
                       : c.recommendation === 'Consider for Interview' ? 'badge-consider' : 'badge-not';
        return `
          <div class="hr-report-candidate">
            <div class="hr-report-rank">#${i+1}</div>
            <div class="hr-report-cand-info">
              <div class="hr-report-cand-name">${c.name}</div>
              <div class="hr-report-cand-meta">${c.email} &bull; ${c.experience_years} yrs &bull; ${c.category}</div>
              ${c.note ? `<div class="hr-report-cand-note">💬 "${c.note}"</div>` : ''}
              ${c.matched_skills?.length ? `<div style="margin-top:0.35rem;">${c.matched_skills.slice(0,4).map(s=>`<span class="skill-pill skill-matched" style="font-size:0.68rem;padding:0.1rem 0.4rem;">${s}</span>`).join('')}</div>` : ''}
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.35rem;flex-shrink:0;">
              <div class="hr-report-cand-score">${c.score}%</div>
              <span class="badge ${recClass} hr-report-rec-badge">${c.recommendation || '—'}</span>
            </div>
          </div>`;
      }).join('')}
    </div>

    <div class="hr-report-section">
      <h4>📋 Next Steps</h4>
      ${data.next_steps.map(s => `<div style="padding:0.45rem 0.75rem;background:rgba(255,255,255,0.03);border-left:3px solid rgba(251,191,36,0.4);border-radius:0 var(--radius-sm) var(--radius-sm) 0;font-size:0.84rem;color:var(--text-secondary);margin-bottom:0.4rem;line-height:1.55;">${s}</div>`).join('')}
    </div>`;

  modal.classList.add('visible');
}

function closeHrReport() {
  document.getElementById('hr-report-modal').classList.remove('visible');
}

// ── Download HR Report as CSV ──────────────────────────────
function downloadHrReport() {
  if (!_hrReportData) return;
  const candidates = _hrReportData.payload.candidates;
  const jobTitle   = _hrReportData.payload.job_title;
  const reportId   = _hrReportData.report_id;
  const ts         = new Date().toISOString().split('T')[0];

  const header = ['Rank','Name','Email','Match Score (%)','Experience (yrs)','Category','Education','Recommendation','Matched Skills','Missing Skills','Recruiter Note'];
  const rows   = candidates.map(c => [
    c.rank, c.name, c.email, c.score, c.experience_years, c.category,
    c.education, c.recommendation,
    (c.matched_skills || []).join('; '),
    (c.missing_skills || []).join('; '),
    c.note || ''
  ].map(v => `"${String(v).replace(/"/g, '""')}"`));

  const csvContent = [
    `"HR Recommendation Report | Position: ${jobTitle} | Report ID: ${reportId} | Date: ${ts}"`,
    '',
    header.map(h => `"${h}"`).join(','),
    ...rows.map(r => r.join(','))
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `HR_Report_${ts}_${reportId}.csv`;
  a.click();
  showToast('HR Report downloaded!', 'success');
}

// ─── Init ─────────────────────────────────────
fetchDatasetInfo();
