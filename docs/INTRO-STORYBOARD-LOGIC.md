# Intro Storyboard Logic
## Rules for generating the visual intro sequence

> **Context:** The intro is NOT a chapter — it has no construction sequence,
> no physical actions to decompose. Instead, it's a **presenter monologue**
> that must be broken into visually varied scenes using emotional beats.

---

## 1. Scene Types in the Intro

| Type | When to use | Visual treatment | Audio |
|------|-------------|-----------------|-------|
| **Bridge ambiental** | Opening shot, transitions, pauses | Epic landscape, aerial | Ambient only, no voice |
| **Presenter** | Jack speaks directly to camera (lip sync) | Medium/close-up, helicopter or on-location | Jack's voice, synced |
| **Flashback** | Jack references the PAST (events that already happened) | Heavier grain, warm/sepia tones | Jack's voice as off-screen narration |
| **B-roll anticipatorio** | Jack describes the FUTURE challenge | Same visual style as the episode body | Jack's voice as off-screen narration |

**Decision logic:**
```
IF narration references the past → Flashback B-roll
IF narration describes future challenge/danger → Anticipatory B-roll  
IF narration is direct hook/confrontation → Presenter (lip sync)
IF no narration (transition/pause) → Bridge ambiental
```

---

## 2. Segmentation by Emotional Beats

Don't cut narration by sentences. Cut by **emotional shifts**:

1. **Hook** (excitement, grab attention) → Presenter
2. **Conflict introduction** (gravity, death) → Presenter
3. **Backstory** (nostalgia, hope, tragedy) → Flashback sequence
4. **Emotional pause** (devastation) → Silent bridge
5. **Urgency** (time pressure, danger) → Presenter + Anticipatory B-roll
6. **Threat visualization** (what happens if fail) → Anticipatory B-roll
7. **Climax question** (can he do it?) → Presenter
8. **Tagline** (epic close) → Presenter

---

## 3. Rhythm Rules

- **Never more than 2-3 consecutive scenes of the same type**
- **After emotional tension → insert silence** (bridge with no voice)
- **Flashbacks go as a grouped block** (3 scenes max, don't scatter them)
- **Scene 1 = always an establishing shot** (geographic context)
- **Last scene = always presenter looking at camera** (tagline)
- **Anticipatory B-roll breaks up long presenter monologues** (pull text out as voice-over)

---

## 4. Duration Estimation

| Scene type | Typical duration | Calculation |
|-----------|-----------------|-------------|
| Presenter (lots of text) | 10-15s | ~2.5 words/second |
| Presenter (short text) | 5-8s | ~2.5 words/second |
| Bridge ambiental | 5-8s | Fixed |
| Flashback with voice-over | ~5s per beat | ~2.5 words/second |
| Anticipatory B-roll with voice-over | ~5s per beat | ~2.5 words/second |

**Total intro target:** 90-120 seconds (~1:30 to 2:00)

---

## 5. Splitting Presenter Monologues into B-roll

When a presenter scene has >30 words (>12 seconds), evaluate:
1. Can part of the text be **shown** instead of told?
2. If YES → extract that portion as voice-over on B-roll
3. Keep the emotional core as presenter (lip sync)

**Example:**
```
BEFORE (1 scene, 15s):
  Jack: "ONLY 90 days before winter becomes a killing machine.
         Ninety days before temperatures drop to minus 40.
         Before blizzards bury everything under meters of snow."

AFTER (2 scenes):
  Scene 8 (Presenter, 5s): Jack: "ONLY 90 days before winter becomes a killing machine."
  Scene 9 (B-roll anticipatorio, 5s): [tormenta] voice-over: "Before blizzards bury everything..."
```

---

## 6. Element & Image Tracking

For each scene, track:
- **Characters needed:** `@Jack`, `@James`, `@Erik`
- **Location image:** what reference to attach in Kling
- **Is reference image downloadable?** (for the operator)

Flashback scenes need:
- A reference image of the character (e.g., `@James`)
- A location image showing the past environment (cabin under construction, not in ruins)

Anticipatory B-roll needs:
- Character references if characters appear (`@Erik`)
- Location images from the episode body (reuse from Chapter 1 when available)

---

## 7. Applied Example: Episode 1 Intro (14 scenes, ~101s)

| # | Type | Visual | Dur. | Narration |
|---|------|--------|------|-----------|
| 1 | Bridge ambiental | Aérea Yukon, helicóptero a lo lejos | ~8s | *(ambiente)* |
| 2 | Presenter | Jack en helicóptero, se gira a cámara | ~12s | "In this first episode, we're heading into the wild Yukon wilderness. We're going to show you one of the most dangerous survival challenges you've ever seen." |
| 3 | Presenter | Jack señala abajo, sombrío | ~8s | "Two years ago, a war veteran named James Lindqvist died. But before he left, he made his son Erik one final promise: finish the cabin." |
| 4 | Flashback | James llegando solo al Yukon | ~5s | *(v/o)* "Fifteen years ago, James came here seeking peace and escape." |
| 5 | Flashback | James cortando troncos, construyendo | ~5s | *(v/o)* "He wanted to build a place where he could leave behind the demons of war." |
| 6 | Flashback | James enfermo contra cabaña a medio hacer | ~5s | *(v/o)* "But a terrible illness took him before he could finish. He died knowing his dream was in ruins." |
| 7 | Bridge ambiental | Ruinas cubiertas de nieve, aérea | ~5s | *(SILENCIO TOTAL)* |
| 8 | Presenter | Jack agresivo en helicóptero | ~10s | "Now Erik is here to face something absolutely insane. He has the skills, he has the experience. But what he doesn't have is time." |
| 9 | B-roll anticipatorio | Erik evaluando terreno nevado | ~5s | *(v/o)* "ONLY 90 days before winter becomes a killing machine. Ninety days before temperatures drop to minus 40." |
| 10 | B-roll anticipatorio | Tormenta azotando árboles | ~5s | *(v/o)* "Before blizzards bury everything under meters of snow." |
| 11 | Presenter | Jack máxima intensidad | ~10s | "This won't be a game. Erik has to build a functional cabin from scratch. He has to light a fire that keeps him alive. And he has to survive alone in one of the most hostile environments on the planet." |
| 12 | B-roll anticipatorio | Erik solo con hacha frente a bosque, espalda a cámara | ~5s | *(v/o)* "Because if he fails, he's trapped. No shelter, no heat, no way out." |
| 13 | Presenter | Jack baja del helicóptero | ~10s | "Can he really do it? Can one man build from scratch what his father couldn't? Or will the Yukon destroy him?" |
| 14 | Presenter | Jack frente a ruinas, pausa épica | ~8s | "This is about to begin. This is The Last Shelter." |

---

*Last updated: 2026-02-23*
