# Manual Video Production Pipeline
## Reference for Future Automation

This document tracks every manual step we're performing to produce a video episode,
so we can systematically automate each one in the app later.

---

## 🔑 CRITICAL INSIGHT: Pipeline Order

> **Audio FIRST → then Video Prompts**
>
> You CANNOT write accurate video prompts without knowing the exact audio duration.
> The durations determine how many scenes you need, how long each one is, and what
> content each scene must cover. Audio is the backbone; video illustrates the audio.

### Correct pipeline order:
```
1. Story DNA → Narration text (Gemini)
2. Narration text → Enhanced text with audio tags (Gemini Flash)  
3. Enhanced text → TTS audio clips (ElevenLabs v3) ← GIVES US EXACT DURATIONS
4. Audio durations → Scene plan (how many scenes, what each covers)
5. Scene plan → Video prompts (one per scene, matched to narration)
6. Video prompts + Elements → Video clips (Kling)
7. Audio + Video → Final assembly (FFmpeg)
```

### Why audio first?
- 63 words at 0.75x speed = 24.1 seconds (measured, not estimated)
- Word count alone is unreliable — pauses, audio tags, and speed settings change duration
- Without real duration, you either generate too few scenes (gaps) or too many (waste credits)

---

## Phase 1: Elements (Character Assets for Kling)

### What we did manually:
1. **Generated portrait images** for each character/object:
   - Format: **2:3 aspect ratio**, neutral white studio background
   - Style: **photorealistic** — explicitly specify "real photography, Canon EOS R5" NOT "3D render"
   - One portrait image is minimum, but **multiple angles = better consistency**
2. **Multi-angle strategy for complex characters** (e.g., animals):
   - Front-facing portrait (mandatory)
   - Side profile, full body (recommended)
   - Top-down view (optional, useful for aerial shots)
   - Kling accepts up to **7 images per element** — more angles = better recognition
3. **Uploaded each image to Kling** as an Element manually
4. **Character description** added in Kling for each element (max 200 chars)

### Elements created for Episode 1:
| Element | Images | Description |
|---------|--------|-------------|
| `@Jack` | 1 (frontal) | Presenter, 45yo, salt-pepper hair, green canvas jacket |
| `@Erik` | 1 (frontal) | 35yo Scandinavian, blonde, Carhartt jacket |
| `@Pickup` | 1 (three-quarter) | 1976 Ford F-150, dark green, rust, firewood in bed |
| `@Gus` | 3 (front + side + top) | Bernese Mountain Dog, tricolor, large build |

### Key learnings:
- ❌ First pickup image looked like a videogame → fixed by adding "real photography, NOT CGI, NOT 3D render"
- ✅ Studio background is important for clean element extraction
- ✅ Animals benefit most from multiple angle references

### Element files location:
```
projects/<project-id>/elements/
├── erik-element.png
├── pickup-element.png
├── gus-element.png
├── gus-side-profile.png
└── gus-top-view.png
```

### Automation needs:
- [ ] Auto-generate element images from character descriptions in story DNA
- [ ] Generate multiple angles automatically for animals/complex objects
- [ ] Kling API to create Elements programmatically (if API supports it)
- [ ] Store element metadata (name, description, images[]) per project

---

## Phase 2: Narration & Audio Generation

> **CRITICAL: Generate audio PER CHAPTER, not per phrase.**
> Generating phrase-by-phrase causes voice tone inconsistency between clips.
> Generating per chapter keeps the emotional arc natural within each chapter.
> Presenter breaks between chapters act as natural dividers — tone changes are invisible.

### Audio structure per episode:
```
[INTRO]      → 1 audio (presenter, Jack)
[CHAPTER 1]  → 1 audio (full chapter narration, voiceover)
[BREAK 1]    → 1 audio (presenter, Jack)  ← hides tone change
[CHAPTER 2]  → 1 audio (full chapter narration, voiceover)
[BREAK 2]    → 1 audio (presenter, Jack)  ← hides tone change
[CHAPTER 3]  → 1 audio (full chapter narration, voiceover)
...
[CLOSE]      → 1 audio (presenter, Jack)
```

### What we did manually:
1. **Generated narration text** via `story_engine.py` → Gemini
   - Intro/breaks/close: presenter-style, first person, direct to camera
   - Body chapters: third-person cinematic voiceover
2. **Enhanced text with audio tags** via `voice_engine.py` → Gemini Flash
   - Adds `[sighs]`, `[whispers]`, `[inhales deeply]`, etc.
3. **Generated TTS audio** via ElevenLabs v3
   - Voice ID: `tkPQHnQfmFvyE5X9juYK`
   - Model: `eleven_v3`
   - Speed: `0.70` (confirmed by user, was 0.75 — too fast)
   - Output: MP3 44100Hz 128kbps
   - **One call per chapter** — NOT per sentence/phrase
   - If chapter exceeds 5000 chars: split into 2 blocks, use `previous_request_ids`
4. **Measured actual duration** from the generated audio file

### Automation needs:
- [x] Narration generation — `story_engine.py`
- [x] Audio enhancement — `voice_engine.py`
- [x] TTS generation — `voice_engine.py`
- [ ] **Generate 1 audio file per chapter** (concat all phase sentences)
- [ ] After audio: analyze text + duration → auto-create scene breakdowns
- [ ] Return per-chapter audio with duration → feeds into video prompt generation

---

## Phase 3: Cinematic Analysis (Text → Visual Sequence)

> **CRITICAL DISCOVERY: Narration ≠ Visual sequence.**
> Literary narration can jump in time ("parks truck" → "swings axe").
> Video CANNOT jump — it must show the logical progression between actions.
> We need BRIDGE SCENES (B-roll, no narration) to fill the visual gaps.

### Two types of scenes:
| Type | Has narration? | Purpose | Example |
|------|---------------|---------|---------|
| **Narrated scene** | ✅ Yes | Illustrates what the voice is describing | Erik swings axe (while narrator describes it) |
| **Bridge scene (B-roll)** | ❌ No, ambient only | Connects two narrated moments logically | Erik walks to the clearing with equipment |

### STEP 1: Deep Process Understanding (MANDATORY before anything)
> **Before writing a single prompt, you MUST deeply understand:**
> - What construction/survival process is described in the chapter
> - What the REAL sequence of physical actions would be (not the literary shortcut)
> - What tools, materials, and movements are involved at each step
> - What the environment looks like at each phase of the work
>
> Example: "drives the axe into frozen wood, clearing spruce saplings" = CLEARING LOW BRUSH,
> not felling large trees. The axe hits small saplings and willow thickets at ground level.
> Understanding this distinction is critical for accurate video prompts.
>
> **⚠️ TEMPORAL LOGIC (tested 2026-02-19):**
> - Each prompt must show BELIEVABLE progress for the time elapsed
> - After 2 scenes of chopping → only a few m² cleared, NOT the entire site
> - After "Day 4" card (editor adds in post) → much more cleared, still not perfect
> - Never show the FINISHED result until the narration explicitly says it's done
> - The editor can insert "Day X" title cards to justify time jumps between scene groups
> - But within a consecutive sequence, progress must be gradual and realistic
> - ASK YOURSELF: "How much could one person do in this amount of time?"
>
> **⚠️ CONSTRUCTION SEQUENCE LOGIC (tested 2026-02-19):**
> - The narration may describe steps out of their real-world order
> - YOU must reorder to match the REAL construction sequence:
>   1. Clear the land FIRST (fully or mostly)
>   2. THEN mark the footprint with stakes
>   3. THEN dig foundation
>   4. THEN lay first logs
>   5. THEN stack walls, etc.
> - You CANNOT mark footprint on uncleared ground — it makes no physical sense
> - If narration puts staking before clearing is done, INSERT a "Day X" bridge
>   to justify the time jump needed for clearing to be complete enough
> - ASK YOURSELF: "Would a real builder do step B before step A is finished?"
>
> **⚠️ TOOL VALIDATION (tested 2026-02-19):**
> - Every action MUST use the correct real-world tool
> - Chopping brush/wood → AXE
> - Hammering stakes into ground → MALLET or HAMMER (NOT axe)
> - Cutting twine → KNIFE
> - Measuring → TAPE MEASURE or marked stick
> - Digging → SHOVEL or PICKAXE
> - Notching logs → AXE + CHISEL
> - The prompt generator must validate: "Is this the right tool for this action?"
> - Use the CORRECT tool even if the narration doesn't mention it explicitly

### STEP 2: Storyboard Analysis Table (MANDATORY before prompts)
Before writing ANY video prompts, produce this table for user review:

```
CHAPTER: [name]
LOCATIONS NEEDED: [list of distinct locations]

# | Narrated action               | What's missing before? (bridge)      | Location  | Elements
--|-------------------------------|--------------------------------------|-----------|----------
1 | Erik parks the pickup         | (start)                              | LOC_A     | @Erik, @Pickup
2 |                               | Erik exits truck, looks around       | LOC_A     | @Erik, @Pickup
3 | Gus jumps from truck          |                                      | LOC_A     | @Gus, @Erik
4 |                               | Erik grabs tools from truck bed      | LOC_A     | @Erik, @Pickup
5 |                               | Erik and Gus walk toward forest      | LOC_B     | @Erik, @Gus
6 |                               | Erik arrives, evaluates terrain      | LOC_C     | @Erik
7 |                               | Erik prepares, positions axe         | LOC_C     | @Erik
8 | Erik clears brush/saplings    | (now makes sense)                    | LOC_C     | @Erik
...
```

**User reviews this table → corrects → THEN prompts are written.**

### STEP 3: Location Image Generation
Each distinct location needs a reference image for Kling.

> **⚠️ CRITICAL: Location images MUST be shot at GROUND LEVEL (eye height).**
> This allows Kling to generate scenes where characters appear front-facing and naturally
> within the environment. Aerial/elevated location images result in wrong perspectives.

**Location image rules:**
- **16:9 aspect ratio**, photorealistic
- **Ground level perspective** (as if you're standing there looking ahead)
- **NO characters** in the image — just the empty environment
- **Consistent lighting** with the chapter's time of day
- **"Real photography"** — NOT CGI, NOT 3D render
- Store in: `projects/<id>/locations/`

---

### STEP 4: Visual Storyboard Chain (MANDATORY — per-scene image evaluation)

> **⚠️ CORE PRINCIPLE (tested 2026-02-19):**
> Every scene MUST have a location image evaluation. Before writing each prompt,
> compare the visual state of THIS scene vs the PREVIOUS scene. If ANYTHING changed,
> generate a NEW location image using the previous image as reference input.
> This creates an evolving visual chain — like a real film storyboard.

**The evaluation flow for EVERY scene:**
```
SCENE N:
  1. Read the State Tracker for this scene
  2. Compare against Scene N-1 state
  3. DIFF CHECK — did ANY of these change?
     □ Construction progress (more cleared, stakes added, logs stacked, walls rising)
     □ Physical objects on ground (tools, materials, structures)
     □ Lighting / time of day (morning → afternoon → golden hour → sunset)
     □ Weather (overcast → clearing → snow falling)
     □ Location entirely (truck area → forest path → clearing → cabin interior)
     □ Season/landscape evolution (early winter → deep winter)
  4. IF any box checked → GENERATE NEW IMAGE
     - Use PREVIOUS scene's image as reference input
     - Prompt: "Based on [previous image]. Modification: [what changed]"
     - This maintains visual consistency while evolving the environment
  5. IF nothing changed → REUSE previous scene's image
  6. Assign image filename to this scene's prompt metadata
```

**Image generation chain example (Chapter 1):**
```
Scene 5:  loc_005.png  ← generated from scratch (first scene at clearing)
Scene 6:  loc_005.png  ← reused (same place, same state)
Scene 7:  loc_005.png  ← reused (chopping starts but image is still "raw")
Scene 8:  loc_008.png  ← NEW (small area cleared after chopping, generated FROM loc_005)
Scene 9:  loc_008.png  ← reused (Gus scene, same clearing)
Scene 10: loc_008.png  ← reused (Erik evaluates, same state)
          ──── EDITOR: "DAY 4" CARD ────
Scene 11: loc_011.png  ← NEW (mostly cleared ground, generated FROM loc_008)
Scene 12: loc_012.png  ← NEW (stakes + twine rectangle visible, FROM loc_011)
Scene 13: loc_013.png  ← NEW (same but golden hour lighting, FROM loc_012)
Scene 14: loc_013.png  ← reused for Erik close-up, then switches to loc_d
Scene 15: loc_d.png    ← dream cabin interior (standalone)
Scene 16: loc_016.png  ← NEW (same as loc_013 but sunset light, FROM loc_013)
```

**Why this works:**
- Each image inherits the visual DNA of the previous one → consistent landscape
- Modifications are INCREMENTAL → no sudden jumps in what's visible
- The AI image generator sees the reference → maintains forest density, tree positions, ground texture
- Perfect for construction sequences where the site evolves gradually

**Image generation prompt pattern:**
```
Using the provided reference image as the base environment.
Modification: [describe what changed].
Keep everything else identical — same trees, same clearing shape, same snow coverage.
Real photography, 16:9 landscape, ground level eye-height. NOT CGI.
```

**Video prompt pattern (every scene):**
```
No music. [rest of the scene prompt]... 4K.
```
*(The reference image is attached directly in Kling — no need to mention it in the prompt text)*

**Location image triggers checklist (for automation):**
| Trigger | Example | New image? |
|---------|---------|------------|
| First scene at new location | Arriving at clearing | ✅ YES (from scratch) |
| Construction progress | More brush cleared | ✅ YES (from previous) |
| Object added to environment | Stakes + twine on ground | ✅ YES (from previous) |
| Lighting change | Afternoon → golden hour | ✅ YES (from previous) |
| Same location, same state | Two actions in same place | ❌ NO (reuse) |
| Close-up of character face | Doesn't show background | ❌ NO (reuse) |
| Dream/vision sequence | Interior of imagined cabin | ✅ YES (standalone) |

### Automation needs:
- [ ] **AI Cinematic Analyzer**: reads full chapter + identifies action gaps
- [ ] Auto-generate storyboard table for user review before prompts
- [ ] Identify all distinct locations from the text
- [ ] Auto-generate ground-level location images per location
- [ ] Auto-insert bridge scenes with appropriate realistic actions
- [ ] Auto-classify: narrated vs bridge
- [ ] Calculate total video duration = narration + bridges
- [ ] Bridge scenes get ambient-only prompts (no dialogue, no narration reference)

---

## Phase 3.5: Scene Intelligence Systems (for App Automation)

> These systems run BETWEEN the Storyboard Analysis (Phase 3) and Prompt Writing (Phase 4).
> They ensure every prompt is logically consistent, temporally realistic, and has the
> right level of detail.

### SYSTEM 1: Scene State Tracker

Every scene inherits and modifies a JSON state object. The prompt generator uses this
state to write accurate environment descriptions — preventing logical errors like showing
a fully cleared site after 2 scenes of chopping.

```json
// Example: Scene 10 state (inherited from scenes 7-9)
{
  "scene": 10,
  "environment": {
    "ground_cleared_pct": 15,
    "ground_description": "a few m² of exposed earth, 85% still dense brush",
    "brush_remaining": "thick willow thickets and saplings fill most of the marked area",
    "stakes_placed": false,
    "twine_laid": false
  },
  "tools": {
    "axe": "planted blade-down in cut stump",
    "canvas_bag": "on ground at edge of cleared patch",
    "stakes_and_twine": "inside bag, not yet used"
  },
  "character": {
    "erik": { "state": "sweaty, tired, sleeves up", "location": "standing in cleared patch" },
    "gus": { "state": "gone, left in scene 9", "location": "in the forest" }
  },
  "time_of_day": "late afternoon, amber light beginning",
  "weather": "overcast, cold, occasional wind",
  "location_image": "loc_c_building_site_partial.png"
}
```

**How it flows into prompts:**
- State `ground_cleared_pct: 15` → prompt says "a small patch of exposed ground surrounded by remaining dense brush"
- State `gus.location: "in the forest"` → Gus does NOT appear in the prompt
- State `axe: "planted in stump"` → prompt starts with Erik beside the planted axe
- State `location_image` → tells the operator WHICH reference image to attach in Kling

**Rules:**
- Each scene READS the previous state → MODIFIES it → PASSES it to the next scene
- Progress increments must be realistic: `ground_cleared_pct` goes up ~5% per chopping scene
- After a "Day X" card (editor marker), state can jump significantly (e.g., 15% → 60%)
- The prompt generator NEVER writes environment descriptions freehand — always from state

**⚠️ EVOLVING LOCATION IMAGES (tested 2026-02-19):**
> The location reference image MUST change when the environment state changes significantly.
> Kling reproduces what it sees in the reference → same image = same-looking result.
> The State Tracker evaluates BEFORE each scene whether a new location image is needed.

| State change trigger | Action |
|---------------------|--------|
| `ground_cleared_pct` crosses 0→15% | Switch from `_raw.png` to `_partial.png` |
| `ground_cleared_pct` crosses 50%+ | Switch to `_mostly_cleared.png` |
| Stakes/twine placed | Generate new image with visible markers |
| Time of day changes (dawn→dusk) | Generate new image with different lighting |
| Location changes entirely | Use different location image |

**Location image naming convention:**
```
loc_c_building_site_raw.png           ← dense brush, untouched (scenes 5-9)
loc_c_building_site_partial.png       ← some clearing visible (scenes 10-12)
loc_c_building_site_mostly_cleared.png ← after "Day X" jump (scenes post-jump)
loc_c_building_site_marked.png        ← with stakes and twine visible
```

### SYSTEM 2: Scene Count Logic (Action Decomposition)

Determines the RIGHT number of scenes by decomposing narrated actions into atomic units.

**Step 1: Extract Action Units from narration**
Break every sentence into the SMALLEST physical action:
```
Narration: "Erik drives the axe into frozen wood, clearing spruce saplings"
→ Action units:
  1. Erik grips the axe
  2. Erik swings the axe low into a sapling
  3. Sapling snaps and falls
  4. Erik kicks aside cut brush
  5. Erik moves to next sapling
  6. Repeat pattern (rhythmic work montage)
```

**Step 2: Determine which units are VISIBLE vs IMPLIED**
Not every atomic action needs its own scene. Group them:
- **Visible (own scene):** First swing, rhythmic montage, pause to rest
- **Implied (skip):** Each individual sapling (repetitive)

**Step 3: Identify GAPS between narrated actions**
```
"He parked the truck" → "He started clearing brush"
GAP: exit truck → look around → grab tools → walk to site → evaluate → prepare
= 2-3 bridge scenes
```

**Step 4: Apply the Bridge Density Rule**
| Gap type | Bridges needed | Example |
|----------|---------------|---------|
| Minor (same location, small time skip) | 0-1 | Chopping → pauses to rest |
| Medium (location change or tool change) | 1-2 | At truck → walking to forest |
| Major (different activity entirely) | 2-3 | Arrives at site → starts clearing |
| Time jump (days pass) | 1 + "Day X" card | Day 1 clearing → Day 4 more cleared |

**Step 5: Calculate total scene count**
```
Narrated scenes = number of distinct narration segments
Bridge scenes = sum of all gaps × density
Total scenes = narrated + bridges
Total video = total scenes × 15s
```

**Validation check:** If total video < 1.3× narration duration → probably missing bridges.
If total video > 2.5× narration duration → probably too many bridges, tighten.

---

## Phase 4: Video Prompt Engineering

### Mandatory metadata per prompt (for editors):
Every video prompt MUST include this header before the prompt itself:
```
SCENE [N] | [BRIDGE / NARRATED] | [duration]s
ELEMENTS: @Erik, @Gus (characters/objects to attach in Kling)
LOCATION: [location image filename to attach in Kling]
NARRATION: "[exact text excerpt that plays over this scene]"
— or —
NARRATION: none (ambient only)
```
This is **essential for editors** to know which audio segment to sync over each clip,
and **essential for Kling operators** to know which assets to attach.

### Prompt template:
```
No music. [Camera movement] of [scene description].
@Element does [action]. Cut to [new angle].
Cut to [another angle/detail].
Sound of [specific ambient sounds]. 4K.
```

### Rules learned:
1. **Always start with `No music.`** — Kling adds music by default
2. **Use `Cut to` for multi-shot** within a single prompt
3. **Reference elements as `@Name`** — `@Erik`, `@Gus`, `@Pickup`
4. **~~DON'T use reference images for locations~~** ← WRONG, corrected below:
   > **⚠️ CORRECTION (tested 2026-02-19): You MUST attach a location/scene reference image.**
   > Without it, Kling generates each scene in a completely different environment (wrong season,
   > no snow, different landscape). The reference image anchors the visual setting.
   > Characters (@elements) alone are NOT enough for consistency.
5. **Specify camera movements:** wide shot, close-up, tracking, low angle, aerial drone, panoramic
6. **Specify ambient sounds:** engine, wind, paws in snow, metallic ticking, etc.
7. **Always end with `4K.`**
8. **Scene setup in Kling — INDEPENDENT SCENES (no frame chaining):**
   > **⚠️ CORRECTION (tested 2026-02-19): Do NOT use last-frame chaining.**
   > Using last frame as start frame causes progressive quality degradation.
   > Each scene should be generated INDEPENDENTLY for maximum quality.
   - **Every scene:** Elements (characters/objects) + location reference image + prompt
   - **No start frames** — each scene stands alone
   - **Duration: 15 seconds** each (Kling max) — gives more footage, better pacing
   - **Continuity** comes from: consistent elements + same location image + consistent prompt descriptions
   - This means the editor handles visual continuity in post-production, not Kling
9. **Keep actions SIMPLE, but use as many cuts as the scene needs:**
   > **⚠️ RULE (tested 2026-02-19): The problem is complex ACTIONS, not the number of cuts.**
   > Each `Cut to` should show a SIMPLE action or angle — but you can have multiple.
   > What causes inconsistencies is multi-step physical interactions within ONE shot,
   > not the number of camera angle changes.
   - Each individual shot: 1 simple action (walk, look, swing, stand)
   - Number of cuts: **as many as cinematically needed** — plan the scene properly
   - Avoid within a single shot: dress/undress, object manipulation, multi-step sequences
   - Think like a film editor: variety of angles keeps the scene alive
10. **Sparse character dialogue — very occasionally:**
   - Once every 4-5 scenes, add a short muttered phrase ("This is the site", "Come on", "That'll hold")
   - Adds authenticity and life without breaking the documentary tone
   - Keep to 3-5 words max, spoken to themselves, never to camera
11. **Multi-image referencing for transition scenes:**
   > **⚠️ RULE (tested 2026-02-19): When a scene transitions between locations,
   > list ALL attached images numbered as @Image1, @Image2 in the metadata
   > AND reference them in the prompt text.**
   - Single location scene → `LOCATION: loc_012.png` (as usual)
   - Transition scene → list each image:
     ```
     @Image1: loc_d_cabin_interior.png (interior — fades out)
     @Image2: loc_016.png (sunset clearing — fades in)
     ```
   - In the prompt text, reference: "The warm @Image1 interior fades... transitions to @Image2 reality..."
   - This ensures the operator knows WHICH image goes WHERE in Kling
   - NEVER leave it ambiguous — always number and reference explicitly

### Two Kling modes:
| Mode | Use case | Format |
|------|----------|--------|
| **Storyboard/Omni** | Separate shots with precise timing | `Shot 1 (3s): ...` |
| **Normal/multishot** | Flowing prompt with organic cuts | `No music. Wide shot... Cut to...` |

### Presenter vs Body scenes:
| Aspect | Presenter scenes | Body/B-roll scenes |
|--------|-----------------|-------------------|
| **Narration** | First person, direct to camera | Third person voiceover |
| **Element** | `@Jack` (presenter) | `@Erik`, `@Gus`, etc. |
| **Camera** | Medium close-up, dramatic angles | Wide, tracking, aerials |
| **Dialogue** | Character speaks in quotes | No dialogue, ambient only |
| **Sound** | Voice + dramatic impacts | Ambient nature sounds |
| **Location** | Where the chapter just ended | Scene-specific (storyboard chain) |

**⚠️ PRESENTER BREAK RULES (tested 2026-02-19):**
> **Location:** The presenter is ALWAYS at the location of the chapter that just ended.
> He stands where the action happened, acknowledges what was accomplished, and
> confronts the audience with what's coming next. This is more powerful because
> the viewer SEES the real site.
>
> **Multi-scene breaks:** If the break text is >30 words, split into 2 scenes:
> - Scene A: Acknowledges what was done (at the site, looking at the work)
> - Scene B: Confronts what's coming next (shifts focus to the challenge ahead)
> Each scene gets its own video prompt with full metadata.
>
> **Tone:** Aggressive, direct, confrontational. Sports commentator meets war
> correspondent. ALWAYS names the character. Never generic.

### Automation needs:
- [ ] AI generates video prompts from: scene text + elements + location + tension level
- [ ] Different prompt templates for presenter vs body scenes
- [ ] Camera movement vocabulary matched to scene tension (calm → aerial/wide, tense → handheld/close)
- [ ] Sound design vocabulary matched to location/weather
- [ ] **Per-card AI Agent Mode (✏️)** — each scene card (storyboard + prompts) gets an agent button:
  1. User clicks ✏️ → input opens below the card
  2. User types natural language instruction: *"he's shouting too much, speak loud but don't yell"*
  3. System sends to Gemini: current prompt + director instruction
  4. Gemini returns modified prompt maintaining format (@Element, SFX, 4K, Cut to)
  5. User accepts or rejects the edit
  - Endpoint: `POST /api/project/<id>/edit-prompt-ai`
  - Payload: `{ scene_index, current_prompt, instruction }`
  - System prompt: "You are a video prompt editor. Modify the prompt following the director's instruction. Keep the format, nomenclature, and only change what is asked."

---

## Phase 5: Video Generation in Kling

### What we did manually:
1. **First clip:** Upload element images + paste prompt → generate
2. **Subsequent clips:** Take last frame of previous clip as start frame
3. **Settings:**
   - Resolution: 1080p
   - Duration: 10-15s per clip
   - Audio: Native ON (for ambient sounds)
   - Mode: depends on prompt style

### Automation needs:
- [ ] Kling API integration for programmatic video generation
- [ ] Auto-chain clips using last-frame continuity
- [ ] Store generated clips per scene with metadata
- [ ] Handle regeneration of individual scenes without breaking the chain

---

## Phase 6: Assembly (Post-production)

### What we'll need to do:
1. **Layer narration audio over video clips** (video ambient audio underneath)
2. **Trim video clips** to match narration timing (we have extra footage)
3. **Add transitions** between scenes (cuts, fades)
4. **Final render** with balanced audio mix

### Automation needs:
- [ ] FFmpeg pipeline for audio/video sync
- [ ] Auto-trim clips to match narration timing
- [ ] Audio mixing: narration at 100%, video ambient at ~30%
- [ ] Transition templates (fade, cut, crossfade)
- [ ] Final render script

---

## Observations Log

### 2026-02-18 — Session 1: Manual Intro + First Body Scene
- Tested cinematic intro prompts for Jack Harlan (helicopter sequence, 6 shots)
- Discovered "shouting" style was too aggressive → changed to calm conviction
- Generated helicopter landing scene using start frame continuity
- Changed intro prompt in `story_engine.py` from literary third-person to presenter first-person
- Generated elements for Erik, Pickup, Gus
- First pickup image looked like videogame CGI → fixed with "real photography" in prompt
- Gus originally generated as Alaskan Malamute → corrected to Bernese Mountain Dog
- Generated TTS for first narration phrase: 63 words = 24.1s at 0.75x
- Planned 4 scenes (Scene 0 establishing + 3 narration scenes) = ~40s video for 24s audio
- **Key takeaway: ALWAYS generate audio FIRST, then plan scenes around real durations**

### 2026-02-19 — Session 2: Chapter 1 Completion + Pipeline Refinements
- **Visual Storyboard Chain System** — every scene gets a location image diff evaluation. If any visual change occurs (construction, objects, lighting), a new image is generated using the previous image as reference input. Creates an evolving chain maintaining visual DNA.
- **Multi-image referencing (@Image1, @Image2)** — transition scenes (dream→reality, interior→exterior) need numbered image attachments referenced in the prompt text.
- **Location images must show physical modifications** — Kling uses the reference as visual truth. Stakes, twine, logs, walls MUST appear in the reference or they won't appear in the video.
- **No "Using the provided reference image" text needed** — attaching the image in Kling is sufficient.
- **Cut rule relaxed** — the problem is complex ACTIONS, not the number of cuts. Use as many camera angle changes as cinematically needed, keep each individual shot simple.
- **Presenter breaks: aggressive style** — always name the character, acknowledge what was done, confront with what's coming. "Sports commentator meets war correspondent, NOT a poet."
- **Presenter location rule** — always at the location of the chapter that just ended. Breaks >30 words split into 2 scenes (acknowledge + confront).
- **Generated @ErikFather element** — portrait for photo frame in dream cabin scene.
- **Chapter 1 scenes 10-17b fully planned** — including dream sequence (14-15), return to reality (16), and presenter break (17a-17b).

---

*Last updated: 2026-02-19 17:06*
