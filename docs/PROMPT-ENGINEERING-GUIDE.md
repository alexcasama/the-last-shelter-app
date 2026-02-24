# Prompt Engineering Guide — Kling 3.0 Multishot
## Reference for video prompt writing

> Extracted from top-performing Kling 3.0 prompts. Apply these patterns
> when writing video prompts for The Last Shelter.

---

## 1. Two Prompt Formats

### Format A: Flowing Narrative (single continuous camera)
Best for: aerial establishing shots, FPV sequences, action sequences.

```
[Camera movement] over [environment]. [Details of what we see].
The camera [transition verb] into [next angle/action].
[Next beat]. [Next transition]. [Final beat].
SFX: [sound 1], [sound 2], [sound 3].
[Color palette], [atmosphere], [realism style].
```

**Example (FPV forest→cabin):**
```
A wide moving aerial shot glides over a mountain forest at dawn, mist
rolling between trees. The camera suddenly tilts forward into aggressive
eagle POV, diving at extreme speed through treetops. Pine branches whip
past the lens. It levels out inches above a river, then rockets toward
a remote wooden cabin. Without slowing, it blasts through an open
doorway, weaving between wooden beams and hanging lights, and ends in
a precise lock onto a rifle mounted above the fireplace.
SFX: Wind rushing in descent, Engine roaring at full throttle.
Natural lighting, motion blur streaks, wood dust particles.
```

### Format B: Numbered Shots (multi-angle character work)
Best for: dialogue scenes, presenter scenes, emotional close-ups.

```
SHOT 1
[Frame type] on [character]. [Physical micro-details].
[Camera movement]. [Ambient detail].
[Character]:"[Dialogue]"

SHOT 2
[Frame type]. [Physical micro-details].
[Light/shadow detail].
[Character]:"[Dialogue]"

SHOT 3
[Frame type], framing [composition context].
[Micro-action]. [Breathing/body tension]. 
[Character]:"[Dialogue]"
```

**Example (tense dialogue):**
```
SHOT 1
Tight frontal close-up on Character A (male, late 50s).
Sweat beads on his temple. Jaw tight. Eyes locked forward.
Camera slow push-in. Lamp hums softly.
A:"You're staring at me like you already decided."

SHOT 2
Profile close-up of Character B (female, early 30s).
Perfect stillness. No blink. Slight curl at the corner of her mouth.
Light cuts sharply across her cheekbone.
B:"No. I'm staring because you're about to contradict yourself."
```

### Format C: Scene-Based (cinematic multi-scene with style tags)
Best for: epic sequences, environmental storytelling, wildlife.

```
Scene 1 – [Shot type]: [full description].
Lighting: [specific lighting]. Cinematic style: [mood/pace].

Cut to Scene 2 – [Shot type]: [full description].
Lighting: [specific lighting]. Cinematic style: [mood/pace].

Cut to Scene 3 – [Shot type]: [full description].
Lighting: [specific lighting]. Cinematic style: [mood/pace].
```

---

## 2. Camera Movement Vocabulary

### Aerials & Establishing
| Movement | When to use | Example |
|----------|-------------|---------|
| **Wide aerial sweep** | Opening/establishing | "camera sweeps slowly over frozen ridges" |
| **Aggressive eagle POV dive** | High-energy transition | "tilts forward into aggressive eagle POV, diving through treetops" |
| **Slow descending aerial** | Revealing a location | "aerial drone shot slowly descending toward a ruined cabin" |
| **Ultra-wide to fast plunge** | Epic scale → focused detail | "ultra-wide aerial begins miles above snowy peaks, then plunges into a fast dive" |

### Character Work
| Movement | When to use | Example |
|----------|-------------|---------|
| **Slow push-in** | Building tension/intimacy | "Camera slow push-in" on tight close-up |
| **Controlled 360° orbit** | Power/isolation | "a slow, controlled 360° orbit circles a tall figure" |
| **Over-the-shoulder** | Dialogue tension | "Over-the-shoulder from B, framing A smaller" |
| **Handheld backward tracking** | Character advancing toward camera | "aggressive handheld backward tracking shot, shaking violently" |
| **Profile close-up** | Internal emotion | "Profile close-up, perfect stillness" |

### Lens & Speed Dynamics
| Technique | When to use | Example |
|-----------|-------------|---------|
| **Focal length compression** | Dramatizing scale/distance | "focal length tightens dramatically, compressing the mountains together visually" |
| **Sudden acceleration** | Energy burst, transition | "camera begins in silence, then suddenly accelerates forward at impossible velocity" |
| **Hyperspeed push-in** | Rush toward subject | "stars stretching into light trails" (for snow: snowflakes streaking) |
| **Brutal dynamic zoom** | Final lock onto detail | "finishes with a brutal dynamic zoom into the illuminated window" |

**Transition chain notation** (use as prompt summary/footer):
```
Deep ultra-wide → hyperspeed push-in → perspective compression → crash zoom
Mountain glide → forest dive → river skim → cabin breach → rifle lock
```

### Action & Transitions
| Movement | When to use | Example |
|----------|-------------|---------|
| **FPV weaving** | Through architecture/forest | "blasts through open doorway, weaving between wooden beams" |
| **Fast lateral tracking** | Parallel to action | "Camera skims along the ridgeline parallel to the tracks" |
| **Rapid climb reveal** | Revealing massive scale | "End with a rapid climb revealing the avalanche swallowing the pass" |
| **Wide arc** | Keeping two subjects in frame | "swings into a wide arc that keeps both the train and avalanche visible" |

---

## 3. Micro-Detail Vocabulary (for character close-ups)

These sell the emotion. Use 2-3 per shot:

### Tension/Fear
- "Sweat beads on his temple"
- "Jaw tight"
- "Eyes locked forward but blinking too fast"
- "His hands tighten, knuckles whitening"
- "Breathing audible"
- "A swallows"
- "expression unreadable, breath faintly visible in the cold air"

### Determination/Intensity
- "Eyes fixed forward"
- "He leans forward"
- "Gestures cutting through the air"
- "Counts on his fingers"
- "Plants his feet"
- "Hands gripping forward"

### Stillness/Presence
- "Perfect stillness. No blink"
- "Slight curl at the corner of her mouth"
- "He remains perfectly still"
- "A quiet smile that never reaches her eyes"
- "A slow inhale"

---

## 4. SFX Block Patterns

Always close the prompt with sound effects. Format:
```
SFX: [primary sound], [secondary sound], [ambient detail].
```

### Yukon/Wilderness sounds:
- "Icy wind cutting through trees"
- "Snow crunching under boots"
- "Deep layered crow caws echoing in the forest"
- "Heavy wing flaps close to camera"
- "Distant branch creaking under weight"
- "Subtle fabric movement in the cold air"
- "Wind howling faintly"
- "Crunching ice"

### Helicopter/Vehicle sounds:
- "Rotor blades pounding heavily"
- "Wind rushing in descent"
- "Engine roaring at full throttle"
- "Rotor wash blowing snow outward"

### Construction/Work sounds:
- "Axe striking wood"
- "Metal tools clinking"
- "Heavy boots on frozen ground"
- "Rope creaking under tension"

---

## 5. Aesthetic Tail Tags

End every prompt with palette + atmosphere + realism level:

### Cold/Winter palettes (The Last Shelter primary):
- "Cold blue-gray palette, dense volumetric fog, high-contrast gothic realism"
- "Natural cold tones with soft backlight from the pale sun"
- "Diffused blue-gray daylight with subtle glimmers of ice reflection"
- "Cold desaturated tones, gritty cinematic realism"
- "Twilight blue glow reflecting on ice"

### Warm/Flashback palettes (for father's memories):
- "Warm amber tones, soft diffused lighting, nostalgic film grain"
- "Golden hour warmth, visible dust particles, vintage documentary feel"

### Epic/Dramatic palettes:
- "Deep structural rumble, dense dust clouds, intense blockbuster realism"
- "Warm golden sunset light cutting through smoke, high-intensity chaotic cinematic realism"

---

## 6. Cinematic Style Tags

Add after lighting to define the feel:
- **Majestic/serene:** "majestic, slow, and hauntingly serene"
- **Intimate/isolated:** "intimate and immersive, emphasizing texture and isolation"
- **Epic/emotional:** "epic, emotional finale with a sense of reverence and mystery"
- **Gothic/oppressive:** "slow oppressive atmosphere"
- **Documentary/raw:** "raw documentary realism, handheld texture"

---

## 7. Applying to The Last Shelter

### Presenter scenes (Jack)
Use **Format B (Numbered Shots)** with micro-details:
```
SHOT 1
Medium close-up on @Jack (male, 45, salt-pepper hair, green canvas jacket).
Headset on, jaw set, eyes scanning the landscape below.
Camera slow push-in. Helicopter rotors thudding.
@Jack speaks: "In this first episode..."

SHOT 2  
Wider angle from backseat, @Jack turns to camera.
He leans forward with urgent energy, hand gesturing.
Cold light from window catches his profile.
@Jack speaks: "...the most dangerous survival challenge..."
```

### Bridge/Establishing shots
Use **Format A (Flowing Narrative)** with FPV or aerial:
```
No music. A wide aerial sweep glides over endless Yukon 
wilderness at dawn. Frozen ridges stretch toward massive 
snow-capped peaks. A tiny helicopter crosses the valley below. 
The camera holds wide, letting the immensity dwarf everything.
SFX: Icy wind cutting through open terrain, distant bird calls.
Diffused blue-gray daylight, majestic and hauntingly serene. 4K.
```

### Flashback scenes (father)
Use **Format A** with warm aesthetic tail:
```
No music. A lone figure (@James) walks through virgin boreal 
forest, heavy pack on his back, axe strapped to the side. 
He stops at a small clearing and looks around slowly, breathing 
visible in the cold air. His expression shifts from exhaustion 
to quiet determination. He drops his pack.
SFX: Boots crunching through undergrowth, distant river.
Warm amber tones, soft diffused lighting, vintage film grain. 4K.
```

### Anticipatory B-roll (Erik teaser)
Use **Format A** with episode's main palette:
```
No music. @Erik stands at the edge of a snow-covered clearing, 
surveying the terrain. Dense boreal forest of dark spruce 
surrounds him. He paces the perimeter with deliberate steps, 
measuring distances. Wind pulls at his jacket.
SFX: Snow crunching under boots, icy wind.
Cold blue-gray palette, natural cold tones, documentary realism. 4K.
```

---

*Last updated: 2026-02-23*
