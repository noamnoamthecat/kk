/* ═══════════════════════════════════════════════════════
   FitPath – app.js  (Part 1: State, Utils, Onboarding)
   ═══════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────
const STATE = {
  profile: {},
  schedule: [],
  progress: { weightLog: [], workoutsCompleted: [], streak: 0, lastActive: null },
  achievements: { unlocked: [], character: 'default', background: 'default' },
  chat: { messages: [] },
  settings: { dark: false, apiKey: '' },
  selectedSports: [],
  currentTab: 'home',
  onbStep: 1,
  unit: 'metric',
};

const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const ONB_TOTAL = 7;

// ── Persistence ───────────────────────────────────────────────
function save() { localStorage.setItem('fitpath_v3', JSON.stringify(STATE)); }
function load() {
  try {
    const d = JSON.parse(localStorage.getItem('fitpath_v3') || 'null');
    if (d) Object.assign(STATE, d);
  } catch(e) {}
}

// ── Utils ─────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function showView(id) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  $(id).classList.add('active');
}
function showToast(msg, ms = 2800) {
  const t = $('toast'); t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), ms);
}
function calcBMR(sex, wKg, hCm, age) {
  const b = 10 * wKg + 6.25 * hCm - 5 * age;
  return sex === 'female' ? b - 161 : b + 5;
}
function calcTDEE(bmr, freq) {
  return Math.round(bmr * ({ sedentary:1.2, light:1.375, moderate:1.55, active:1.725, very_active:1.9 }[freq] || 1.2));
}
function calcBMI(wKg, hCm) { return wKg / Math.pow(hCm / 100, 2); }
function fmtDate(d) { return new Date(d).toLocaleDateString('en-GB', { day:'numeric', month:'short' }); }
function todayStr() { return new Date().toISOString().slice(0, 10); }
function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

// ── Dark mode ─────────────────────────────────────────────────
function applyTheme() {
  document.documentElement.setAttribute('data-theme', STATE.settings.dark ? 'dark' : 'light');
  $('darkToggle').textContent = STATE.settings.dark ? '☀️' : '🌙';
}
function toggleDark() {
  STATE.settings.dark = !STATE.settings.dark;
  applyTheme(); save();
}

// ── Landing ───────────────────────────────────────────────────
function goHome() { showView('view-landing'); }
function startOnboarding() {
  STATE.onbStep = 1;
  STATE.selectedSports = [];
  showView('view-onboarding');
  renderOnbStep(1);
}
function openDashboard() {
  showView('view-dashboard');
  switchTab('home');
  renderDashboardHeader();
}

// ── Unit toggle ───────────────────────────────────────────────
function setUnit(u) {
  STATE.unit = u;
  $('utMetric').classList.toggle('active', u === 'metric');
  $('utImperial').classList.toggle('active', u === 'imperial');
  $('heightMetric').classList.toggle('hidden', u !== 'metric');
  $('heightImperial').classList.toggle('hidden', u !== 'imperial');
  $('wtUnit').textContent = u === 'metric' ? 'kg' : 'lb';
}

// ── Onboarding step render ────────────────────────────────────
function renderOnbStep(n) {
  document.querySelectorAll('.onb-step').forEach(s => s.classList.remove('active'));
  const step = document.querySelector(`.onb-step[data-step="${n}"]`);
  if (step) step.classList.add('active');
  const pct = Math.round((n - 1) / ONB_TOTAL * 100);
  $('onbProgress').style.width = pct + '%';
  $('onbStepText').textContent = `${n}/${ONB_TOTAL}`;
  if (n === 6) buildSportsPicker();
}

function showError(msg) {
  let el = document.querySelector('.onb-err');
  if (!el) {
    el = document.createElement('div');
    el.className = 'onb-err';
    document.querySelector('.onb-step.active').appendChild(el);
  }
  el.textContent = '⚠️ ' + msg;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 3500);
}

// ── Onboarding validation & next ─────────────────────────────
function onbNext(step) {
  if (!validateStep(step)) return;
  collectStep(step);
  if (step === ONB_TOTAL) {
    finishOnboarding();
  } else {
    STATE.onbStep = step + 1;
    renderOnbStep(step + 1);
  }
}

function validateStep(step) {
  switch (step) {
    case 1:
      if (!$('inpName').value.trim()) { showError('Please enter your name.'); return false; }
      return true;
    case 2:
      if (!document.querySelector('input[name=sex]:checked')) { showError('Please select your sex.'); return false; }
      if (!$('inpAge').value || $('inpAge').value < 13) { showError('Please enter a valid age.'); return false; }
      return true;
    case 3:
      if (STATE.unit === 'metric' && (!$('inpHCm').value || $('inpHCm').value < 100)) { showError('Enter a valid height (cm).'); return false; }
      if (STATE.unit === 'imperial' && !$('inpHFt').value) { showError('Enter a valid height.'); return false; }
      if (!$('inpWt').value) { showError('Please enter your weight.'); return false; }
      return true;
    case 4:
      if (!document.querySelector('input[name=body]:checked')) { showError('Please pick a body type.'); return false; }
      return true;
    case 5:
      if (!document.querySelector('input[name=exp]:checked')) { showError('Select your weight training experience.'); return false; }
      if (!document.querySelector('input[name=freq]:checked')) { showError('Select your weekly activity level.'); return false; }
      return true;
    case 6:
      if (STATE.selectedSports.length === 0) { showError('Pick at least 1 sport.'); return false; }
      return true;
    case 7:
      if (!document.querySelector('input[name=goal]:checked')) { showError('Please select your goal.'); return false; }
      return true;
    default: return true;
  }
}

function collectStep(step) {
  const p = STATE.profile;
  switch (step) {
    case 1: p.name = $('inpName').value.trim(); break;
    case 2:
      p.sex = document.querySelector('input[name=sex]:checked').value;
      p.age = parseInt($('inpAge').value);
      break;
    case 3:
      if (STATE.unit === 'metric') {
        p.heightCm = parseFloat($('inpHCm').value);
        p.weightKg = parseFloat($('inpWt').value);
      } else {
        const ft = parseFloat($('inpHFt').value || 0);
        const inch = parseFloat($('inpHIn').value || 0);
        p.heightCm = (ft * 12 + inch) * 2.54;
        p.weightKg = parseFloat($('inpWt').value) * 0.453592;
      }
      p.unit = STATE.unit;
      break;
    case 4: p.bodyType = document.querySelector('input[name=body]:checked').value; break;
    case 5:
      p.weightExp  = document.querySelector('input[name=exp]:checked').value;
      p.exerciseFreq = document.querySelector('input[name=freq]:checked').value;
      break;
    case 6: p.sports = [...STATE.selectedSports]; break;
    case 7: p.goal = document.querySelector('input[name=goal]:checked').value; break;
  }
}

function finishOnboarding() {
  collectStep(ONB_TOTAL);
  STATE.progress.startWeight = STATE.profile.weightKg;
  STATE.schedule = generateSchedule();
  unlockAchievement('profile_done');
  save();
  openDashboard();
  showToast('🎉 Your plan is ready, ' + STATE.profile.name + '!');
}

/* ═══ Part 2: Sports Picker ═══ */
function buildSportsPicker() {
  const cats = ['All', ...new Set(SPORTS.map(s => s.cat))];
  $('sportCatFilter').innerHTML = cats.map((c,i) =>
    `<button class="chip${i===0?' active':''}" onclick="filterByCat('${c}',this)">${c}</button>`
  ).join('');
  renderSportsGrid(SPORTS);
}
function filterByCat(cat, el) {
  document.querySelectorAll('#sportCatFilter .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  const q = $('sportSearch').value.toLowerCase();
  const list = SPORTS.filter(s => (cat === 'All' || s.cat === cat) && s.name.toLowerCase().includes(q));
  renderSportsGrid(list);
}
function filterSports() {
  const q = $('sportSearch').value.toLowerCase();
  const active = document.querySelector('#sportCatFilter .chip.active');
  const cat = active ? active.textContent : 'All';
  const list = SPORTS.filter(s => (cat === 'All' || s.cat === cat) && s.name.toLowerCase().includes(q));
  renderSportsGrid(list);
}
function renderSportsGrid(list) {
  $('sportsGrid').innerHTML = list.map(s => {
    const sel = STATE.selectedSports.includes(s.id);
    return `<div class="sport-tile${sel?' selected':''}" onclick="toggleSport('${s.id}',this)">
      <div class="sport-emoji">${s.emoji}</div>
      <div class="sport-name">${s.name}</div>
      <div class="sport-cat">${s.cat}</div>
      ${sel ? '<div class="sport-check">✓</div>' : ''}
    </div>`;
  }).join('');
}
function toggleSport(id, el) {
  const idx = STATE.selectedSports.indexOf(id);
  if (idx >= 0) {
    STATE.selectedSports.splice(idx, 1);
    el.classList.remove('selected');
    el.querySelector('.sport-check')?.remove();
  } else {
    if (STATE.selectedSports.length >= 5) { showToast('Max 5 sports — remove one first'); return; }
    STATE.selectedSports.push(id);
    el.classList.add('selected');
    el.insertAdjacentHTML('beforeend', '<div class="sport-check">✓</div>');
  }
  $('sportsCount').textContent = STATE.selectedSports.length;
}

/* ═══ Part 3: Schedule Generation ═══ */
function generateSchedule() {
  const p = STATE.profile;
  const sports = (p.sports || []).map(id => SPORTS.find(s => s.id === id)).filter(Boolean);
  if (!sports.length) return [];
  const gc = GOAL_CONFIG[p.goal] || GOAL_CONFIG.general;
  const numDays = FREQ_DAYS[p.exerciseFreq] || 3;
  const schedule = [];
  const workDays = DAYS.slice(0, numDays > 5 ? 6 : numDays);
  workDays.forEach((day, i) => {
    const sport = sports[i % sports.length];
    const isCardio = sport.cardio >= 4;
    const intensity = p.weightExp === 'none' ? 2 : p.weightExp === 'beginner' ? 3 : 4;
    const duration = p.exerciseFreq === 'sedentary' ? 30 : p.exerciseFreq === 'light' ? 40 : 50;
    const altSport = sports[(i + 1) % sports.length];
    schedule.push({
      day,
      sport: sport.id,
      sportName: sport.name,
      emoji: sport.emoji,
      duration,
      intensity,
      calories: Math.round(sport.cal * (duration / 60)),
      alt: altSport && altSport.id !== sport.id ? altSport.name : 'Rest / Light walk',
      done: false,
    });
  });
  const restDays = DAYS.filter(d => !workDays.includes(d));
  restDays.forEach(day => schedule.push({ day, sport: 'rest', sportName: 'Rest Day', emoji: '😴', duration: 0, calories: 0, done: false }));
  schedule.sort((a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day));
  return schedule;
}

/* ═══ Part 4: Dashboard Header ═══ */
function renderDashboardHeader() {
  const p = STATE.profile;
  $('dbGreeting').textContent = greeting() + (p.name ? ', ' + p.name : '');
  $('dbTitle').textContent = getTodayMotivation();
  const char = CHARACTERS.find(c => c.id === STATE.achievements.character) || CHARACTERS[0];
  $('dbAvatar').textContent = char.emoji;
  const bg = BACKGROUNDS.find(b => b.id === STATE.achievements.background) || BACKGROUNDS[0];
  $('dbAvatar').style.background = bg.gradient;
}
function getTodayMotivation() {
  const msgs = ['Let\'s crush it today 💪','Stay consistent. Stay winning 🏆','Small steps = big results 📈','You\'ve got this! 🔥','Progress, not perfection ⚡'];
  return msgs[new Date().getDay() % msgs.length];
}

/* ═══ Part 5: Tab Switching ═══ */
function switchTab(tab) {
  STATE.currentTab = tab;
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  renderDashboardHeader();
  const main = $('dbMain');
  switch (tab) {
    case 'home':     main.innerHTML = renderHome();     break;
    case 'schedule': main.innerHTML = renderSchedule(); break;
    case 'chat':     renderChatTab(); break;
    case 'progress': main.innerHTML = renderProgress(); break;
    case 'profile':  main.innerHTML = renderProfile();  break;
  }
  if (tab === 'progress') drawChart();
}

/* ═══ Part 6: Home Tab ═══ */
function renderHome() {
  const p = STATE.profile;
  if (!p.name) return `<div style="text-align:center;padding:60px 20px"><div style="font-size:3rem">👋</div><h2>Welcome!</h2><p class="muted">Complete your profile to get started.</p><button class="btn btn-primary" onclick="startOnboarding()" style="margin-top:20px">Set Up My Profile</button></div>`;
  const bmr  = calcBMR(p.sex, p.weightKg, p.heightCm, p.age);
  const tdee = calcTDEE(bmr, p.exerciseFreq);
  const bmi  = calcBMI(p.weightKg, p.heightCm);
  const gc   = GOAL_CONFIG[p.goal] || GOAL_CONFIG.general;
  const targetCal = tdee + gc.surplusKcal;
  const q    = QUOTES[new Date().getDate() % QUOTES.length];
  const todaySched = STATE.schedule.find(s => s.day === DAYS[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1]);
  const streak = STATE.progress.streak || 0;
  const sports = (p.sports || []).map(id => SPORTS.find(s => s.id === id)).filter(Boolean);

  return `
  <div class="motivation">
    <h3>"${q.text}"</h3>
    <p>— ${q.author}</p>
  </div>
  <div class="streak-row">
    <div class="left"><div class="fire">🔥</div><div class="info"><strong>${streak} Day${streak!==1?'s':''}</strong><span>Current streak</span></div></div>
    <div style="font-size:1.5rem">${streak>=7?'🏆':streak>=3?'⚡':'💪'}</div>
  </div>
  <div class="stats-row">
    <div class="stat-card primary"><div class="label-sm">Daily Target</div><div class="value">${targetCal}</div><div class="sub">kcal/day</div></div>
    <div class="stat-card"><div class="label-sm">Protein Goal</div><div class="value">${Math.round(p.weightKg*(gc.proteinMultiplier||1.8))}g</div><div class="sub">per day</div></div>
    <div class="stat-card"><div class="label-sm">BMI</div><div class="value">${bmi.toFixed(1)}</div><div class="sub">${bmi<18.5?'Underweight':bmi<25?'Normal':bmi<30?'Overweight':'Obese'}</div></div>
    <div class="stat-card"><div class="label-sm">TDEE</div><div class="value">${tdee}</div><div class="sub">kcal maintenance</div></div>
  </div>
  ${todaySched && todaySched.sport !== 'rest' ? `
  <div class="section">
    <div class="section-title">Today's Session <button class="section-link" onclick="switchTab('schedule')">Full Schedule →</button></div>
    <div class="plan-card" style="border-left-color:${gc.color}">
      <h4>${todaySched.emoji} ${todaySched.sportName} — ${todaySched.duration} min</h4>
      <p>~${todaySched.calories} kcal · Intensity: ${INTENSITY_LABELS[todaySched.intensity]}</p>
      <p style="margin-top:6px;font-size:0.78rem;color:var(--text-muted)">Alternative: ${todaySched.alt}</p>
      <button class="btn btn-primary" style="margin-top:12px;padding:10px 20px;font-size:0.85rem" onclick="markDone()">✓ Mark as Done</button>
    </div>
  </div>` : `<div class="plan-card"><h4>😴 Rest Day</h4><p>Recovery is part of the plan. Stay hydrated and sleep well!</p></div>`}
  <div class="section">
    <div class="section-title">Your Sports</div>
    <div style="display:flex;flex-wrap:wrap;gap:8px">${sports.map(s=>`<div class="chip active">${s.emoji} ${s.name}</div>`).join('')}</div>
  </div>
  <div class="section">
    <div class="section-title">Goal: ${gc.label}</div>
    <div class="plan-card">
      <h4>Short-term (4 weeks)</h4>
      <p>${getShortTermGoal(p, tdee)}</p>
    </div>
    <div class="plan-card" style="border-left-color:${gc.color};margin-top:8px">
      <h4>Long-term (3 months)</h4>
      <p>${getLongTermGoal(p, tdee)}</p>
    </div>
  </div>`;
}
function getShortTermGoal(p, tdee) {
  const gc = GOAL_CONFIG[p.goal] || GOAL_CONFIG.general;
  const kgW = gc.surplusKcal / 7700 * 7;
  if (p.goal==='weight_loss') return `Expect to lose ~${Math.abs(kgW*4).toFixed(1)} kg. Energy levels improve. Clothes fit better.`;
  if (p.goal==='muscle_gain') return `Gain ~${(0.5).toFixed(1)}–1kg lean muscle. Strength increases 10–15%.`;
  if (p.goal==='athletic') return `Noticeable endurance boost. Performance improves in all selected sports.`;
  return `Increased energy, better sleep, forming healthy habits.`;
}
function getLongTermGoal(p, tdee) {
  const gc = GOAL_CONFIG[p.goal] || GOAL_CONFIG.general;
  const kgW = gc.surplusKcal / 7700 * 7;
  if (p.goal==='weight_loss') return `~${Math.abs(kgW*12).toFixed(1)} kg total loss. Significant body recomposition. Improved metabolic health.`;
  if (p.goal==='muscle_gain') return `~2–3 kg lean muscle gain. Visible physique change. Significantly stronger.`;
  if (p.goal==='athletic') return `Peak athletic form across your chosen sports. Ready for competition-level performance.`;
  return `Established healthy lifestyle. Reduced disease risk. Mental and physical wellbeing transformed.`;
}
function markDone() {
  const today = todayStr();
  if (!STATE.progress.workoutsCompleted.includes(today)) {
    STATE.progress.workoutsCompleted.push(today);
    const last = STATE.progress.lastActive;
    const yesterday = new Date(); yesterday.setDate(yesterday.getDate()-1);
    const yStr = yesterday.toISOString().slice(0,10);
    STATE.progress.streak = (last === yStr || last === today) ? (STATE.progress.streak||0)+1 : 1;
    STATE.progress.lastActive = today;
    checkAchievements();
    save();
    showToast('🎉 Workout logged! Streak: ' + STATE.progress.streak + ' days');
    switchTab('home');
  } else {
    showToast('Already logged today!');
  }
}

/* ═══ Part 7: Schedule Tab ═══ */
function renderSchedule() {
  const sched = STATE.schedule;
  if (!sched.length) return `<p class="muted" style="text-align:center;padding:40px">No schedule yet. Complete your profile first.</p>`;
  const gc = GOAL_CONFIG[STATE.profile.goal] || GOAL_CONFIG.general;
  return `
  <div class="section">
    <div class="section-title">Weekly Schedule
      <button class="section-link" onclick="regenerateSchedule()">↻ Regenerate</button>
    </div>
    ${sched.map(s => `
    <div class="plan-card" style="border-left-color:${s.sport==='rest'?'var(--border)':gc.color};margin-bottom:10px;opacity:${s.done?'0.55':'1'}">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <h4>${s.emoji} ${s.day} — ${s.sportName}</h4>
        ${s.sport!=='rest'?`<button class="btn btn-secondary" style="padding:6px 12px;font-size:0.75rem" onclick="markDayDone('${s.day}')">${s.done?'✓ Done':'Mark Done'}</button>`:''}
      </div>
      ${s.sport!=='rest'?`
      <p>${s.duration} min · ~${s.calories} kcal · ${INTENSITY_LABELS[s.intensity]||'Moderate'}</p>
      <p style="margin-top:4px;font-size:0.76rem;color:var(--text-muted)">🔄 Alternative: ${s.alt}</p>`
      :'<p>Active recovery — stretch, walk, or full rest.</p>'}
    </div>`).join('')}
  </div>
  <div class="section">
    <div class="section-title">Body Type Note</div>
    <div class="plan-card">
      <p>${BODY_CONFIG[STATE.profile.bodyType]?.note || 'Stay consistent and track your response to training.'}</p>
    </div>
  </div>`;
}
function markDayDone(day) {
  const item = STATE.schedule.find(s => s.day === day);
  if (item) { item.done = true; save(); switchTab('schedule'); showToast('✓ ' + day + ' session logged!'); }
}
function regenerateSchedule() {
  STATE.schedule = generateSchedule();
  STATE.schedule.forEach(s => s.done = false);
  save();
  switchTab('schedule');
  showToast('Schedule updated!');
}

/* ═══ Part 8: Progress Tab ═══ */
function renderProgress() {
  const logs = STATE.progress.weightLog || [];
  const p = STATE.profile;
  const bmi = calcBMI(p.weightKg, p.heightCm);
  const bmiPct = Math.min(Math.max(((bmi-14)/(40-14))*100,2),98);
  const preds = getProgressPredictions(p, calcTDEE(calcBMR(p.sex,p.weightKg,p.heightCm,p.age),p.exerciseFreq));
  const wu = p.unit==='imperial';
  return `
  <div class="section">
    <div class="section-title">Log Weight</div>
    <div class="log-form">
      <div class="input-wrap" style="flex:1"><input type="number" id="logWtInp" placeholder="${wu?'lbs':'kg'}" step="0.1"/><span class="unit">${wu?'lb':'kg'}</span></div>
      <button class="btn btn-primary" onclick="logWeight()">+ Log</button>
    </div>
    <div class="chart-card">
      <h4>📉 Weight Over Time</h4>
      <div class="chart-container"><canvas id="weightChart"></canvas></div>
      ${!logs.length?'<p class="muted" style="text-align:center;padding:20px 0">No data yet — log your first weigh-in above!</p>':''}
    </div>
  </div>
  <div class="section">
    <div class="section-title">BMI</div>
    <div class="chart-card">
      <div class="bmi-bar">
        <div class="bmi-bar-track"><div class="bmi-bar-marker" id="bmiMarker" style="left:${bmiPct}%"></div></div>
        <div class="bmi-bar-labels"><span>Underweight</span><span>Normal</span><span>Overweight</span><span>Obese</span></div>
      </div>
      <p style="text-align:center;font-size:0.85rem;margin-top:8px">BMI: <strong>${bmi.toFixed(1)}</strong> — ${bmi<18.5?'Underweight':bmi<25?'Normal weight':bmi<30?'Overweight':'Obese'}</p>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Goal Timeline</div>
    ${preds.milestones.map((m,i)=>`
    <div class="plan-card" style="margin-bottom:8px;border-left-color:${i<2?'var(--primary)':'var(--accent)'}">
      <h4>${m.label}</h4><p>${m.desc}</p>
    </div>`).join('')}
  </div>
  <div class="section">
    <div class="section-title">Recent Logs</div>
    <ul class="log-list">${logs.slice(-8).reverse().map(l=>`
      <li><span>${wu?(l.weight*2.20462).toFixed(1)+' lb':l.weight+' kg'}</span><span class="log-date">${fmtDate(l.date)}</span></li>`).join('') || '<li><span class="muted">No entries yet</span></li>'}
    </ul>
  </div>`;
}
function logWeight() {
  const inp = $('logWtInp');
  let val = parseFloat(inp.value);
  if (!val || val <= 0) { showToast('Enter a valid weight'); return; }
  if (STATE.profile.unit === 'imperial') val = val * 0.453592;
  STATE.progress.weightLog.push({ date: todayStr(), weight: Math.round(val*10)/10 });
  save(); inp.value = '';
  switchTab('progress');
  showToast('Weight logged!');
  checkAchievements();
}
function drawChart() {
  const canvas = $('weightChart');
  if (!canvas) return;
  const logs = STATE.progress.weightLog || [];
  if (!logs.length) return;
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = 150;
  const vals = logs.map(l => l.unit === 'imperial' ? l.weight * 2.20462 : l.weight);
  const labels = logs.map(l => fmtDate(l.date));
  const min = Math.min(...vals) - 1, max = Math.max(...vals) + 1;
  const W = canvas.width, H = canvas.height;
  const px = (i) => (i / (vals.length-1||1)) * (W-40) + 20;
  const py = (v) => H - 20 - ((v-min)/(max-min||1)) * (H-40);
  ctx.clearRect(0,0,W,H);
  // Grid lines
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--border').trim() || '#e5e7eb';
  ctx.lineWidth = 1;
  [0.25,0.5,0.75].forEach(f => { ctx.beginPath(); ctx.moveTo(20,H-20-(f*(H-40))); ctx.lineTo(W-20,H-20-(f*(H-40))); ctx.stroke(); });
  // Line
  const grad = ctx.createLinearGradient(0,0,W,0);
  grad.addColorStop(0,'#6C63FF'); grad.addColorStop(1,'#FF6584');
  ctx.beginPath(); ctx.strokeStyle = grad; ctx.lineWidth = 2.5;
  vals.forEach((v,i) => i===0 ? ctx.moveTo(px(i),py(v)) : ctx.lineTo(px(i),py(v)));
  ctx.stroke();
  // Fill
  ctx.beginPath();
  vals.forEach((v,i) => i===0 ? ctx.moveTo(px(i),py(v)) : ctx.lineTo(px(i),py(v)));
  ctx.lineTo(px(vals.length-1),H-20); ctx.lineTo(px(0),H-20); ctx.closePath();
  const fillGrad = ctx.createLinearGradient(0,0,0,H);
  fillGrad.addColorStop(0,'rgba(108,99,255,0.2)'); fillGrad.addColorStop(1,'rgba(108,99,255,0)');
  ctx.fillStyle = fillGrad; ctx.fill();
  // Dots
  vals.forEach((v,i) => { ctx.beginPath(); ctx.arc(px(i),py(v),4,0,Math.PI*2); ctx.fillStyle='#6C63FF'; ctx.fill(); ctx.strokeStyle='#fff'; ctx.lineWidth=2; ctx.stroke(); });
}

/* ═══ Part 9: Chat Tab ═══ */
function renderChatTab() {
  const msgs = STATE.chat.messages;
  $('dbMain').innerHTML = `
  <div class="chat-wrap">
    <div class="chat-messages" id="chatMessages">
      ${!msgs.length ? `<div class="chat-bubble ai"><div class="chat-avatar">🤖</div><div class="bubble-text">Hi ${STATE.profile.name||'there'}! I'm your AI fitness coach. Tell me about schedule conflicts, how you're feeling, or ask for advice — I'll adjust your plan! 💪</div></div>` : ''}
      ${msgs.map(m=>`<div class="chat-bubble ${m.role}">
        ${m.role==='ai'?'<div class="chat-avatar">🤖</div>':''}
        <div class="bubble-text">${Chat.renderMarkdown(m.text)}</div>
        ${m.delay?`<div class="delay-badge">⏱ +${m.delay} to goal</div>`:''}
      </div>`).join('')}
      <div id="chatTyping" class="chat-bubble ai hidden"><div class="chat-avatar">🤖</div><div class="bubble-text typing-dots"><span></span><span></span><span></span></div></div>
    </div>
    <div class="chat-quick">
      <button class="chip" onclick="quickMsg('I\'m sick this week')">🤒 I\'m sick</button>
      <button class="chip" onclick="quickMsg('I have a conflict on Saturday')">📅 Schedule conflict</button>
      <button class="chip" onclick="quickMsg('I hit a plateau')">📉 Plateau</button>
      <button class="chip" onclick="quickMsg('How am I doing?')">📊 My progress</button>
      <button class="chip" onclick="quickMsg('I want to train harder')">🔥 More intensity</button>
    </div>
    <div class="chat-input-row">
      <input type="text" id="chatInp" class="chat-input" placeholder="Ask your AI coach anything..." onkeydown="if(event.key==='Enter')sendChat()"/>
      <button class="btn btn-primary" onclick="sendChat()">Send</button>
    </div>
    ${!STATE.settings.apiKey?`<p class="chat-api-note">Using smart rule-based AI. <button class="btn-link-inline" onclick="promptApiKey()">Add Claude API key</button> for real AI.</p>`:''}
  </div>`;
  scrollChat();
}
function scrollChat() {
  setTimeout(() => { const el=$('chatMessages'); if(el) el.scrollTop=el.scrollHeight; }, 100);
}
function quickMsg(msg) { $('chatInp').value = msg; sendChat(); }
async function sendChat() {
  const inp = $('chatInp');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  STATE.chat.messages.push({ role:'user', text:msg });
  renderChatTab();
  const typing = $('chatTyping');
  if (typing) typing.classList.remove('hidden');
  scrollChat();
  try {
    const resp = await Chat.respond(msg, STATE.profile, STATE.schedule, STATE.progress, STATE.settings.apiKey);
    if (typing) typing.classList.add('hidden');
    STATE.chat.messages.push({ role:'ai', text:resp.text, delay:resp.delay||null });
    if (resp.adjustment) applyAdjustment(resp.adjustment);
    unlockAchievement('chat_first');
    if (resp.delay) unlockAchievement('resilient');
    save();
    renderChatTab();
  } catch(e) {
    if (typing) typing.classList.add('hidden');
    STATE.chat.messages.push({ role:'ai', text:'Sorry, something went wrong. Please try again!' });
    renderChatTab();
  }
}
function applyAdjustment(adj) {
  if (adj.type === 'rest' || adj.type === 'deload') showToast('Schedule adjusted for recovery week');
  if (adj.type === 'flex_day' && adj.day) showToast(adj.day + ' marked as flex day');
}
function promptApiKey() {
  const key = prompt('Enter your Claude API key (starts with sk-ant-):');
  if (key && key.startsWith('sk-ant-')) {
    STATE.settings.apiKey = key;
    save();
    showToast('API key saved! Real AI enabled.');
    renderChatTab();
  } else if (key) {
    showToast('Invalid key format.');
  }
}

/* ═══ Part 10: Profile / Achievements Tab ═══ */
function renderProfile() {
  const p = STATE.profile;
  const gc = GOAL_CONFIG[p.goal] || GOAL_CONFIG.general;
  const char = CHARACTERS.find(c => c.id === STATE.achievements.character) || CHARACTERS[0];
  const bg   = BACKGROUNDS.find(b => b.id === STATE.achievements.background) || BACKGROUNDS[0];
  const unlocked = STATE.achievements.unlocked || [];
  const wCount = STATE.progress.workoutsCompleted?.length || 0;
  const streak  = STATE.progress.streak || 0;

  return `
  <div class="profile-top">
    <div class="profile-avatar" style="background:${bg.gradient}">${char.emoji}</div>
    <div class="profile-name">${p.name || 'Athlete'}</div>
    <div class="profile-goal">Goal: ${gc.label}</div>
    <div style="display:flex;gap:16px;justify-content:center;margin-top:16px">
      <div style="text-align:center"><strong style="font-size:1.3rem">${wCount}</strong><br/><span class="muted" style="font-size:0.75rem">Workouts</span></div>
      <div style="text-align:center"><strong style="font-size:1.3rem">${streak}</strong><br/><span class="muted" style="font-size:0.75rem">Streak</span></div>
      <div style="text-align:center"><strong style="font-size:1.3rem">${unlocked.length}</strong><br/><span class="muted" style="font-size:0.75rem">Badges</span></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🏆 Achievements</div>
    <div class="achievement-grid">
      ${ACHIEVEMENTS.map(a => {
        const isUnlocked = unlocked.includes(a.id);
        return `<div class="ach-card ${isUnlocked?'unlocked':'locked'}">
          <div class="ach-icon">${isUnlocked ? a.icon : '🔒'}</div>
          <div class="ach-title">${isUnlocked ? a.title : '???'}</div>
          <div class="ach-desc">${isUnlocked ? a.desc : 'Keep going...'}</div>
        </div>`;
      }).join('')}
    </div>
  </div>

  <div class="section">
    <div class="section-title">🧑 Characters</div>
    <div class="cosmetic-row">
      ${CHARACTERS.map(c => {
        const isOwned = !c.locked || unlocked.some(id => ACHIEVEMENTS.find(a=>a.id===id)?.reward==='character_'+c.id.replace('character_',''));
        const active  = STATE.achievements.character === c.id;
        return `<div class="cosmetic-card ${active?'active':''} ${!isOwned?'locked':''}" onclick="${isOwned?`selectChar('${c.id}')`:''}" title="${c.name}">
          <div style="font-size:1.8rem">${isOwned ? c.emoji : '🔒'}</div>
          <div style="font-size:0.7rem;margin-top:4px">${isOwned ? c.name : '???'}</div>
          ${active?'<div class="cosmetic-active-dot"></div>':''}
        </div>`;
      }).join('')}
    </div>
  </div>

  <div class="section">
    <div class="section-title">🎨 Backgrounds</div>
    <div class="cosmetic-row">
      ${BACKGROUNDS.map(b => {
        const isOwned = !b.locked || unlocked.some(id => ACHIEVEMENTS.find(a=>a.id===id)?.reward===b.id||ACHIEVEMENTS.find(a=>a.id===id)?.reward==='bg_'+b.id);
        const active  = STATE.achievements.background === b.id;
        return `<div class="cosmetic-card bg-card ${active?'active':''} ${!isOwned?'locked':''}" onclick="${isOwned?`selectBg('${b.id}')`:''}" style="${isOwned?'background:'+b.gradient:''}">
          ${active?'<div class="cosmetic-active-dot"></div>':''}
          ${!isOwned?'<div style="font-size:1.5rem">🔒</div>':''}
        </div>`;
      }).join('')}
    </div>
  </div>

  <div class="section">
    <div class="section-title">⚙️ Settings</div>
    <div class="setting-group">
      <div class="setting-row" onclick="toggleDark()">
        <div class="setting-icon">🌙</div>
        <div class="setting-label">Dark Mode</div>
        <div class="switch ${STATE.settings.dark?'on':''}"></div>
      </div>
      <div class="setting-row" onclick="promptApiKey()">
        <div class="setting-icon">🤖</div>
        <div class="setting-label">Claude AI Key</div>
        <div class="setting-value">${STATE.settings.apiKey ? '✓ Set' : 'Not set'}</div>
      </div>
      <div class="setting-row" onclick="startOnboarding()">
        <div class="setting-icon">✏️</div>
        <div class="setting-label">Edit Profile</div>
        <div class="setting-value">→</div>
      </div>
      <div class="setting-row" onclick="resetApp()">
        <div class="setting-icon">🗑️</div>
        <div class="setting-label">Reset All Data</div>
        <div class="setting-value" style="color:var(--danger)">Reset</div>
      </div>
    </div>
  </div>`;
}
function selectChar(id) { STATE.achievements.character = id; save(); switchTab('profile'); renderDashboardHeader(); showToast('Character updated!'); }
function selectBg(id)   { STATE.achievements.background = id; save(); switchTab('profile'); renderDashboardHeader(); showToast('Background updated!'); }
function resetApp() {
  if (!confirm('Reset all data? This cannot be undone.')) return;
  localStorage.removeItem('fitpath_v3');
  location.reload();
}

/* ═══ Part 11: Achievements ═══ */
function checkAchievements() {
  const s = STATE.progress.streak || 0;
  const w = STATE.progress.workoutsCompleted?.length || 0;
  const logs = STATE.progress.weightLog || [];
  const startW = STATE.progress.startWeight || STATE.profile.weightKg;
  const curW   = logs.length ? logs[logs.length-1].weight : startW;
  const lost   = startW - curW;

  ACHIEVEMENTS.forEach(a => {
    if (STATE.achievements.unlocked.includes(a.id)) return;
    let earned = false;
    if (a.type === 'streak'    && s >= a.threshold) earned = true;
    if (a.type === 'workouts'  && w >= a.threshold) earned = true;
    if (a.type === 'weight_loss' && lost >= a.threshold) earned = true;
    if (earned) unlockAchievement(a.id);
  });
}
function unlockAchievement(id) {
  if (STATE.achievements.unlocked.includes(id)) return;
  STATE.achievements.unlocked.push(id);
  const ach = ACHIEVEMENTS.find(a => a.id === id);
  if (!ach) return;
  if (ach.reward) applyReward(ach.reward);
  showAchievementPopup(ach);
  save();
}
function applyReward(reward) {
  if (reward.startsWith('character_')) {
    const charId = reward.replace('character_','');
    const c = CHARACTERS.find(c => c.id === charId);
    if (c) c.locked = false;
  } else if (reward.startsWith('bg_') || BACKGROUNDS.find(b=>b.id===reward)) {
    const bgId = reward.startsWith('bg_') ? reward.replace('bg_','') : reward;
    const bg = BACKGROUNDS.find(b => b.id === bgId);
    if (bg) bg.locked = false;
  }
}
function showAchievementPopup(ach) {
  const pop = $('achPopup');
  $('achPopIcon').textContent  = ach.icon;
  $('achPopTitle').textContent = ach.title;
  $('achPopDesc').textContent  = ach.desc;
  pop.classList.remove('hidden');
  setTimeout(() => pop.classList.add('hidden'), 3500);
}

/* ═══ Part 12: CSS additions for new components (injected) ═══ */
function injectDynamicStyles() {
  const style = document.createElement('style');
  style.textContent = `
  .sports-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-height:340px;overflow-y:auto;padding:4px 0}
  .sport-tile{background:var(--bg-elevated);border:2px solid var(--border);border-radius:var(--r-md);padding:12px 6px;text-align:center;cursor:pointer;transition:all .15s;position:relative}
  .sport-tile:hover{border-color:var(--primary)}
  .sport-tile.selected{border-color:var(--primary);background:var(--primary-light)}
  .sport-emoji{font-size:1.6rem}
  .sport-name{font-size:.72rem;font-weight:700;margin-top:4px;line-height:1.2}
  .sport-cat{font-size:.62rem;color:var(--text-muted)}
  .sport-check{position:absolute;top:4px;right:4px;background:var(--primary);color:#fff;border-radius:50%;width:18px;height:18px;font-size:.65rem;display:flex;align-items:center;justify-content:center;font-weight:700}
  .sports-counter{text-align:center;font-weight:700;font-size:.9rem;color:var(--primary);margin-bottom:10px}
  /* chat */
  .chat-wrap{display:flex;flex-direction:column;height:calc(100vh - 180px)}
  .chat-messages{flex:1;overflow-y:auto;padding:8px 0 12px;display:flex;flex-direction:column;gap:12px}
  .chat-bubble{display:flex;gap:8px;align-items:flex-start;animation:fadeIn .2s}
  .chat-bubble.user{flex-direction:row-reverse}
  .chat-avatar{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--accent));display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0}
  .bubble-text{background:var(--bg-elevated);border:1px solid var(--border-light);border-radius:14px;padding:12px 14px;font-size:.85rem;line-height:1.6;max-width:85%}
  .chat-bubble.user .bubble-text{background:var(--primary);color:#fff;border:none}
  .bubble-text blockquote{border-left:3px solid var(--primary);padding-left:10px;margin:8px 0;font-style:italic;opacity:.9}
  .bubble-text ul{padding-left:16px;margin:4px 0}
  .delay-badge{margin-top:6px;display:inline-block;background:#fef3c7;color:#b45309;border-radius:20px;padding:3px 10px;font-size:.72rem;font-weight:600}
  .chat-quick{display:flex;gap:8px;overflow-x:auto;padding:8px 0;scrollbar-width:none}
  .chat-quick::-webkit-scrollbar{display:none}
  .chat-input-row{display:flex;gap:8px;padding-top:8px}
  .chat-input{flex:1;padding:12px 14px;border:2px solid var(--border);border-radius:var(--r-md);font-size:.9rem;background:var(--bg-elevated);color:var(--text);outline:none}
  .chat-input:focus{border-color:var(--primary)}
  .chat-api-note{font-size:.72rem;color:var(--text-muted);text-align:center;margin-top:8px}
  .btn-link-inline{background:none;border:none;color:var(--primary);font-size:.72rem;font-weight:600;cursor:pointer;text-decoration:underline}
  .typing-dots{display:flex;gap:4px;align-items:center;padding:4px 0}
  .typing-dots span{width:7px;height:7px;border-radius:50%;background:var(--text-muted);animation:bounce .9s infinite}
  .typing-dots span:nth-child(2){animation-delay:.15s}
  .typing-dots span:nth-child(3){animation-delay:.3s}
  @keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
  /* achievements */
  .achievement-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
  .ach-card{background:var(--bg-elevated);border:1px solid var(--border-light);border-radius:var(--r-md);padding:12px 8px;text-align:center;transition:all .2s}
  .ach-card.unlocked{border-color:var(--primary);background:var(--primary-light)}
  .ach-card.locked{opacity:.5}
  .ach-icon{font-size:1.6rem;margin-bottom:4px}
  .ach-title{font-size:.72rem;font-weight:700;margin-bottom:2px}
  .ach-desc{font-size:.65rem;color:var(--text-muted)}
  /* cosmetics */
  .cosmetic-row{display:flex;gap:10px;flex-wrap:wrap}
  .cosmetic-card{width:64px;height:64px;border:2px solid var(--border);border-radius:var(--r-md);display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;position:relative;transition:all .15s;font-size:.7rem;text-align:center;overflow:hidden}
  .cosmetic-card.active{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-light)}
  .cosmetic-card.locked{opacity:.4;cursor:not-allowed}
  .cosmetic-card.bg-card{font-size:.7rem;color:#fff}
  .cosmetic-active-dot{position:absolute;bottom:4px;right:4px;width:8px;height:8px;border-radius:50%;background:var(--primary)}
  /* achievement popup */
  .achievement-popup{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:var(--bg-elevated);border:2px solid var(--primary);border-radius:var(--r-md);padding:14px 20px;box-shadow:var(--shadow-lg);z-index:400;display:flex;align-items:center;gap:12px;min-width:260px;animation:popIn .3s}
  .achievement-popup.hidden{display:none}
  .ach-pop-icon{font-size:2rem}
  .ach-pop-text strong{display:block;font-size:.95rem;color:var(--primary)}
  .ach-pop-text span{font-size:.8rem;color:var(--text-muted)}
  .onb-err{color:#dc2626;font-size:.82rem;margin-top:10px;padding:10px 14px;background:#fef2f2;border-radius:var(--r-sm);border:1px solid #fecaca;display:none}
  `;
  document.head.appendChild(style);
}

/* ═══ Part 13: Init ═══ */
function init() {
  load();
  applyTheme();
  injectDynamicStyles();
  if (STATE.profile.name) {
    $('continueBtn').style.display = 'block';
  }
  showView('view-landing');
}

init();
