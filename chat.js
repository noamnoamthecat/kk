/* ═══════════════════════════════════════════════════════
   FitPath – AI Coach Chat Engine
   Handles rule-based intelligence + optional Claude API
   ═══════════════════════════════════════════════════════ */

const Chat = (() => {

  // ── Intent detection ─────────────────────────────────────────
  const INTENTS = [
    { intent:'sick',      patterns:[/sick|cold|fever|ill|not feel|unwell|flu|headache|nausea|covid/i] },
    { intent:'conflict',  patterns:[/wedding|party|event|trip|travel|vacation|holiday|birthday|funeral|appointment|can't make|cant make|busy|meeting/i] },
    { intent:'plateau',   patterns:[/plateau|not losing|stopped losing|stagnant|no progress|same weight|stuck/i] },
    { intent:'tired',     patterns:[/tired|exhausted|fatigue|no energy|burnout|overtraining|sore|soreness/i] },
    { intent:'motivate',  patterns:[/motivat|inspire|unmotivat|lazy|can't be bothered|give up|quit/i] },
    { intent:'progress',  patterns:[/how am i|my progress|how.*doing|update.*goal|on track/i] },
    { intent:'adjust',    patterns:[/adjust|change|modify|reschedule|move|swap|skip/i] },
    { intent:'nutrition', patterns:[/eat|food|diet|meal|calorie|protein|carb|fat|nutrition|hungry/i] },
    { intent:'schedule',  patterns:[/schedule|plan|week|workout|session|training day/i] },
    { intent:'pain',      patterns:[/pain|hurt|injury|injured|muscle ache|pulled|strain|sprain/i] },
    { intent:'more',      patterns:[/more intense|harder|push more|add.*session|extra workout|step up/i] },
    { intent:'less',      patterns:[/easier|reduce|less intense|dial.*down|too hard|too much/i] },
  ];

  function detectIntent(msg) {
    for (const { intent, patterns } of INTENTS) {
      if (patterns.some(p => p.test(msg))) return intent;
    }
    return 'general';
  }

  // ── Extract specifics from message ───────────────────────────
  function extractDay(msg) {
    const days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday'];
    return days.find(d => msg.toLowerCase().includes(d)) || null;
  }

  function extractSport(msg, profile) {
    if (!profile.sports) return null;
    return profile.sports.find(sid => {
      const sport = SPORTS.find(s => s.id === sid);
      return sport && msg.toLowerCase().includes(sport.name.toLowerCase());
    }) || null;
  }

  // ── Response generators ───────────────────────────────────────

  function respondSick(msg, profile, schedule) {
    const severity = /fever|covid|hospital|serious|very sick/i.test(msg) ? 'serious' : 'mild';
    const restDays = severity === 'serious' ? '7–10' : '3–5';
    const goalDelay = severity === 'serious' ? '1–2 weeks' : '3–5 days';
    const sports = profile.sports?.map(id => SPORTS.find(s => s.id === id)?.name).filter(Boolean) || [];

    return {
      text: `I'm sorry you're not feeling well! 🤒 Here's your adjusted plan:

**This week:** Full rest. Your body heals and grows stronger during recovery — this isn't lost time.

**Impact on your goal:** Expect a slight delay of ~${goalDelay} to your ${GOAL_CONFIG[profile.goal]?.label} goal. Not a big deal in the long run!

**What you CAN do while sick:**
• Light stretching or gentle yoga (if energy allows)
• Stay hydrated — aim for 3L of water/day
• Sleep 8–9 hours — this is when recovery happens
• Eat your protein to preserve muscle

**When you return:** Start at 60% intensity for your first session back. ${sports.length ? `Your ${sports[0]} session will be your first comeback workout.` : ''}

You've got this — rest today, win tomorrow. 💪`,
      adjustment: { type: 'rest', days: severity === 'serious' ? 7 : 3 },
      delay: goalDelay,
    };
  }

  function respondConflict(msg, profile, schedule) {
    const day = extractDay(msg);
    const dayStr = day ? day.charAt(0).toUpperCase() + day.slice(1) : 'that day';
    const sport = extractSport(msg, profile);
    const sportName = sport ? SPORTS.find(s => s.id === sport)?.name : 'your session';
    const sports = profile.sports?.map(id => SPORTS.find(s => s.id === id)).filter(Boolean) || [];
    const altSport = sports.find(s => s.id !== sport) || sports[0];

    return {
      text: `No problem — life happens! 🎉 Here's how we'll handle ${dayStr}:

**${dayStr}'s ${sportName} is rescheduled:**
• Option A: Move it to the next available day
• Option B: Do a shorter 20–30 min home workout instead${altSport ? `\n• Option C: Swap with a ${altSport.name} session` : ''}

**Impact on your goal:** Missing one session = approximately **+1–3 days** to reach your milestone. Totally manageable!

**Quick home alternative for ${dayStr}:**
• 20 min HIIT (jumping jacks, burpees, mountain climbers)
• Or a brisk 30 min walk to maintain calorie burn

**Updated schedule:** I've noted ${dayStr} as a flex day. Enjoy your event — you deserve it! 🥂`,
      adjustment: { type: 'flex_day', day },
      delay: '1–3 days',
    };
  }

  function respondPlateau(msg, profile, schedule) {
    return {
      text: `Plateaus are completely normal — and beatable! 📊 Here's the science and your fix:

**Why it happens:** Your body adapts to your current routine. Metabolism slows slightly as you lose weight, and muscles become efficient at familiar exercises.

**Your 3-step plateau breaker:**

1. **Change the stimulus** — This week, swap the order of your sports or try a new one from your list at higher intensity
2. **Calorie/nutrition audit** — Temporarily reduce by 100–150 kcal/day or increase protein to ${profile.weightKg ? Math.round(profile.weightKg * 2) : 150}g/day
3. **Add a HIIT day** — 20 minutes of high-intensity intervals spikes your metabolism for 24–48 hours

**Revised schedule this week:**
• Add one extra session (short, 20–25 min high intensity)
• Take one session and double the duration at lower intensity

**Estimated result:** With these changes, expect to break the plateau within **10–14 days**. Your goal is still on track! 🎯`,
      adjustment: { type: 'plateau_break' },
    };
  }

  function respondTired(msg, profile, schedule) {
    return {
      text: `Fatigue is a signal worth listening to! 😴 Let's dial things back strategically:

**This week: Recovery Week**
• Reduce all session intensities by 30–40%
• Cut session durations by 15–20 min
• Add an extra rest day
• Focus on sleep (7–9 hours is non-negotiable)

**Signs you need more rest:**
• Performance dropping for 3+ days in a row ✓
• Mood or motivation unusually low ✓
• Muscle soreness lasting more than 72 hours

**What still helps during recovery:**
• Light yoga or gentle stretching
• 20–30 min easy walks
• Cold showers to reduce inflammation
• Extra protein and hydration

**Goal impact:** A proper deload week actually **improves** long-term results by 15–20%. You'll come back stronger. ⚡`,
      adjustment: { type: 'deload' },
    };
  }

  function respondMotivate(msg, profile) {
    const q = QUOTES[Math.floor(Math.random() * QUOTES.length)];
    const name = profile.name || 'Champion';
    const goal = GOAL_CONFIG[profile.goal]?.label || 'your goal';
    return {
      text: `Hey ${name} — I hear you. Every great athlete has days like this. 🌟

> *"${q.text}"*
> — ${q.author}

**Here's a reminder of how far you've come:**
You made the commitment to pursue ${goal}. That puts you ahead of most people who never even start.

**For today — just do 10 minutes:**
Research shows if you start, you almost always finish. A short session is infinitely better than zero.

**Your 10-minute starter:**
• 2 min warmup (arm circles, leg swings)
• 3 rounds of: 30s exercise, 30s rest
• 2 min cool down

You've got this. 💪 I'll be here cheering you on every step of the way.`,
    };
  }

  function respondProgress(msg, profile, progressData) {
    const workouts = progressData?.workoutsCompleted?.length || 0;
    const streak   = progressData?.streak || 0;
    const logs     = progressData?.weightLog || [];
    const startW   = logs[0]?.weight || profile.weightKg;
    const currentW = logs[logs.length - 1]?.weight || profile.weightKg;
    const change   = (currentW - startW).toFixed(1);
    const goal     = GOAL_CONFIG[profile.goal]?.label || 'your goal';

    return {
      text: `Here's your progress snapshot, ${profile.name || 'champ'}! 📊

**Overall Stats:**
• Workouts completed: **${workouts}**
• Current streak: **${streak} day${streak !== 1 ? 's' : ''}** 🔥
• Weight change: **${change > 0 ? '+' : ''}${change} kg**

**Goal: ${goal}**
${workouts < 10 ? '⏳ Keep building consistency — the first 4 weeks are the hardest!' :
  workouts < 25 ? '🚀 You\'re in the zone! Progress is compounding.' :
  '🏆 You\'re a committed athlete. Keep this up!'}

**This week's recommendation:**
${streak >= 7 ? '🔥 You\'re on a hot streak — maintain it!' : `Focus on building your streak. You're at ${streak} days — can you hit ${Math.min(streak + 3, 7)}?`}

Keep logging workouts and weight to see your full progress chart. You're doing amazing! 🌟`,
    };
  }

  function respondNutrition(msg, profile) {
    const tdee = calcTDEE(
      calcBMR(profile.sex, profile.weightKg, profile.heightCm, profile.age),
      profile.exerciseFreq
    );
    const gc = GOAL_CONFIG[profile.goal] || GOAL_CONFIG.general;
    const targetCal = tdee + gc.surplusKcal;
    const protein   = Math.round((profile.weightKg || 70) * gc.proteinMultiplier);

    return {
      text: `Here's your personalized nutrition guidance! 🥗

**Your Daily Targets:**
• **Calories:** ~${targetCal} kcal/day
• **Protein:** ${protein}g (most important macro)
• **Carbs:** ${Math.round(targetCal * 0.4 / 4)}g (fuel for workouts)
• **Fats:** ${Math.round(targetCal * 0.3 / 9)}g (hormones & recovery)
• **Water:** 2.5–3L minimum

**Best protein sources for your goal:**
Chicken breast, Greek yogurt, eggs, salmon, cottage cheese, lentils, tofu

**Pre-workout (30–60 min before):**
Banana + protein shake, or oats + fruit

**Post-workout (within 45 min after):**
Protein + carbs — e.g. chicken + rice, or protein shake + fruit

**Meal timing tip:** Eating every 3–4 hours keeps metabolism fired up. Aim for 4–5 smaller meals vs 2–3 big ones.

Need a specific meal plan? Just ask! 🍽️`,
    };
  }

  function respondPain(msg, profile) {
    return {
      text: `⚠️ First — if the pain is severe or you heard a pop/crack, please see a doctor before continuing training.

**For typical muscle soreness or minor aches:**

**RICE Protocol (first 48 hours):**
• **R**est — avoid the affected movement
• **I**ce — 15–20 min, 3–4x daily
• **C**ompression — light wrap if possible
• **E**levation — if it's a limb

**Adjusted training this week:**
• Skip exercises that aggravate the area
• Work around it — if your shoulder hurts, do lower body; if knee hurts, focus upper body
• Light swimming or walking is almost always safe for recovery

**Your modified plan:**
${profile.sports?.map(id => {
  const s = SPORTS.find(sp => sp.id === id);
  return s ? `• ${s.emoji} ${s.name} — low impact alternative available` : '';
}).filter(Boolean).join('\n') || '• Focus on unaffected body parts'}

**Goal impact:** A small adjustment now prevents a major injury later. Smart athletes train around obstacles. 💡`,
    };
  }

  function respondMore(msg, profile) {
    const tdee = calcTDEE(
      calcBMR(profile.sex, profile.weightKg, profile.heightCm, profile.age),
      profile.exerciseFreq
    );
    return {
      text: `Love the energy! Let's level up! ⚡

**Added to your schedule this week:**
• +1 extra session (high intensity, 30–40 min)
• Increase each session duration by 10–15 min
• Add 2 sets to strength exercises

**Extra session options:**
• HIIT circuit (burpees, box jumps, battle ropes)
• ${profile.sports?.[0] ? SPORTS.find(s => s.id === profile.sports[0])?.name + ' extra session' : 'Cardio sprint session'}
• Yoga or mobility work (active recovery)

**Nutrition adjustment:**
• Increase calories by ~150–200 kcal on intense training days
• Prioritize post-workout protein within 30 min

**Warning:** If you add intensity, also add recovery. Make sure you have at least 1 full rest day. Overtraining is real!

Goal impact: Extra sessions could accelerate results by **15–25%**! 🚀`,
      adjustment: { type: 'increase_intensity' },
    };
  }

  function respondGeneral(msg, profile) {
    const name = profile.name || 'there';
    const sports = profile.sports?.map(id => SPORTS.find(s => s.id === id)?.name).filter(Boolean) || [];
    return {
      text: `Hey ${name}! 🤖 I'm your AI fitness coach. Here's what I can help you with:

**Schedule adjustments:**
• "I'm sick this week" — I'll reschedule your sessions
• "I have a wedding on Saturday" — I'll move or adapt that session
• "I'm feeling tired/overtrained" — I'll create a recovery week

**Progress & Goals:**
• "How am I doing?" — I'll give you a full progress report
• "I hit a plateau" — I'll adjust your plan to break through
• "Add more intensity" — I'll level up your schedule

**Nutrition & Recovery:**
• "What should I eat?" — I'll give you precise macro targets
• "I have shoulder pain" — I'll modify your training safely

**Your active sports:** ${sports.length ? sports.join(', ') : 'None selected yet'}
**Your goal:** ${GOAL_CONFIG[profile.goal]?.label || 'Not set'}

What would you like to talk about? 💬`,
    };
  }

  // ── Shared calc helpers (mirrors app.js) ─────────────────────
  function calcBMR(sex, wKg, hCm, age) {
    if (!wKg || !hCm || !age) return 1800;
    const b = 10 * wKg + 6.25 * hCm - 5 * age;
    return sex === 'female' ? b - 161 : b + 5;
  }
  function calcTDEE(bmr, freq) {
    const m = { sedentary:1.2, light:1.375, moderate:1.55, active:1.725, very_active:1.9 };
    return Math.round(bmr * (m[freq] || 1.2));
  }

  // ── Main response dispatcher ─────────────────────────────────
  async function respond(userMsg, profile, schedule, progressData, apiKey) {
    // If user has provided a Claude API key, use the real AI
    if (apiKey && apiKey.startsWith('sk-ant-')) {
      try {
        return await callClaudeAPI(userMsg, profile, schedule, apiKey);
      } catch (e) {
        console.warn('Claude API failed, falling back to rules:', e.message);
      }
    }
    // Rule-based fallback
    const intent = detectIntent(userMsg);
    switch (intent) {
      case 'sick':      return respondSick(userMsg, profile, schedule);
      case 'conflict':  return respondConflict(userMsg, profile, schedule);
      case 'plateau':   return respondPlateau(userMsg, profile, schedule);
      case 'tired':     return respondTired(userMsg, profile, schedule);
      case 'motivate':  return respondMotivate(userMsg, profile);
      case 'progress':  return respondProgress(userMsg, profile, progressData);
      case 'nutrition': return respondNutrition(userMsg, profile);
      case 'pain':      return respondPain(userMsg, profile);
      case 'more':      return respondMore(userMsg, profile);
      case 'less':      return respondTired(userMsg, profile, schedule); // treat as deload
      default:          return respondGeneral(userMsg, profile);
    }
  }

  // ── Claude API integration ───────────────────────────────────
  async function callClaudeAPI(userMsg, profile, schedule, apiKey) {
    const sports = profile.sports?.map(id => SPORTS.find(s => s.id === id)?.name).filter(Boolean) || [];
    const systemPrompt = `You are FitPath AI, an expert personal fitness coach embedded in a fitness app.
The user's profile:
- Name: ${profile.name || 'User'}
- Goal: ${GOAL_CONFIG[profile.goal]?.label || 'General Health'}
- Sports: ${sports.join(', ') || 'None selected'}
- Experience: ${profile.weightExp || 'Beginner'}
- Weight: ${profile.weightKg}kg, Height: ${profile.heightCm}cm, Age: ${profile.age}
- Activity level: ${profile.exerciseFreq}

Respond in a friendly, motivating tone. Use markdown formatting. Be specific, practical, and encouraging.
If they mention schedule conflicts, illness, or setbacks, adjust their plan and mention the impact on their goal timeline.
Keep responses concise (200–350 words max).`;

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 600,
        system: systemPrompt,
        messages: [{ role: 'user', content: userMsg }],
      }),
    });

    if (!response.ok) throw new Error(`API ${response.status}`);
    const data = await response.json();
    return { text: data.content[0].text };
  }

  // ── Simple markdown renderer ─────────────────────────────────
  function renderMarkdown(text) {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
      .replace(/^• (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br/>');
  }

  return { respond, renderMarkdown, detectIntent };
})();
