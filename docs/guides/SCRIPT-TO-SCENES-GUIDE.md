# SCRIPT-TO-SCENES TRANSFORMATION GUIDE
## Complete Framework for Converting a Written Script into a Production-Ready Visual Scene Sequence

---

## PURPOSE

This document explains the COMPLETE methodology for taking a finished narration script and transforming it into an ordered sequence of video scenes ready for production. It covers:

- How to decompose narration into atomic visual actions
- When and how to insert bridge scenes (B-roll with no narration)
- Time management (each scene = 15 seconds of video)
- Construction/survival process knowledge for logical ordering
- Scene state tracking for visual continuity
- Jack Harlan presenter break integration
- Location image chain evolution
- Quality validation

This is a standalone reference. You do NOT need any external code or app — just the script and this guide.

---

## CORE PRINCIPLE

> **Narration ≠ Visual Sequence.**
> Literary narration can jump in time ("parks truck" → "swings axe").
> Video CANNOT jump — it must show the logical physical progression between every action.
> We use **BRIDGE SCENES** (B-roll, ambient sound only, no narration) to fill the visual gaps.

---

## PIPELINE ORDER (NON-NEGOTIABLE)

```
1. Story/Narration text → finalized script with chapters
2. Script → TTS audio generation per chapter → GIVES US EXACT DURATIONS
3. Audio durations → Scene decomposition (this guide)
4. Scene sequence → Video prompts (one per scene)
5. Video prompts + Character elements + Location images → Video clips (Kling)
6. Audio + Video → Final assembly (FFmpeg)
```

**Why audio FIRST?** Because 63 words at 0.75x speed = 24.1 seconds (measured). Without real duration, you generate too few scenes (gaps) or too many (wasted credits). The audio is the backbone; scenes illustrate the audio.

---

## STEP 1: DEEP PROCESS UNDERSTANDING

> ⚠️ **MANDATORY before writing a single scene.**

Before decomposing any chapter, you MUST deeply understand:

1. **What physical process** is described (clearing land, building foundation, raising walls, etc.)
2. **What the REAL sequence of actions** would be in the physical world — NOT the literary shortcut
3. **What tools, materials, and movements** are involved at each step
4. **What the environment looks like** at each phase of work

### Example of Deep Understanding:

**Narration says:** "drives the axe into frozen wood, clearing spruce saplings"

**Shallow reading:** Erik is chopping down trees  
**Deep understanding:** He is CLEARING LOW BRUSH — cutting small saplings and willow thickets at ground level with horizontal and low-angle axe swings. This is NOT felling large trees. The axe hits small-diameter woody stems close to the ground.

This distinction COMPLETELY changes the video prompt (camera angle, action, particle effects, scale).

---

## STEP 2: THREE CRITICAL LOGIC SYSTEMS

### 2A: TEMPORAL LOGIC
- Each scene must show BELIEVABLE progress for time elapsed
- After 2 scenes of chopping → only a few m² cleared, NOT the entire site
- After a "Day X" card → significantly more progress, but still not 100% unless narration says so
- Never show the FINISHED result until narration explicitly says it's done
- **ASK YOURSELF:** "How much could ONE person do in this amount of time?"

**Progress increment rules:**
| Time elapsed | Realistic clearing progress |
|-------------|----------------------------|
| 2-3 scenes (45s) | ~5-10% of area |
| 1 day of work | ~30-40% of area |
| Multiple days | 60-80% depending on difficulty |
| "Finally cleared" narration | 100% — only now |

### 2B: CONSTRUCTION SEQUENCE LOGIC
The narration may describe steps OUT of real-world order. YOU must reorder to match the REAL construction/survival sequence:

**Cabin building correct order:**
1. **Arrive at site** → park truck, unload
2. **Survey the land** → walk around, evaluate terrain, plan
3. **Clear the land** (fully or mostly) → chop brush, remove debris
4. **Mark the footprint** with stakes and twine → measure, drive stakes, string twine
5. **Dig foundation** → shovel/pickaxe into earth
6. **Lay first logs** → position, check level
7. **Stack walls** → notch logs, lift, interlock
8. **Frame roof** → ridge beam, rafters
9. **Close roof** → sheeting, waterproofing
10. **Finish interior** → floor, hearth, chimney, door

You CANNOT mark footprint on uncleared ground. You CANNOT stack walls without foundation logs. You CANNOT put a roof on without walls. If the narration puts staking before clearing is done, INSERT a "Day X" bridge to justify the time jump.

**ASK YOURSELF:** "Would a real builder do step B before step A is finished?"

### 2C: TOOL VALIDATION
Every action MUST use the correct real-world tool. The script might not mention tools explicitly — you must know which tool is correct:

| Action | Correct tool | WRONG tool |
|--------|-------------|------------|
| Chopping brush/wood | AXE | — |
| Hammering stakes into ground | MALLET or HAMMER | NOT axe |
| Cutting twine | KNIFE | NOT teeth |
| Measuring | TAPE MEASURE or marked stick | — |
| Digging | SHOVEL or PICKAXE | NOT axe |
| Notching logs | AXE + CHISEL | — |
| Leveling surface | SHOVEL + LEVEL | — |
| Lifting heavy logs | CANT HOOK or PEAVEY | NOT bare hands (for large logs) |
| Debarking logs | DRAWKNIFE | NOT axe |

**Rule:** If a scene shows Erik hammering stakes, the tool is a MALLET — even if the narration says "axe." Use the CORRECT tool.

---

## STEP 3: SCENE DECOMPOSITION

### Two types of scenes:

| Type | Has narration? | Purpose | Example |
|------|---------------|---------|---------|
| **Narrated scene** | ✅ Yes — voiceover plays | Illustrates what the narrator describes | Erik swings axe (while narrator says "he cleared brush") |
| **Bridge scene (B-roll)** | ❌ No, ambient sound only | Connects two narrated moments logically | Erik walks from truck to clearing with equipment |

### How to decompose:

**A) Extract Action Units from narration**

Break every sentence into the SMALLEST physical action that would be visible on camera:

```
Narration: "Erik drives the axe into frozen wood, clearing spruce saplings"

→ Action units:
  1. Erik grips the axe, positions himself
  2. Erik swings the axe low into a sapling
  3. Sapling snaps and falls
  4. Erik kicks aside cut brush
  5. Erik moves to next sapling
  6. Repeat pattern (rhythmic work montage)
```

**B) Determine which units become SCENES vs which are IMPLIED**

Not every atomic action needs its own 15-second scene. Group them:
- **Gets its own scene:** First swing, rhythmic montage of chopping, pause to rest/survey
- **Implied (skip):** Each individual sapling hit (repetitive — one montage covers it)

**C) Identify GAPS between narrated actions — these become BRIDGES**

```
Narration: "He parked the truck" → "He started clearing brush"

GAP detected — what's PHYSICALLY missing?
  → Exit truck
  → Look around the area
  → Grab tools from truck bed
  → Walk to the site
  → Evaluate the terrain
  → Position himself, prepare

= 2-3 bridge scenes
```

---

## STEP 4: BRIDGE DENSITY RULES

The number of bridges between two narrated scenes depends on the GAP SIZE:

| Gap type | Bridges needed | Example |
|----------|---------------|---------|
| **Minor** (same location, small time skip) | 0-1 | Chopping → pauses to rest → chops again |
| **Medium** (location change OR tool change) | 1-2 | At truck → walking to forest; OR axe work → grabs tape measure |
| **Major** (different activity entirely) | 2-3 | Arrives at site → starts clearing (exit, look, grab tools, walk, evaluate) |
| **Time jump** (days pass) | 1 bridge + suggest "Day X" card | Day 1 clearing → Day 4 more cleared area |

### Mandatory Bridge Types Checklist

Before finalizing any chapter, verify you have bridges for ALL of these:

- [ ] **Exiting vehicles** → character gets out, looks around
- [ ] **Changing locations** → walking/traveling from A to B
- [ ] **Changing tools** → putting down one tool, retrieving another
- [ ] **Starting new activities** → surveying, preparing, positioning
- [ ] **Time jumps** → "Day X" card suggestion + progress bridge
- [ ] **Evaluating/surveying** → character pauses to assess situation, wipes brow, looks at work

### Bridge Scene Ratio Rule

> **Bridges must constitute AT LEAST 30% of total scenes.**
> If your chapter has 10 narrated scenes and only 2 bridges → you're missing transitions.
> A well-decomposed chapter typically has 40-60% bridges.

**Validation formula:**
```
Narrated scenes = N (from the script)
Bridge scenes = B (you insert)
Total = N + B
Bridge ratio = B / (N + B)

Target: bridge ratio ≥ 0.30
Ideal: bridge ratio ≈ 0.40-0.50
```

If ratio < 0.30 → go back and look for missing transitions.

---

## STEP 5: SCENE STATE TRACKING

Every scene inherits and modifies a state. This ensures visual continuity — you never show a cleared site after only 2 scenes of chopping.

### State Object (track for EVERY scene):

```json
{
  "scene_num": 10,
  "environment": {
    "ground_cleared_pct": 15,
    "ground_description": "a few m² of exposed earth, 85% still dense brush",
    "structures": "none yet",
    "objects_on_ground": "canvas tool bag at edge of cleared patch"
  },
  "tools": {
    "in_hand": "axe",
    "on_ground": "canvas bag with stakes, twine, tape measure",
    "at_truck": "shovel, pickaxe, saw"  
  },
  "character": {
    "erik": { "state": "sweaty, sleeves rolled up", "position": "standing in cleared patch" },
    "gus": { "state": "wandered off into forest", "present": false }
  },
  "time_of_day": "late afternoon, amber light beginning",
  "weather": "overcast, cold, occasional wind gusts",
  "location_image": "loc_c_building_site_partial.png"
}
```

### Scene State Thinking (MANDATORY between scenes):

Before writing each scene, explicitly reason:

```
PREVIOUS SCENE: Erik was chopping brush at the clearing, axe in hand, 15% cleared.
THIS SCENE: Erik marks the footprint with stakes.

→ PROBLEM: He can't mark footprint on mostly-uncleared ground.
→ SOLUTION: Insert "Day X" card to justify clearing being complete ENOUGH (~80%).
→ Also needs BRIDGE: Erik puts down axe, walks to truck, retrieves stakes & twine & tape measure, walks back.
→ STATE CHANGE: ground_cleared_pct jumps to 80% after Day card. Tool changes from axe to mallet + stakes.
```

### State Rules:
- Each scene READS previous state → MODIFIES → PASSES to next scene
- Progress increments must be physically realistic (~5% per active work scene)
- After a "Day X" card, state can jump significantly (15% → 60%)
- Environment descriptions are ALWAYS derived from state — never freehand
- If `gus.present = false`, Gus does NOT appear in the scene

---

## STEP 6: STORYBOARD TABLE FORMAT

Before writing any video prompts, produce this review table:

```
CHAPTER: [Chapter Name]
AUDIO DURATION: [X seconds]  
LOCATIONS NEEDED: [list of distinct locations]

#  | Type     | Action                                        | Narration excerpt          | Location     | Elements        | Tools           | Time    | Progress
---|----------|-----------------------------------------------|---------------------------|--------------|-----------------|-----------------|---------|----------
 1 | narrated | Erik parks the pickup on a snowy trail         | "His old Ford..."         | truck_area   | @Erik, @Pickup  | —               | morning | —
 2 | bridge   | Erik exits truck, surveys the area             | —                         | truck_area   | @Erik, @Pickup  | —               | morning | —
 3 | narrated | Gus leaps from the truck bed into snow         | "Gus, a furry avalanche..." | truck_area | @Gus, @Pickup   | —               | morning | —
 4 | bridge   | Erik grabs axe and canvas bag from truck bed   | —                         | truck_area   | @Erik, @Pickup  | axe, canvas bag | morning | —
 5 | bridge   | Erik and Gus walk toward the forest clearing   | —                         | forest_path  | @Erik, @Gus     | axe             | morning | —
 6 | bridge   | Erik arrives at clearing, evaluates terrain    | —                         | clearing     | @Erik           | axe             | morning | —
 7 | bridge   | Erik positions himself, prepares to chop       | —                         | clearing     | @Erik           | axe             | morning | —
 8 | narrated | Erik swings axe into frozen brush              | "Erik drives the axe..."  | clearing     | @Erik           | axe             | morning | +5% cleared
 9 | narrated | Close-up of strain and effort                  | "his muscles tightening..." | clearing   | @Erik           | axe             | morning | +10% cleared
10 | narrated | Gus nearby, watching                           | "yet the rhythmic work..." | clearing    | @Gus, @Erik     | —               | morning | —
11 | bridge   | Time passes — more area cleared (Day 4 card)   | —                         | clearing     | @Erik           | axe             | afternoon | 60% cleared
12 | bridge   | Erik retrieves stakes, twine, tape from truck  | —                         | truck_area   | @Erik, @Pickup  | stakes, twine, tape measure | afternoon | —
13 | bridge   | Erik uses tape measure, marks corner points    | —                         | clearing     | @Erik           | tape measure, stakes | afternoon | footprint 25% marked
14 | narrated | Erik walks perimeter, stretching twine          | "He stretches the taut..." | clearing   | @Erik           | twine, stakes   | afternoon | footprint 100% marked
...
```

**Column explanation:**
- **#**: Scene number (sequential)
- **Type**: `narrated` (voiceover plays) or `bridge` (ambient only)
- **Action**: What physically happens — one clear atomic action
- **Narration excerpt**: The exact text from the script that plays over this scene (or — for bridges)
- **Location**: Where the scene takes place
- **Elements**: Which characters/objects appear (for Kling element attachment)
- **Tools**: What tools are visible/in use
- **Time**: Time of day (affects lighting)
- **Progress**: Construction/work progress change

---

## STEP 7: JACK HARLAN PRESENTER BREAKS

Jack Harlan breaks are SHORT presenter-to-camera segments that add drama, context, and urgency WITHOUT stopping the action flow.

### 4 Types of Jack Breaks:

| Type | Duration | Purpose | When to use |
|------|----------|---------|-------------|
| **Setup** | 30-45s | Explain what's about to happen and why it matters | Before a new phase of work |
| **Consequence** | 20-30s | Explain what just happened and its significance | After completing a milestone |
| **Cliffhanger** | 15-20s | Create tension about what's next | Between phases, before problems |
| **Crisis** | 30-45s | Explain a major problem and its stakes | When something goes critically wrong |

### Jack Break Structure in the Scene Sequence:

```
[SETUP BREAK: Jack at the site - 30-45s → 2-3 scenes]
  ↓
[ACTION: Erik working - 1-2 minutes → 4-8 scenes]
  ↓  
[CONSEQUENCE BREAK: Jack assesses - 20-30s → 1-2 scenes]
  ↓
[ACTION: Erik continues - 1-2 minutes → 4-8 scenes]
  ↓
[CLIFFHANGER BREAK: Jack warns - 15-20s → 1 scene]
```

### Jack Break Rules:
- **Location:** Jack is ALWAYS at the location of what just happened. He stands where the action was.
- **Tone:** Aggressive, direct, confrontational. Sports commentator meets war correspondent.
- **Language:** Future tense ("This will be..."), rhetorical questions ("Can he pull this off?"), "we are going to show you" (not "I'm showing you")
- **Duration:** 20-30 seconds MAXIMUM (except setup breaks: 30-45 seconds)
- **Long breaks (>30 words):** Split into 2 scenes:
  - Scene A: Acknowledges what was done (looking at the work)
  - Scene B: Confronts what's coming (shifts to the challenge ahead)
- **Frequency:** Every 5-10 minutes of video (every 20-40 scenes)

### Jack Break Scene Format:

```
#  | Type           | Action                                              | Narration                    | Location
---|----------------|-----------------------------------------------------|------------------------------|----------
17 | presenter_setup | Jack stands at clearing, gestures at staked ground   | "This is where it gets real..." | clearing
18 | presenter_setup | Jack turns to camera, serious expression             | "...60 days and counting."     | clearing
```

**Note:** Presenter break scenes also count as 15 seconds each. They appear IN the storyboard sequence at the natural break points between phases.

---

## STEP 8: LOCATION IMAGE CHAIN

Every scene needs a reference image that shows the ENVIRONMENT at that point. As the environment changes (construction progress, lighting, weather), the location image must evolve.

### Image Chain Flow:

```
Scene 5:  loc_005.png  ← generated from scratch (first scene at clearing)
Scene 6:  loc_005.png  ← reused (same place, same state)
Scene 7:  loc_005.png  ← reused (chopping starts but nothing visually changed yet)
Scene 8:  loc_008.png  ← NEW (small area cleared, generated FROM loc_005 as reference)
Scene 9:  loc_008.png  ← reused (same clearing state)
Scene 10: loc_008.png  ← reused (same state)
          ──── "DAY 4" CARD ────
Scene 11: loc_011.png  ← NEW (mostly cleared ground, generated FROM loc_008)
Scene 12: loc_012.png  ← NEW (stakes + twine visible, FROM loc_011)
Scene 13: loc_013.png  ← NEW (golden hour lighting, FROM loc_012)
```

### When to generate a NEW location image:

| Trigger | New image? | Method |
|---------|-----------|--------|
| First scene at new location | ✅ YES | Generate from scratch |
| Construction progress (more cleared, stakes, logs) | ✅ YES | Generate from PREVIOUS image |
| Object added (tools on ground, structures) | ✅ YES | Generate from previous |
| Lighting/time change (morning → afternoon → dusk) | ✅ YES | Generate from previous |
| Same location, same state | ❌ NO | Reuse previous image |
| Close-up of character (no background) | ❌ NO | Reuse previous image |
| Dream/vision sequence | ✅ YES | Generate standalone |

### Location Image Rules:
- **16:9 aspect ratio**, photorealistic
- **Ground level perspective** (eye height — as if standing there)
- **NO characters** in the image — just the environment
- **Consistent lighting** with the scene's time_of_day
- **Style:** "Real photography" — NOT CGI, NOT 3D render
- When generating from a previous image, describe ONLY what changed: "Same environment but 60% of brush cleared, exposing dark earth and small stumps"

---

## STEP 9: VIDEO PROMPT STRUCTURE

Each scene gets ONE video prompt with this format:

### Metadata Header (for operators/editors):
```
SCENE [N] | [NARRATED / BRIDGE / PRESENTER] | 15s
ELEMENTS: @Erik, @Gus (characters/objects to attach in Kling)
LOCATION: loc_008.png (location image to attach)
NARRATION: "exact text excerpt that plays over this scene"
  — or —
NARRATION: none (ambient only — bridge scene)
```

### Prompt Template:
```
No music. [Camera movement] of [scene description].
@Element does [action]. Cut to [another angle].
Cut to [detail shot]. Sound of [ambient sounds]. 4K.
```

### Prompt Rules:
1. **Always start with `No music.`** — Kling adds music by default
2. **Use `Cut to` for multiple camera angles** within 15 seconds — as many as needed
3. **Keep each individual shot SIMPLE** — 1 action per shot. Complexity comes from cuts, not complex actions
4. **Reference elements as `@Name`** — @Erik, @Gus, @Pickup
5. **Specify camera movements:** wide shot, close-up, tracking shot, low angle, aerial drone, panoramic
6. **Specify ambient sounds:** engine rumble, wind through trees, axe impact, paws crunching snow
7. **Always end with `4K.`**
8. **Each scene is INDEPENDENT** — no frame chaining between scenes
9. **Sparse dialogue (once every 4-5 scenes):** Short muttered phrase ("This is the site", "Come on", "That'll hold") — 3-5 words max, spoken to themselves

---

## STEP 10: DURATION CALCULATION

```
Each scene = 15 seconds of video

Narrated scenes = N (determined by script sentence count)
Bridge scenes = B (you insert based on gap analysis)
Presenter breaks = P (Jack Harlan breaks, ~2 scenes each)
Total scenes = N + B + P
Total video duration = Total scenes × 15 seconds

Audio duration (from TTS) = A seconds

VALIDATION:
- If total video < 1.3 × A → you're probably MISSING bridges (too tight)
- If total video > 2.5 × A → too many bridges (overpopulated)
- Sweet spot: total video ≈ 1.5-2.0 × A
```

---

## STEP 11: THE COMPLETE EXAMPLE

### Input narration (Chapter 1, 3 sentences):

> "Erik parks his old Ford at the edge of the trail, engine ticking in the cold silence. Gus, a furry avalanche of anticipation, leaps from the truck bed into the snow. Erik drives the axe with force into the base of a thick spruce sapling, clearing the brush that occupies the building site."

### Step-by-step decomposition:

**1. Deep Process Understanding:**
- Process: ARRIVAL → SITE CLEARING
- Real sequence: park → exit → grab tools → walk to site → evaluate → start chopping
- Tools needed: axe (for chopping), canvas bag (for carrying tools)

**2. Narrated scenes identified:** 3 (one per sentence)

**3. Gaps identified:**
- Sentence 1 → 2: Minor gap (same location) → 0-1 bridges
- Sentence 2 → 3: MAJOR gap (at truck → clearing brush at building site) → 3-4 bridges
  - Exit truck, grab tools
  - Walk to the clearing
  - Arrive, evaluate terrain
  - Position, prepare to chop

**4. Final Scene Sequence:**

```
#  | Type     | Action                                           | Narration                    | Location    | Progress
---|----------|--------------------------------------------------|------------------------------|-------------|----------
 1 | narrated | Erik parks pickup, engine ticks in silence        | "His old Ford..."            | truck_area  | —
 2 | bridge   | Erik exits truck, stands, surveys the landscape   | —                            | truck_area  | —
 3 | narrated | Gus leaps from truck bed into snow                | "Gus, a furry avalanche..."  | truck_area  | —
 4 | bridge   | Erik grabs axe and canvas bag from truck bed       | —                            | truck_area  | —
 5 | bridge   | Erik and Gus walk along forest path to clearing   | —                            | forest_path | —
 6 | bridge   | Erik arrives at clearing, evaluates the terrain    | —                            | clearing    | —
 7 | bridge   | Erik positions himself, tests ground, prepares     | —                            | clearing    | —
 8 | narrated | Erik swings axe into spruce sapling base           | "Erik drives the axe..."     | clearing    | +5% cleared
```

**Scene count:** 3 narrated + 5 bridges = 8 total  
**Bridge ratio:** 5/8 = 62% ✅  
**Video duration:** 8 × 15s = 120 seconds (2 minutes)  
**Audio duration:** ~24 seconds  
**Ratio:** 120/24 = 5.0× — slightly high for only 3 sentences, but appropriate because of the major location change (truck → clearing)

---

## QUALITY VALIDATION CHECKLIST

Before finalizing any chapter's scene sequence, verify:

### Logic Checks:
- [ ] Construction sequence is in correct real-world order
- [ ] Tools match the actions (mallet for stakes, NOT axe)
- [ ] Progress is physically realistic for time elapsed
- [ ] No character appears in a scene after they left
- [ ] Time of day progression is logical (no backwards jumps)
- [ ] Location changes have walking/traveling bridges

### Bridge Checks:
- [ ] Bridge ratio ≥ 30% (ideally 40-50%)
- [ ] Every vehicle exit has a bridge
- [ ] Every location change has a walking bridge
- [ ] Every tool change has a pick-up/put-down bridge
- [ ] Every new activity has a preparation bridge
- [ ] Time jumps have "Day X" cards suggested

### Continuity Checks:
- [ ] Scene state tracks consistently (progress, tools, weather, time)
- [ ] Location images evolve when environment changes
- [ ] Elements (characters) are only present when they should be
- [ ] Lighting shifts match time of day in state tracker

### Duration Checks:
- [ ] Total video ≈ 1.5-2.0× narration audio duration
- [ ] No scene has more than 1 atomic action
- [ ] Presenter breaks are positioned every 5-10 minutes of video

---

## APPENDIX A: SCENE OUTPUT FORMAT (FOR PRODUCTION)

When delivering the final scene sequence, use this JSON format per scene:

```json
{
  "scene_num": 8,
  "type": "narrated",
  "narration_excerpt": "Erik drives the axe with force into the base of a thick spruce sapling...",
  "action": "Erik swings the axe low into a spruce sapling base. Wood chips fly. The sapling cracks and falls.",
  "location_id": "clearing",
  "elements": ["@Erik"],
  "time_of_day": "morning",
  "weather": "overcast, cold",
  "tools": ["axe"],
  "progress_delta": "+5% ground cleared",
  "bridge_reason": null,
  "location_image": "loc_008.png",
  "state": {
    "ground_cleared_pct": 10,
    "tools_in_hand": "axe",
    "erik_state": "sleeves rolled up, starting to sweat"
  }
}
```

For bridge scenes:
```json
{
  "scene_num": 5,
  "type": "bridge",
  "narration_excerpt": null,
  "action": "Erik and Gus walk along a narrow forest path toward the clearing. Gus bounds ahead through the snow.",
  "location_id": "forest_path",
  "elements": ["@Erik", "@Gus"],
  "time_of_day": "morning",
  "weather": "overcast, cold",
  "tools": ["axe"],
  "progress_delta": null,
  "bridge_reason": "Transition from truck area to building site — must show the travel",
  "location_image": "loc_forest_path.png",
  "state": {
    "ground_cleared_pct": 0,
    "tools_in_hand": "axe in right hand, canvas bag over shoulder",
    "erik_state": "fresh, determined, walking briskly"
  }
}
```

---

## APPENDIX B: EPISODE STRUCTURE REFERENCE

For a 45-50 minute episode with ~6 chapters + presenter breaks:

```
[0:00-1:30]   INTRO (Jack in helicopter) → 6 scenes
[1:30-5:00]   PHASE 1: ARRIVAL & ASSESSMENT → 14 scenes + 1 Jack break
[5:00-12:00]  PHASE 2: FOUNDATION & PREPARATION → 28 scenes + 2 Jack breaks
[12:00-20:00] PHASE 3: BUILDING STRUCTURE → 32 scenes + 2 Jack breaks
[20:00-28:00] PHASE 4: CRISIS & TURNING POINT → 32 scenes + 2 Jack breaks
[28:00-38:00] PHASE 5: FINAL PUSH → 40 scenes + 3 Jack breaks
[38:00-45:00] PHASE 6: COMPLETION & PAYOFF → 28 scenes + 1 Jack break
[45:00-50:00] OUTRO → 6 scenes

TOTAL: ~186 scenes ≈ 46.5 minutes at 15s/scene
```

---

*This guide consolidates methodologies tested during manual production of "The Last Shelter" Episode 1 (2026-02-18/19) and validated against real Kling O3 Pro video generation results.*
