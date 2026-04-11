/* ═══════════════════════════════════════════════════════
   FitPath – Static Data: Sports, Achievements, Quotes
   ═══════════════════════════════════════════════════════ */

// ── SPORTS DATABASE ──────────────────────────────────────────
// Each sport: { id, name, emoji, category, calPerHour, cardio(0-5), strength(0-5),
//              flexibility(0-5), endurance(0-5), agility(0-5), equipment, difficulty }

const SPORTS = [
  // ─ Cardio / Running ─
  { id:'running',     name:'Running',           emoji:'🏃', cat:'Cardio',    cal:600,  cardio:5, str:2, flex:1, end:5, agi:2, equip:'Shoes',              diff:'Beginner' },
  { id:'cycling',     name:'Cycling',           emoji:'🚴', cat:'Cardio',    cal:550,  cardio:5, str:2, flex:1, end:5, agi:1, equip:'Bike',               diff:'Beginner' },
  { id:'walking',     name:'Brisk Walking',     emoji:'🚶', cat:'Cardio',    cal:280,  cardio:3, str:1, flex:1, end:3, agi:1, equip:'Shoes',              diff:'Beginner' },
  { id:'hiking',      name:'Hiking',            emoji:'🥾', cat:'Outdoor',   cal:450,  cardio:4, str:2, flex:1, end:4, agi:2, equip:'Shoes, backpack',    diff:'Beginner' },
  { id:'jump_rope',   name:'Jump Rope',         emoji:'🪢', cat:'Cardio',    cal:700,  cardio:5, str:2, flex:2, end:4, agi:4, equip:'Jump rope',          diff:'Beginner' },
  { id:'trail_run',   name:'Trail Running',     emoji:'🌲', cat:'Outdoor',   cal:650,  cardio:5, str:3, flex:1, end:5, agi:3, equip:'Trail shoes',        diff:'Intermediate' },
  { id:'triathlon',   name:'Triathlon',         emoji:'🏅', cat:'Cardio',    cal:800,  cardio:5, str:3, flex:2, end:5, agi:2, equip:'Bike, wetsuit',      diff:'Advanced' },
  { id:'rowing_erg',  name:'Rowing (Erg)',      emoji:'🛶', cat:'Cardio',    cal:600,  cardio:5, str:4, flex:2, end:5, agi:1, equip:'Rowing machine',     diff:'Intermediate' },

  // ─ Swimming / Water ─
  { id:'swimming',    name:'Swimming',          emoji:'🏊', cat:'Water',     cal:550,  cardio:5, str:3, flex:3, end:5, agi:2, equip:'Goggles, pool',     diff:'Beginner' },
  { id:'surfing',     name:'Surfing',           emoji:'🏄', cat:'Water',     cal:400,  cardio:4, str:3, flex:3, end:3, agi:5, equip:'Surfboard',         diff:'Intermediate' },
  { id:'kayaking',    name:'Kayaking',          emoji:'🚣', cat:'Water',     cal:400,  cardio:4, str:3, flex:2, end:4, agi:2, equip:'Kayak, paddle',     diff:'Beginner' },
  { id:'paddleboard', name:'Paddleboarding',    emoji:'🏄', cat:'Water',     cal:430,  cardio:4, str:3, flex:3, end:3, agi:4, equip:'SUP board',         diff:'Beginner' },
  { id:'water_polo',  name:'Water Polo',        emoji:'🤽', cat:'Water',     cal:600,  cardio:5, str:3, flex:2, end:5, agi:4, equip:'Pool access',        diff:'Intermediate' },
  { id:'open_swim',   name:'Open Water Swim',   emoji:'🌊', cat:'Water',     cal:580,  cardio:5, str:3, flex:2, end:5, agi:2, equip:'Wetsuit',           diff:'Intermediate' },

  // ─ Team Sports ─
  { id:'soccer',      name:'Soccer',            emoji:'⚽', cat:'Team',      cal:600,  cardio:5, str:2, flex:2, end:4, agi:5, equip:'Cleats, ball',      diff:'Beginner' },
  { id:'basketball',  name:'Basketball',        emoji:'🏀', cat:'Team',      cal:550,  cardio:5, str:2, flex:2, end:4, agi:5, equip:'Ball, court',       diff:'Beginner' },
  { id:'volleyball',  name:'Volleyball',        emoji:'🏐', cat:'Team',      cal:400,  cardio:4, str:2, flex:3, end:3, agi:4, equip:'Ball, court',       diff:'Beginner' },
  { id:'beach_volley',name:'Beach Volleyball',  emoji:'🏖️', cat:'Team',      cal:480,  cardio:4, str:2, flex:3, end:4, agi:5, equip:'Ball',              diff:'Beginner' },
  { id:'rugby',       name:'Rugby',             emoji:'🏉', cat:'Team',      cal:650,  cardio:5, str:4, flex:2, end:4, agi:4, equip:'Ball, boots',       diff:'Intermediate' },
  { id:'baseball',    name:'Baseball',          emoji:'⚾', cat:'Team',      cal:350,  cardio:2, str:3, flex:2, end:2, agi:3, equip:'Glove, bat, ball',  diff:'Beginner' },
  { id:'hockey',      name:'Field Hockey',      emoji:'🏑', cat:'Team',      cal:550,  cardio:5, str:2, flex:2, end:4, agi:4, equip:'Stick, shin pads',  diff:'Intermediate' },
  { id:'ice_hockey',  name:'Ice Hockey',        emoji:'🏒', cat:'Team',      cal:700,  cardio:5, str:3, flex:2, end:5, agi:5, equip:'Skates, stick',     diff:'Intermediate' },
  { id:'handball',    name:'Handball',          emoji:'🤾', cat:'Team',      cal:600,  cardio:5, str:3, flex:2, end:4, agi:4, equip:'Ball',              diff:'Intermediate' },
  { id:'lacrosse',    name:'Lacrosse',          emoji:'🥍', cat:'Team',      cal:550,  cardio:5, str:3, flex:2, end:4, agi:4, equip:'Stick, pads',       diff:'Intermediate' },
  { id:'cricket',     name:'Cricket',           emoji:'🏏', cat:'Team',      cal:350,  cardio:2, str:3, flex:2, end:3, agi:3, equip:'Bat, ball',         diff:'Beginner' },
  { id:'american_fb', name:'American Football', emoji:'🏈', cat:'Team',      cal:550,  cardio:4, str:5, flex:2, end:4, agi:4, equip:'Pads, helmet',      diff:'Intermediate' },

  // ─ Racket Sports ─
  { id:'tennis',      name:'Tennis',            emoji:'🎾', cat:'Racket',    cal:500,  cardio:4, str:2, flex:3, end:4, agi:5, equip:'Racket, balls',     diff:'Beginner' },
  { id:'badminton',   name:'Badminton',         emoji:'🏸', cat:'Racket',    cal:450,  cardio:4, str:2, flex:3, end:3, agi:5, equip:'Racket',            diff:'Beginner' },
  { id:'squash',      name:'Squash',            emoji:'🎱', cat:'Racket',    cal:700,  cardio:5, str:2, flex:3, end:5, agi:5, equip:'Racket',            diff:'Intermediate' },
  { id:'table_tennis',name:'Table Tennis',      emoji:'🏓', cat:'Racket',    cal:300,  cardio:3, str:1, flex:2, end:2, agi:5, equip:'Paddle',            diff:'Beginner' },
  { id:'pickleball',  name:'Pickleball',        emoji:'🎯', cat:'Racket',    cal:380,  cardio:3, str:1, flex:2, end:3, agi:4, equip:'Paddle',            diff:'Beginner' },
  { id:'padel',       name:'Padel',             emoji:'🎾', cat:'Racket',    cal:450,  cardio:4, str:2, flex:3, end:3, agi:4, equip:'Padel racket',       diff:'Beginner' },

  // ─ Combat / Martial Arts ─
  { id:'boxing',      name:'Boxing',            emoji:'🥊', cat:'Combat',    cal:700,  cardio:5, str:4, flex:2, end:4, agi:4, equip:'Gloves, bag',       diff:'Intermediate' },
  { id:'mma',         name:'MMA',               emoji:'🥋', cat:'Combat',    cal:750,  cardio:5, str:4, flex:3, end:4, agi:5, equip:'Gloves, mat',       diff:'Advanced' },
  { id:'judo',        name:'Judo',              emoji:'🥋', cat:'Combat',    cal:600,  cardio:4, str:4, flex:3, end:4, agi:4, equip:'Gi',                diff:'Intermediate' },
  { id:'bjj',         name:'Brazilian Jiu-Jitsu',emoji:'🥋',cat:'Combat',   cal:500,  cardio:4, str:4, flex:4, end:4, agi:3, equip:'Gi or no-gi',       diff:'Intermediate' },
  { id:'karate',      name:'Karate',            emoji:'🥋', cat:'Combat',    cal:500,  cardio:4, str:3, flex:4, end:3, agi:4, equip:'Gi',                diff:'Beginner' },
  { id:'taekwondo',   name:'Taekwondo',         emoji:'🦵', cat:'Combat',    cal:550,  cardio:4, str:3, flex:5, end:3, agi:5, equip:'Dobak, pads',       diff:'Beginner' },
  { id:'muay_thai',   name:'Muay Thai',         emoji:'👊', cat:'Combat',    cal:700,  cardio:5, str:4, flex:3, end:4, agi:4, equip:'Gloves, hand wraps',diff:'Intermediate' },
  { id:'wrestling',   name:'Wrestling',          emoji:'🤼', cat:'Combat',    cal:650,  cardio:5, str:5, flex:3, end:4, agi:4, equip:'Mat',               diff:'Intermediate' },
  { id:'fencing',     name:'Fencing',           emoji:'🤺', cat:'Combat',    cal:400,  cardio:3, str:2, flex:3, end:3, agi:5, equip:'Foil, mask',        diff:'Intermediate' },
  { id:'kickboxing',  name:'Kickboxing',        emoji:'🥊', cat:'Combat',    cal:650,  cardio:5, str:3, flex:3, end:4, agi:4, equip:'Gloves',            diff:'Intermediate' },

  // ─ Gym / Strength ─
  { id:'weightlifting',name:'Weightlifting',    emoji:'🏋️', cat:'Strength',  cal:400,  cardio:2, str:5, flex:2, end:2, agi:1, equip:'Barbell, gym',      diff:'Intermediate' },
  { id:'powerlifting', name:'Powerlifting',     emoji:'🏋️', cat:'Strength',  cal:380,  cardio:1, str:5, flex:2, end:2, agi:1, equip:'Barbell, belt',     diff:'Intermediate' },
  { id:'crossfit',    name:'CrossFit',          emoji:'💪', cat:'Strength',  cal:700,  cardio:4, str:4, flex:2, end:4, agi:3, equip:'Gym membership',    diff:'Intermediate' },
  { id:'calisthenics',name:'Calisthenics',      emoji:'🤸', cat:'Strength',  cal:450,  cardio:3, str:4, flex:3, end:3, agi:3, equip:'Pull-up bar',       diff:'Beginner' },
  { id:'gymnastics',  name:'Gymnastics',        emoji:'🤸', cat:'Strength',  cal:500,  cardio:3, str:4, flex:5, end:3, agi:5, equip:'Mat, bars',         diff:'Advanced' },
  { id:'bodybuilding',name:'Bodybuilding',      emoji:'💪', cat:'Strength',  cal:380,  cardio:1, str:5, flex:2, end:2, agi:1, equip:'Gym full access',   diff:'Intermediate' },

  // ─ Flexibility / Mind-Body ─
  { id:'yoga',        name:'Yoga',              emoji:'🧘', cat:'Wellness',  cal:250,  cardio:1, str:2, flex:5, end:1, agi:3, equip:'Mat',               diff:'Beginner' },
  { id:'pilates',     name:'Pilates',           emoji:'🧘', cat:'Wellness',  cal:300,  cardio:2, str:3, flex:5, end:2, agi:2, equip:'Mat, reformer',     diff:'Beginner' },
  { id:'tai_chi',     name:'Tai Chi',           emoji:'☯️', cat:'Wellness',  cal:200,  cardio:1, str:1, flex:4, end:2, agi:3, equip:'None',              diff:'Beginner' },
  { id:'dance_hiphop',name:'Hip-Hop Dance',     emoji:'💃', cat:'Dance',     cal:450,  cardio:4, str:2, flex:3, end:3, agi:5, equip:'Shoes',             diff:'Beginner' },
  { id:'dance_ballet',name:'Ballet',            emoji:'🩰', cat:'Dance',     cal:380,  cardio:3, str:3, flex:5, end:3, agi:5, equip:'Pointe shoes',      diff:'Intermediate' },
  { id:'dance_salsa', name:'Salsa Dancing',     emoji:'💃', cat:'Dance',     cal:420,  cardio:4, str:1, flex:3, end:3, agi:5, equip:'Shoes',             diff:'Beginner' },
  { id:'aerial_silk', name:'Aerial Silk',       emoji:'🎪', cat:'Dance',     cal:400,  cardio:3, str:4, flex:5, end:3, agi:4, equip:'Silk fabric',       diff:'Advanced' },

  // ─ Outdoor / Adventure ─
  { id:'rock_climb',  name:'Rock Climbing',     emoji:'🧗', cat:'Outdoor',   cal:500,  cardio:3, str:5, flex:3, end:4, agi:4, equip:'Harness, shoes',    diff:'Intermediate' },
  { id:'mtb',         name:'Mountain Biking',   emoji:'🚵', cat:'Outdoor',   cal:600,  cardio:5, str:3, flex:2, end:4, agi:4, equip:'Mountain bike',     diff:'Intermediate' },
  { id:'parkour',     name:'Parkour',           emoji:'🏃', cat:'Outdoor',   cal:600,  cardio:4, str:3, flex:4, end:4, agi:5, equip:'Shoes',             diff:'Advanced' },
  { id:'skateboard',  name:'Skateboarding',     emoji:'🛹', cat:'Outdoor',   cal:350,  cardio:3, str:2, flex:3, end:3, agi:5, equip:'Skateboard',        diff:'Intermediate' },
  { id:'horseback',   name:'Horseback Riding',  emoji:'🐎', cat:'Outdoor',   cal:350,  cardio:2, str:3, flex:3, end:3, agi:3, equip:'Horse, helmet',     diff:'Intermediate' },
  { id:'archery',     name:'Archery',           emoji:'🏹', cat:'Outdoor',   cal:180,  cardio:1, str:3, flex:2, end:1, agi:2, equip:'Bow, arrows',       diff:'Beginner' },

  // ─ Winter Sports ─
  { id:'skiing',      name:'Alpine Skiing',     emoji:'⛷️', cat:'Winter',    cal:500,  cardio:4, str:3, flex:2, end:3, agi:5, equip:'Skis, boots',       diff:'Intermediate' },
  { id:'snowboard',   name:'Snowboarding',      emoji:'🏂', cat:'Winter',    cal:450,  cardio:4, str:3, flex:3, end:3, agi:5, equip:'Board, boots',      diff:'Intermediate' },
  { id:'ice_skating', name:'Ice Skating',       emoji:'⛸️', cat:'Winter',    cal:400,  cardio:4, str:2, flex:3, end:3, agi:4, equip:'Ice skates',        diff:'Beginner' },
  { id:'xc_ski',      name:'Cross-Country Ski', emoji:'🎿', cat:'Winter',    cal:700,  cardio:5, str:3, flex:2, end:5, agi:2, equip:'XC skis',           diff:'Intermediate' },

  // ─ Other ─
  { id:'golf',        name:'Golf',              emoji:'⛳', cat:'Leisure',   cal:280,  cardio:2, str:2, flex:3, end:2, agi:2, equip:'Clubs',             diff:'Beginner' },
  { id:'bowling',     name:'Bowling',           emoji:'🎳', cat:'Leisure',   cal:180,  cardio:1, str:2, flex:1, end:1, agi:2, equip:'Bowling ball',      diff:'Beginner' },
  { id:'frisbee',     name:'Ultimate Frisbee',  emoji:'🥏', cat:'Team',      cal:550,  cardio:5, str:2, flex:2, end:4, agi:5, equip:'Disc',              diff:'Beginner' },
  { id:'polo',        name:'Polo',              emoji:'🏇', cat:'Outdoor',   cal:400,  cardio:3, str:3, flex:3, end:3, agi:4, equip:'Horse, mallet',     diff:'Advanced' },
  { id:'cheerleading',name:'Cheerleading',      emoji:'📣', cat:'Dance',     cal:450,  cardio:4, str:3, flex:4, end:3, agi:5, equip:'Uniform',           diff:'Intermediate' },
];

// ── ACHIEVEMENTS DATABASE ─────────────────────────────────────

const ACHIEVEMENTS = [
  // Streak achievements
  { id:'streak_3',    title:'On a Roll',          desc:'3-day streak',       icon:'🔥', type:'streak', threshold:3,   reward:'character_spark' },
  { id:'streak_7',    title:'Week Warrior',        desc:'7-day streak',       icon:'⚡', type:'streak', threshold:7,   reward:'bg_energy' },
  { id:'streak_14',   title:'Two Week Titan',      desc:'14-day streak',      icon:'💪', type:'streak', threshold:14,  reward:'character_titan' },
  { id:'streak_30',   title:'Month Master',        desc:'30-day streak',      icon:'🌟', type:'streak', threshold:30,  reward:'bg_galaxy' },
  { id:'streak_60',   title:'Iron Will',           desc:'60-day streak',      icon:'🏆', type:'streak', threshold:60,  reward:'character_champion' },
  { id:'streak_100',  title:'Century Legend',      desc:'100-day streak',     icon:'💎', type:'streak', threshold:100, reward:'bg_legend' },

  // Workout count achievements
  { id:'workouts_1',  title:'First Step',          desc:'Complete 1 workout', icon:'👟', type:'workouts', threshold:1,   reward:null },
  { id:'workouts_10', title:'Getting Serious',     desc:'10 workouts done',   icon:'🎯', type:'workouts', threshold:10,  reward:'bg_gym' },
  { id:'workouts_25', title:'Quarter Century',     desc:'25 workouts done',   icon:'🥈', type:'workouts', threshold:25,  reward:'character_athlete' },
  { id:'workouts_50', title:'Half Century',        desc:'50 workouts done',   icon:'🥇', type:'workouts', threshold:50,  reward:'bg_stadium' },
  { id:'workouts_100',title:'Centurion',           desc:'100 workouts done',  icon:'🏅', type:'workouts', threshold:100, reward:'character_pro' },

  // Goal milestones
  { id:'goal_1kg',    title:'First Kilo',          desc:'Lost 1 kg',          icon:'⚖️', type:'weight_loss', threshold:1,   reward:null },
  { id:'goal_5kg',    title:'Five Down',           desc:'Lost 5 kg',          icon:'🔥', type:'weight_loss', threshold:5,   reward:'bg_beach' },
  { id:'goal_10kg',   title:'Transformation',      desc:'Lost 10 kg',         icon:'🦋', type:'weight_loss', threshold:10,  reward:'character_lean' },

  // Sports-specific
  { id:'multi_sport', title:'Versatile',           desc:'Train 3 different sports', icon:'🎽', type:'sports', threshold:3, reward:'bg_sports' },
  { id:'swim_champ',  title:'Fish',                desc:'Log 10 swim sessions',     icon:'🐟', type:'sport_swim', threshold:10, reward:'character_swimmer' },
  { id:'run_champ',   title:'Road Runner',         desc:'Log 10 run sessions',      icon:'🏃', type:'sport_run', threshold:10, reward:'character_runner' },

  // Chat & adjustment
  { id:'chat_first',  title:'Communicator',        desc:'Use the AI coach first time',icon:'🤖', type:'chat', threshold:1, reward:null },
  { id:'resilient',   title:'Resilient',           desc:'Recovered from a setback', icon:'🧠', type:'resilience', threshold:1, reward:'bg_mountain' },

  // Onboarding
  { id:'profile_done',title:'Ready to Go!',        desc:'Complete your profile',   icon:'✅', type:'onboarding', threshold:1, reward:null },
];

// ── CHARACTERS (profile avatars) ─────────────────────────────

const CHARACTERS = [
  { id:'default',   name:'Starter',      emoji:'🧑', locked:false },
  { id:'spark',     name:'Spark',        emoji:'⚡', locked:true },
  { id:'titan',     name:'Titan',        emoji:'💪', locked:true },
  { id:'champion',  name:'Champion',     emoji:'🏆', locked:true },
  { id:'athlete',   name:'Athlete',      emoji:'🏅', locked:true },
  { id:'swimmer',   name:'Swimmer',      emoji:'🏊', locked:true },
  { id:'runner',    name:'Road Runner',  emoji:'🏃', locked:true },
  { id:'lean',      name:'Lean Machine', emoji:'🦋', locked:true },
  { id:'pro',       name:'Pro',          emoji:'⭐', locked:true },
];

// ── BACKGROUNDS ───────────────────────────────────────────────

const BACKGROUNDS = [
  { id:'default',  name:'Default',   gradient:'linear-gradient(135deg,#6C63FF,#FF6584)', locked:false },
  { id:'gym',      name:'Gym',       gradient:'linear-gradient(135deg,#1a1a2e,#4a4a8a)', locked:true },
  { id:'energy',   name:'Energy',    gradient:'linear-gradient(135deg,#f59e0b,#ef4444)', locked:true },
  { id:'beach',    name:'Beach',     gradient:'linear-gradient(135deg,#06b6d4,#f59e0b)', locked:true },
  { id:'mountain', name:'Mountain',  gradient:'linear-gradient(135deg,#374151,#6ee7b7)', locked:true },
  { id:'galaxy',   name:'Galaxy',    gradient:'linear-gradient(135deg,#0f0f1e,#6C63FF)', locked:true },
  { id:'stadium',  name:'Stadium',   gradient:'linear-gradient(135deg,#10b981,#1a1a2e)', locked:true },
  { id:'sports',   name:'Sports',    gradient:'linear-gradient(135deg,#ef4444,#f59e0b)', locked:true },
  { id:'legend',   name:'Legend',    gradient:'linear-gradient(135deg,#FFD166,#FF6584,#6C63FF)', locked:true },
];

// ── MOTIVATIONAL QUOTES ───────────────────────────────────────

const QUOTES = [
  { text:"The only bad workout is the one that didn't happen.", author:"Unknown" },
  { text:"Your body can stand almost anything. It's your mind you have to convince.", author:"Unknown" },
  { text:"Don't stop when you're tired. Stop when you're done.", author:"David Goggins" },
  { text:"Success is what comes after you stop making excuses.", author:"Luis Galarza" },
  { text:"Take care of your body. It's the only place you have to live.", author:"Jim Rohn" },
  { text:"The pain you feel today will be the strength you feel tomorrow.", author:"Unknown" },
  { text:"Every workout is progress, even when it doesn't feel like it.", author:"Unknown" },
  { text:"You don't have to be great to start, but you have to start to be great.", author:"Zig Ziglar" },
  { text:"Sweat is just fat crying.", author:"Unknown" },
  { text:"Push yourself because no one else is going to do it for you.", author:"Unknown" },
  { text:"Small daily improvements lead to stunning results.", author:"Robin Sharma" },
  { text:"The hardest lift is lifting your butt off the couch.", author:"Unknown" },
];

// ── SCHEDULE TEMPLATES (per goal) ────────────────────────────

const INTENSITY_LABELS = { 1:'Easy', 2:'Moderate', 3:'Moderate-Hard', 4:'Hard', 5:'Max Effort' };

const FREQ_DAYS = { sedentary:3, light:3, moderate:4, active:5, very_active:6 };

// ── GOAL CONFIGS ──────────────────────────────────────────────

const GOAL_CONFIG = {
  athletic:    { surplusKcal:+250, proteinMultiplier:2.0, cardioRatio:0.4, strengthRatio:0.6, label:'Athletic Performance', color:'#6C63FF' },
  weight_loss: { surplusKcal:-450, proteinMultiplier:1.8, cardioRatio:0.65, strengthRatio:0.35, label:'Weight Loss', color:'#FF6584' },
  muscle_gain: { surplusKcal:+350, proteinMultiplier:2.2, cardioRatio:0.25, strengthRatio:0.75, label:'Muscle Gain', color:'#10b981' },
  general:     { surplusKcal:+0,   proteinMultiplier:1.6, cardioRatio:0.5,  strengthRatio:0.5,  label:'General Health', color:'#f59e0b' },
};

// ── BODY TYPE CONFIGS ─────────────────────────────────────────

const BODY_CONFIG = {
  ectomorph:  { note:'As an ectomorph, eat frequently and prioritize progressive overload.', calBonus:+200 },
  mesomorph:  { note:'Mesomorphs respond well to training. Push the intensity!', calBonus:0 },
  endomorph:  { note:'Focus on metabolic conditioning and a consistent calorie deficit.', calBonus:-100 },
  unsure:     { note:'Stick to a balanced approach and track your response to training.', calBonus:0 },
};

// ── PREDICTION DATA ───────────────────────────────────────────

function getProgressPredictions(profile, tdee) {
  const gc = GOAL_CONFIG[profile.goal] || GOAL_CONFIG.general;
  const dailyDelta = gc.surplusKcal;  // kcal/day vs maintenance
  const kgPerWeek  = dailyDelta / 7700 * 7; // 1kg ≈ 7700 kcal
  const bmi        = profile.weightKg / Math.pow(profile.heightCm / 100, 2);

  const milestones = [];
  if (profile.goal === 'weight_loss') {
    [2, 4, 8, 12, 24].forEach(weeks => {
      const loss = Math.abs(kgPerWeek) * weeks;
      milestones.push({ weeks, label:`-${loss.toFixed(1)} kg`, desc:`After ${weeks} weeks` });
    });
  } else if (profile.goal === 'muscle_gain') {
    [4, 8, 12, 24].forEach(weeks => {
      const gain = (profile.weightExp === 'none' ? 0.2 : profile.weightExp === 'beginner' ? 0.15 : 0.1) * weeks;
      milestones.push({ weeks, label:`+${gain.toFixed(1)} kg muscle`, desc:`After ${weeks} weeks` });
    });
  } else if (profile.goal === 'athletic') {
    milestones.push(
      { weeks:4,  label:'Noticeable endurance boost',    desc:'Week 4' },
      { weeks:8,  label:'Strength +10–15%',              desc:'Week 8' },
      { weeks:12, label:'Peak performance phase begins', desc:'Week 12' },
      { weeks:24, label:'Athletic peak form',            desc:'Week 24' },
    );
  } else {
    milestones.push(
      { weeks:2,  label:'Better energy levels',     desc:'Week 2' },
      { weeks:6,  label:'Visible fitness gains',    desc:'Week 6' },
      { weeks:12, label:'Lifestyle transformation', desc:'Week 12' },
    );
  }
  return { milestones, kgPerWeek, bmi };
}
