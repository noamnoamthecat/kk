/* ============================================================
   FitPath – App Logic
   ============================================================ */

const TOTAL_STEPS = 5; // screens 1–5 (0 = welcome, 6 = results)
let currentScreen = 0;
let unit = 'metric';

// ── Utility ──────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function showScreen(n) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  $(`screen-${n}`).classList.add('active');
  currentScreen = n;
  updateProgress();
}

function updateProgress() {
  const pct = currentScreen === 0 ? 0
    : currentScreen > TOTAL_STEPS ? 100
    : Math.round((currentScreen / TOTAL_STEPS) * 100);
  $('progressBar').style.width = pct + '%';

  const dots = document.querySelectorAll('.step-dot');
  dots.forEach((dot, i) => {
    dot.classList.remove('active', 'done');
    const step = i + 1;
    if (step === currentScreen) dot.classList.add('active');
    else if (step < currentScreen) dot.classList.add('done');
  });
}

function buildStepDots() {
  const container = $('stepIndicators');
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const dot = document.createElement('div');
    dot.className = 'step-dot';
    container.appendChild(dot);
  }
}

function nextScreen() { showScreen(currentScreen + 1); }
function prevScreen() { showScreen(currentScreen - 1); }

function resetApp() {
  document.querySelectorAll('input[type=radio]').forEach(r => r.checked = false);
  document.querySelectorAll('input[type=number]').forEach(i => i.value = '');
  showScreen(0);
}

// ── Unit Toggle ───────────────────────────────────────────────

function setUnit(u) {
  unit = u;
  $('unitMetric').classList.toggle('active', u === 'metric');
  $('unitImperial').classList.toggle('active', u === 'imperial');

  if (u === 'metric') {
    $('heightGroup').classList.remove('hidden');
    $('heightFtGroup').classList.add('hidden');
    $('weightUnit').textContent = 'kg';
    $('heightUnit').textContent = 'cm';
  } else {
    $('heightGroup').classList.add('hidden');
    $('heightFtGroup').classList.remove('hidden');
    $('weightUnit').textContent = 'lb';
  }
}

// ── Validation ────────────────────────────────────────────────

function showError(msg) {
  let el = document.querySelector('.error-msg');
  if (!el) {
    el = document.createElement('div');
    el.className = 'error-msg';
    $(`screen-${currentScreen}`).querySelector('.screen-content').appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 4000);
}

function validateAndNext(step) {
  if (!validate(step)) return;
  if (step === TOTAL_STEPS) {
    buildResults();
    showScreen(6);
  } else {
    nextScreen();
  }
}

function validate(step) {
  switch (step) {
    case 1: {
      const sex = document.querySelector('input[name=sex]:checked');
      const age = $('age').value;
      if (!sex) { showError('Please select your sex.'); return false; }
      if (!age || age < 13 || age > 100) { showError('Please enter a valid age (13–100).'); return false; }
      return true;
    }
    case 2: {
      const weight = parseFloat($('weight').value);
      if (!weight || weight <= 0) { showError('Please enter your weight.'); return false; }
      if (unit === 'metric') {
        const h = parseFloat($('heightCm').value);
        if (!h || h < 100 || h > 250) { showError('Please enter a valid height (100–250 cm).'); return false; }
      } else {
        const ft = parseFloat($('heightFt').value);
        if (!ft || ft < 3 || ft > 8) { showError('Please enter a valid height.'); return false; }
      }
      return true;
    }
    case 3: {
      const bt = document.querySelector('input[name=bodyType]:checked');
      if (!bt) { showError('Please select your body type.'); return false; }
      return true;
    }
    case 4: {
      const we = document.querySelector('input[name=weightExp]:checked');
      const ef = document.querySelector('input[name=exerciseFreq]:checked');
      if (!we) { showError('Please select your weight training experience.'); return false; }
      if (!ef) { showError('Please select your exercise frequency.'); return false; }
      return true;
    }
    case 5: {
      const goal = document.querySelector('input[name=goal]:checked');
      if (!goal) { showError('Please select your goal.'); return false; }
      return true;
    }
    default: return true;
  }
}

// ── Results Builder ───────────────────────────────────────────

function getData() {
  const sex      = document.querySelector('input[name=sex]:checked').value;
  const age      = parseInt($('age').value);
  const bodyType = document.querySelector('input[name=bodyType]:checked').value;
  const weightExp = document.querySelector('input[name=weightExp]:checked').value;
  const exerciseFreq = document.querySelector('input[name=exerciseFreq]:checked').value;
  const goal     = document.querySelector('input[name=goal]:checked').value;

  let weightKg, heightCm;
  const rawWeight = parseFloat($('weight').value);
  if (unit === 'metric') {
    weightKg  = rawWeight;
    heightCm  = parseFloat($('heightCm').value);
  } else {
    weightKg  = rawWeight * 0.453592;
    const ft  = parseFloat($('heightFt').value) || 0;
    const inn = parseFloat($('heightIn').value) || 0;
    heightCm  = (ft * 12 + inn) * 2.54;
  }

  return { sex, age, weightKg, heightCm, bodyType, weightExp, exerciseFreq, goal };
}

function calcBMI(weightKg, heightCm) {
  const h = heightCm / 100;
  return weightKg / (h * h);
}

function bmiCategory(bmi) {
  if (bmi < 18.5) return { label: 'Underweight', color: '#93c5fd' };
  if (bmi < 25)   return { label: 'Normal weight', color: '#6ee7b7' };
  if (bmi < 30)   return { label: 'Overweight', color: '#fde68a' };
  return { label: 'Obese', color: '#fca5a5' };
}

// Mifflin-St Jeor BMR
function calcBMR(sex, weightKg, heightCm, age) {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * age;
  return sex === 'female' ? base - 161 : base + 5;
}

const activityMultipliers = {
  sedentary:   1.2,
  light:       1.375,
  moderate:    1.55,
  active:      1.725,
  very_active: 1.9,
};

function calcTDEE(bmr, freq) {
  return Math.round(bmr * (activityMultipliers[freq] || 1.2));
}

// ── Plan Data ─────────────────────────────────────────────────

const plans = {
  athletic: {
    emoji: '🏆',
    title: 'Athletic Performance Plan',
    subtitle: 'Train hard, eat smart, perform at your peak.',
    cards: (d, tdee) => [
      {
        title: '🏋️ Training Focus',
        desc: trainingFocus(d),
      },
      {
        title: '🔥 Daily Calorie Target',
        desc: `~${tdee + 250}–${tdee + 400} kcal/day — a slight surplus supports muscle growth and energy for intense training. Prioritize complex carbs around workouts.`,
      },
      {
        title: '🥩 Protein Intake',
        desc: `Aim for ${Math.round(d.weightKg * 1.8)}–${Math.round(d.weightKg * 2.2)} g of protein per day. Great sources: chicken, fish, eggs, Greek yogurt, legumes.`,
      },
      {
        title: '📅 Weekly Schedule Suggestion',
        desc: weeklySchedule(d, 'athletic'),
      },
      {
        title: '💡 Performance Tips',
        desc: performanceTips(d),
      },
    ],
  },
  weight_loss: {
    emoji: '⚖️',
    title: 'Weight Loss Plan',
    subtitle: 'Burn fat, build habits, feel great every day.',
    cards: (d, tdee) => [
      {
        title: '🥗 Calorie Target',
        desc: `~${tdee - 500}–${tdee - 300} kcal/day — a moderate deficit for steady fat loss (~0.5 kg/week) without losing muscle. Never go below 1200 kcal (women) or 1500 kcal (men).`,
      },
      {
        title: '🏃 Cardio Strategy',
        desc: cardioStrategy(d),
      },
      {
        title: '🏋️ Resistance Training',
        desc: `Lift weights ${liftDays(d)} days per week. Muscle mass raises your metabolism and prevents the "skinny fat" effect. ${d.weightExp === 'none' ? 'Start with full-body circuits 2–3x/week.' : 'Focus on compound lifts: squats, deadlifts, rows.'}`,
      },
      {
        title: '🥩 Protein Intake',
        desc: `Keep protein high — ${Math.round(d.weightKg * 1.6)}–${Math.round(d.weightKg * 2.0)} g/day — to preserve muscle while in a deficit. Protein also keeps you fuller longer.`,
      },
      {
        title: '💡 Habit Tips',
        desc: habitTips(d),
      },
    ],
  },
};

function trainingFocus({ weightExp, bodyType }) {
  const base = {
    none: 'Start with 3 full-body sessions per week using bodyweight and light weights. Master the basics: squat, hinge, push, pull.',
    beginner: 'Follow a 3-day PPL (Push/Pull/Legs) or full-body program. Build a solid strength foundation before specializing.',
    intermediate: 'Move to a 4-day Upper/Lower split. Add progressive overload each session — increase weight or reps weekly.',
    advanced: 'Use a 5–6-day periodized program (linear or block periodization). Incorporate deload weeks every 4–6 weeks.',
  }[weightExp];
  const btNote = bodyType === 'ectomorph' ? ' As an ectomorph, prioritize heavy compound lifts and adequate rest.' : bodyType === 'endomorph' ? ' Include metabolic conditioning to manage body fat.' : '';
  return base + btNote;
}

function weeklySchedule({ weightExp, exerciseFreq }, goal) {
  if (exerciseFreq === 'sedentary' || weightExp === 'none') {
    return 'Mon: Full-body strength · Wed: Light cardio / yoga · Fri: Full-body strength · Weekend: Active recovery (walk, swim).';
  }
  if (exerciseFreq === 'moderate' || weightExp === 'beginner') {
    return 'Mon: Upper body · Tue: Cardio · Thu: Lower body · Fri: Full body · Sat: Active recovery.';
  }
  return 'Mon: Push · Tue: Pull · Wed: Legs · Thu: Upper (hypertrophy) · Fri: Lower (power) · Sat: Cardio + core · Sun: Rest.';
}

function performanceTips({ bodyType, weightExp, sex }) {
  const tips = [
    'Sleep 7–9 hours — this is when your muscles rebuild and strength gains are locked in.',
    'Track your lifts in a notebook or app to ensure progressive overload.',
    'Warm up properly (5–10 min dynamic stretching) before every session to prevent injury.',
  ];
  if (bodyType === 'ectomorph') tips.push('Eat frequently (every 3–4 hrs) to support high caloric needs.');
  if (weightExp === 'advanced') tips.push('Consider periodized deload weeks to allow full recovery and break plateaus.');
  return tips.join(' · ');
}

function cardioStrategy({ exerciseFreq, bodyType, weightExp }) {
  if (exerciseFreq === 'sedentary') return 'Start with 20–30 min brisk walks 4–5x/week. This is low-impact, effective, and sustainable. Gradually add jogging intervals.';
  if (bodyType === 'endomorph') return '3–4 sessions of HIIT (high-intensity interval training) per week — e.g., 20 min of 40s on / 20s off. Endomorphs respond well to high-intensity work.';
  return '2–3 sessions of moderate cardio (cycling, swimming, jogging) plus 1–2 HIIT sessions per week. Vary intensity to prevent adaptation.';
}

function liftDays({ exerciseFreq }) {
  return { sedentary: 2, light: 2, moderate: 3, active: 4, very_active: 4 }[exerciseFreq] || 3;
}

function habitTips({ sex, age }) {
  const tips = [
    'Drink 2.5–3 L of water daily — dehydration is often mistaken for hunger.',
    'Eat slowly and without screens to improve satiety awareness.',
    'Prep meals in advance on Sundays to avoid reaching for junk food.',
  ];
  if (age > 40) tips.push('Prioritize joint-friendly exercises and recovery — listen to your body.');
  return tips.join(' · ');
}

// ── Render Results ────────────────────────────────────────────

function buildResults() {
  const d = getData();
  const bmi = calcBMI(d.weightKg, d.heightCm);
  const bmiCat = bmiCategory(bmi);
  const bmr = calcBMR(d.sex, d.weightKg, d.heightCm, d.age);
  const tdee = calcTDEE(bmr, d.exerciseFreq);
  const plan = plans[d.goal];

  // Subtitle
  $('resultsSubtitle').textContent = `${plan.emoji} ${plan.title}`;

  // Stats
  const displayWeight = unit === 'metric'
    ? `${Math.round(d.weightKg)} kg`
    : `${Math.round(d.weightKg * 2.20462)} lb`;
  const displayHeight = unit === 'metric'
    ? `${Math.round(d.heightCm)} cm`
    : `${Math.floor(d.heightCm / 30.48)}' ${Math.round((d.heightCm % 30.48) / 2.54)}"`;

  $('statsGrid').innerHTML = `
    <div class="stat-card">
      <div class="stat-value">${displayWeight}</div>
      <div class="stat-label">Weight</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${displayHeight}</div>
      <div class="stat-label">Height</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${bmi.toFixed(1)}</div>
      <div class="stat-label">BMI · ${bmiCat.label}</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${Math.round(bmr)}</div>
      <div class="stat-label">BMR (kcal)</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${tdee}</div>
      <div class="stat-label">TDEE (kcal)</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${d.age}</div>
      <div class="stat-label">Age</div>
    </div>
  `;

  // BMI Bar
  const bmiPct = Math.min(Math.max(((bmi - 14) / (40 - 14)) * 100, 2), 98);
  const bmiBar = `
    <div class="bmi-bar-wrap">
      <div class="bmi-bar-label"><span>Underweight</span><span>Normal</span><span>Overweight</span><span>Obese</span></div>
      <div class="bmi-bar-track">
        <div class="bmi-bar-marker" style="left:${bmiPct}%"></div>
      </div>
      <div class="bmi-value-label">Your BMI: <strong>${bmi.toFixed(1)}</strong> — ${bmiCat.label}</div>
    </div>
  `;

  // Plan cards
  const cards = plan.cards(d, tdee).map(c => `
    <div class="plan-card">
      <div class="plan-card-title">${c.title}</div>
      <div class="plan-card-desc">${c.desc}</div>
    </div>
  `).join('');

  $('planSection').innerHTML = `
    ${bmiBar}
    <h3 style="margin-top:24px; margin-bottom:14px;">📋 Your Recommendations</h3>
    <div class="plan-cards">${cards}</div>
    <p style="margin-top:20px; font-size:0.76rem; color:var(--text-muted); text-align:center;">
      ⚠️ These are general guidelines, not medical advice. Consult a healthcare professional before starting a new fitness program.
    </p>
  `;
}

// ── Init ──────────────────────────────────────────────────────

buildStepDots();
showScreen(0);
