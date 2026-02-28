# CHANGELOG — The Last Shelter · Story Engine

---

## 2026-02-28 — Storyboard Break Generation & Rendering Fixes

### 🐛 Bug Fixes
**Backend (`app.py`)** & **Frontend (`storyboard.js`)**
- **Phantom Break Blocks Removed**: Fixed a UI bug in `storyboard.js` where a visual "Break" block was unconditionally rendered after every single chapter phase. The UI now strictly checks the `narration.json` file to see if a break actually exists for a specific phase (using `after_phase_index`) before rendering the block.
- **Dynamic Fallback Break Generation**: Fixed a crash (`Index out of range`) in `app.py` when the frontend requested a break index that didn't exist in the pre-generated `narration.json`. 
- **Context-Aware Fallback**: If a requested break index is missing, the backend now dynamically queries the Gemini API on the fly to generate a unique, contextually accurate short Break script. The prompt explicitly feeds Gemini the exact phase that was just completed and the one that is about to start to ensure 100% temporal consistency.

---

## 2026-02-24 — Prompt Generation Rules + UI Polish + Edit Elements

### 🎬 Video Prompt Generation — Rule Refinement
**Backend (`app.py`)**
- **Non-Presenter Narration**: Removed instructions to include "Voice-over narration" text for bridge, flashback, anticipatorio, and chapter action scenes. This ensures Kling focuses 100% on pure visual cinematic action, as Voice-overs are added in post-production.
- **Cinematic Quality Enforcement**: Strengthened instructions forcing Gemini to match the exact density, hyper-specific sensory details, and multishot structure of the reference examples.
- **Location Image Naming Conventions**: Fixed how Kling is instructed to reference location images. If there is only one layout image, it uses `@Image`. If there are multiple, it numbers them `@Image1`, `@Image2`, etc.
- **Existing Prompts Fix**: Ran a backend Python script to retroactively update all Chapter 1 `storyboard.json` prompts to use `@Image` for single layout images.

### ✏️ Element Image Editing
**Backend (`story_engine.py`, `app.py`)** & **Frontend (`index.html`, `app.js`)**
- Added an **"Edit Image"** UI feature for Elements (Characters, Objects, Vehicles).
- Automatically triggers a backend AI revision of the `frontal_prompt`, maintaining the strict constraint of rendering elements against a clean white portrait background.
- UI Modal added alongside location edits to allow inputting custom revision instructions, viewing the current prompt, and auto-refreshing the element image upon completion.

### 🖼️ Cross-Chapter Location Referencing
**Backend (`app.py`)** & **Frontend (`storyboard.js`)**
- Upgraded the "Regenerate Image" modal for locations to allow referencing any previously generated image from the entire project.
- The reference image dropdown now aggregates images across all Intros, Chapters, Breaks, and Closes, correctly labeled by their origin.
- The backend API (`/api/project/<project_id>/edit-location-image`) was updated to dynamically locate reference images from different block folders, ensuring visual consistency across the entire episode.

### ✨ UI and Sidebar Tweaks
**Frontend (`index.html`, `app.js`, `storyboard.js`, `style.css`, `storyboard.css`)**
- **Collapsible Storyboard Blocks**: Implemented a lazy-loading accordion UI for the Storyboard view. Blocks now load collapsed by default, drastically saving memory by deferring the DOM creation and image loading of hundreds of scenes until the block is explicitly expanded.
- **Global Expand/Collapse All**: Added a generic toggle button to the top-bar navigation that expands or collapses every block in the project simultaneously with visual hover feedback.
- **Individual Block Toggles**: Replaced default emojis with discrete UI ghost buttons styled as `▼ Expand` / `▲ Collapse`, relocated to the right-hand actions area of each block header. Clicking anywhere on the block header also triggers expansion.
- **Sidebar Cleanup**: Removed the `duration` and `elements_generated` system status badges from project cards for a cleaner interface.
- **Text Wrapping**: Allowed long Episode Titles in the sidebar to wrap natively onto two lines using `-webkit-line-clamp`.
- **Button Feedback**: Added visual feedback (disabled state + "⏳ Generating..." text) when the "Regenerate Prompts" button is clicked in the storyboard workflow, and auto-expands the block on click.
- **Storyboard Labels**: Fixed hardcoded label rendering so that single images read as `@Image` instead of `@Image1` in the prompt image captions and Modal headers.

### 🐛 Parsing Bug Fix
**Frontend & Backend (`storyboard.js`, `app.py`)**
- Fixed Regex parsing to correctly handle possessives and map complex elements to simple `prompt_names` (e.g. `@Erik's Old Ford Pickup` → `@Pickup`).

---

## 2026-02-20 — Elements Refinement + Portrait Style + Lightbox Fixes

### 🧩 Elements System — Refinement for Kling

**`elements.json` (project data)**
- **Removed** 3 non-element items: "The Cabin Ruins", "Pile of Firewood", "Chainsaw" — relegated to scenario/environment
- **Added** 2 inherited characters: **Erik's Father** (manual image upload) and **Erik's Uncle** (generated portrait)
- Final element list: 6 items (3 characters, 1 vehicle, 1 object, 1 companion animal)

**Element Categories for Kling:**
| Category | Includes | NOT included |
|----------|----------|-------------|
| character | People, animals | — |
| vehicle | Trucks, ATVs, canoes | — |
| object | Tents, stoves, backpacks | Ruins, firewood, generic tools |

### 🖼️ Character Portraits — Close-Up Style

**`story_engine.py` — `analyze_elements()` prompt**
- **Before**: "Full body portrait, standing pose, head to toe visible"
- **After**: "Close-up chest-up portrait, shoulders and head visible, sharp focus on face"
- Added separate prompt template for companion animals (head + shoulders)
- Updated example prompt to match close-up style

### 🐛 Lightbox Bug Fixes

**`static/app.js` — `renderElements()`**
- **Quote escaping**: Labels with apostrophes (e.g. "Erik's Father") broke `onclick` handlers. Added `safeLabel` with single-quote escaping

**`static/app.js` — `regenerateElement()`**
- **Stale image after regenerate**: `onclick` handler kept old cached URL after regeneration. Now updates both `img.src` and `onclick` with new timestamped URL

### 🔧 UI Fix — Elements Expand Button

**`templates/index.html`**
- Added missing `btnCollapseElements` button to Elements section header

**`static/app.js` — `loadProject()` + `toggleStepButtons()`**
- Added `btnCollapseElements` to default-collapsed list and step completion visibility logic

### 📁 Files Modified

| Archivo | Cambios |
|---------|---------|
| `story_engine.py` | Portrait prompts → close-up style, companion animal template |
| `static/app.js` | Lightbox quote fix + regenerate onclick fix + expand button logic |
| `templates/index.html` | Added collapse button for Elements section |
| `elements.json` | Refined to 6 elements with updated close-up prompts |

---

## 2026-02-17 Night — ElevenLabs Voice Engine + Show Settings Voice Controls

### 🎙️ Voice Engine — ElevenLabs v3 TTS Pipeline

**`voice_engine.py`** [NUEVO] — Motor de voz completo (370+ líneas)
- **`enhance_narration_for_tts()`**: Usa Gemini Flash para inyectar audio tags (`[sighs]`, `[whispers]`, `[exhales]`, `[inhales deeply]`, etc.) y puntuación expresiva (CAPS, `...`, `—`) en el texto de narración antes de enviarlo a ElevenLabs
- **`generate_audio_segment()`**: Genera audio MP3 usando ElevenLabs v3 con VoiceSettings configurables (stability, speed)
- **`generate_all_audio()`**: Pipeline completo que procesa intro → fases → breaks → close con SSE progress streaming

**Parámetros finales (tras A/B testing)**:
| Parámetro | Valor | Alternativas testeadas |
|-----------|-------|----------------------|
| **Modelo** | `eleven_v3` | v3 DPO (descartado) |
| **Stability** | `0.5` (Natural) | 0.0 Creative, 1.0 Robust |
| **Speed** | `0.75` | 1.0, 0.85 |

**Descubrimientos del A/B testing**:
- v3 solo acepta stability `0.0` (Creative), `0.5` (Natural), `1.0` (Robust) — valores intermedios dan error `invalid_ttd_stability`
- `eleven_v3` base sonó mejor que `eleven_v3_dpo_20260217` (DPO) para narración cinematográfica
- Speed `0.75` da ritmo pausado ideal para documentales (1.0 sonaba apresurado)
- Stability `0.5` (Natural) mejor balance que `0.0` (Creative) que era demasiado errático

### ⚙️ Show Settings — Migración a ElevenLabs Voice Controls

**Eliminado**: Campo `kling_voice_formula` (texto libre para Kling 3 TTS)

**Añadido**: 3 controles de voz ElevenLabs:
- **Voice Model** (dropdown): `eleven_v3` (recommended), `eleven_v3_dpo_20260217` (experimental), `eleven_multilingual_v2`
- **Stability** (dropdown): Creative (0.0), Natural (0.5), Robust (1.0)
- **Speed** (slider): 0.70 – 1.20 con feedback visual en tiempo real

**Archivos modificados**:
- `config/show_settings.json`: Reemplazado `kling_voice_formula` con `elevenlabs_model`, `elevenlabs_stability`, `elevenlabs_speed`
- `templates/index.html`: Modal con dropdown de modelo, dropdown de stability, slider de velocidad
- `static/app.js`: `loadShowSettings()` y `saveShowSettings()` actualizadas para los nuevos campos
- `static/style.css`: `.form-row` layout para stability + speed side-by-side
- `app.py`: Defaults y keys de guardado actualizadas

### 📦 Dependencias

- `elevenlabs>=1.0.0` añadido a `requirements.txt` (instalado v2.36.0)
- `ELEVENLABS_API_KEY` añadido a `.env`

### 📁 Archivos Modificados/Nuevos

| Archivo | Tipo | Cambios |
|---------|------|---------|
| `voice_engine.py` | NEW | Motor de voz ElevenLabs v3 (enhance + generate + pipeline) |
| `test_voice.py` | NEW | Script de prueba para validar enhance → TTS pipeline |
| `requirements.txt` | MODIFY | Añadido `elevenlabs>=1.0.0` |
| `config/show_settings.json` | MODIFY | Kling formula → ElevenLabs params (model, stability, speed) |
| `templates/index.html` | MODIFY | Modal con dropdowns y slider de voz |
| `static/app.js` | MODIFY | Load/save de nuevos campos de voz |
| `static/style.css` | MODIFY | Layout `.form-row` para controles side-by-side |
| `app.py` | MODIFY | Defaults y keys de show-settings actualizadas |

---

## 2026-02-17 — Show Settings + Presenter Identity (Jack Harlan)

### ⚙️ Show Settings — Global Presenter Configuration

**Backend (`app.py`)**
- **`GET /api/show-settings`**: Carga config global del presentador desde `config/show_settings.json`
- **`POST /api/show-settings`**: Guarda nombre, Voice ID, y Voice Formula
- **`POST /api/show-settings/upload`**: Upload de imagen turnaround del presentador a `config/presenter/`
- **`GET /config/presenter/<filename>`**: Sirve imágenes de referencia del presentador

**Frontend (`index.html`, `app.js`, `style.css`)**
- **Botón ⚙️ en header**: Acceso rápido a Show Settings desde cualquier vista
- **Modal Show Settings**: Panel con campos de nombre, turnaround (drag & drop + preview), Voice ID y Voice Formula
- **Persistencia**: Valores se guardan en JSON y se restauran al reabrir

**Config**
- **`config/show_settings.json`** [NUEVO]: Almacena nombre, turnaround_image, elevenlabs_voice_id, kling_voice_formula
- **`config/presenter/`** [NUEVO]: Directorio para imágenes de referencia del presentador

### 🎙️ Presenter Identity — Jack Harlan

- **Nombre**: Jack Harlan — presentador de campo, mid-40s, estilo rugged adventure host
- **Voice Design (ElevenLabs)**: Voz natural, off-the-cuff, con respiraciones sutiles, vocal fry, variaciones de volumen. Anti-robótico: "unscripted", "not performing for a microphone"
- **Voice ID**: `tkPQHnQfmFvyE5X9juYK` (configurado en Show Settings)
- **Visual Prompt (Nano Banana Pro)**: Ropa limpia de aventura profesional (olive hiking jacket, fleece collar, charcoal henley), shot on Canon EOS R5, handheld camera feel
- **Turnaround**: `jack-harlan.png` subido como referencia principal

### 🖼️ YouTube Banner — Prompt Design

- Prompt completo para banner apaisado 16:9 (2560x1440) estilo Bear Grylls / Alone
- Pose dinámica de Jack en acción (mid-stride, gesturing)
- Logo "THE LAST SHELTER" con tipografía forjada/erosionada + "WITH JACK HARLAN"
- Color grading teal-and-orange cinematográfico (referencia Fincher/Deakins)
- Variante con A-frame survival shelter en mid-distance

### 📁 Archivos Modificados

| Archivo | Tipo | Cambios |
|---------|------|---------|
| `app.py` | MODIFY | 4 nuevos endpoints de Show Settings |
| `templates/index.html` | MODIFY | Botón ⚙️ en header + modal completo |
| `static/app.js` | MODIFY | Funciones open/close/load/save/upload + drag-drop |
| `static/style.css` | MODIFY | Estilos modal, upload zone, header settings |
| `config/show_settings.json` | NEW | Config global del presentador |
| `config/presenter/` | NEW | Directorio de imágenes de referencia |

### 🔧 Story Engine — Refactoring para Pipeline Kling 3

**Backend (`story_engine.py`)**
- **Eliminado**: `generate_scenes_from_narration()` — el antiguo scene breakdown escena-a-escena
- **Nuevo**: `analyze_elements()` — analiza story + narration para identificar Elements (personajes, objetos, entornos) para Kling 3 reference-to-video
- **Eliminado**: `generate_scene_image_prompts()`, `evaluate_image_prompt_continuity()`, `fix_weak_image_prompt_transitions()` — reemplazados por pipeline de Scene Prompts unificado
- **Eliminado**: `generate_video_prompts()`, `evaluate_video_prompt_continuity()`, `fix_weak_video_prompt_transitions()` — reemplazados por video prompts integrados en scene prompts
- **Eliminado**: `generate_character_references()`, `generate_image_with_ref()` — reemplazados por Elements system

**Backend (`app.py`)**
- Limpieza de endpoints obsoletos del pipeline anterior (scenes, prompts, transitions, character refs)
- Simplificación de rutas para alinearse con el nuevo pipeline de 6 pasos

### 📖 STORY_DNA — Modelos Emocionales por Tipo de Episodio

**`STORY_DNA.md`**
- **[NUEVO]** Sección completa de **Modelos Emocionales por Tipo de Episodio** — 8 modelos distintos:
  - `build` → Future Vision (7 capas de integración)
  - `full_build` → Future Vision + Mastery
  - `rescue` → Loss & Recovery
  - `restore` → Heritage Connection
  - `survive` → Primal Anchor
  - `critical_system` → Engineering Desperation
  - `underground` → Obsessive Vision
  - `cabin_life` → Present Moment
- Cada modelo incluye capas específicas de integración, reglas de detalles sensoriales, y escalación de stakes
- Basado en el modelo "Aron Ralston / 127 Hours" de Future Vision como patrón base

### 🎙️ Narration Style — Frases Cinematográficas

- **Cambio de estilo narrativo**: frases cinematográficas compuestas (15-35 palabras) como default
- Frases cortas (5-12 palabras) reservadas SOLO para turning points y momentos de crisis
- Mejora el flujo narrativo y elimina el efecto "choppy" del estilo anterior

### 📚 Documentación Nueva

| Archivo | Tipo | Contenido |
|---------|------|-----------|
| `STORY_ENGINE_IMPROVEMENT_METHODOLOGY.md` | NEW | 623 líneas — Metodología "Future Vision" completa, framework de 7 capas, checklist de integración, adaptación por tipo de episodio |
| `PIPELINE_PROPOSAL.md` | NEW | Pipeline final de 6 pasos: Story → Narration → Voice (ElevenLabs) → Elements → Scene Prompts → Generation (Kling 3) |
| `STORY_NARRATION_ENGINE.md` | NEW | Documentación técnica del motor de historias y narración: modelos, prompts, word budget, quality gate |
| `TITLE_FORMULA.md` | NEW | Fórmulas de títulos virales y patrones probados |
| `TOP_5_EPISODES.md` | NEW | Top 5 episodios potenciales con keywords y tipos |

### 🗑️ Archivos Eliminados

| Archivo | Razón |
|---------|-------|
| `templates/storyboard.html` | Migrado a flujo de trabajo separado con G-Labs Automation |

---

## 2026-02-16 — Storyboard System + Image Reload + Per-Scene Prompt Regen

### 🖼️ Storyboard — New Dedicated Page

**Backend (`app.py`)**
- **`GET /project/<id>/storyboard`**: Nueva página de storyboard con vista de scene cards
- **`GET /api/project/<id>/storyboard/state`**: API para leer estado del storyboard (variaciones, selecciones, aprobaciones)
- **`POST /api/project/<id>/storyboard/select-image`**: Selección de variación para Frame A/B
- **`POST /api/project/<id>/storyboard/regenerate-image`**: Regeneración de imágenes por escena o frame individual
- **`POST /api/project/<id>/storyboard/regenerate-prompt`**: **[NUEVO]** Regeneración de image prompts para una sola escena — llama a Gemini solo para esa escena, merge en `prompts.json`
- **Backend clear on regen**: Al iniciar regeneración de imágenes, el state backend limpia las variaciones antiguas (`frame_a_variations = []`, `frame_b_variations = []`) ANTES de lanzar el thread. Esto evita que el polling del frontend detecte imágenes viejas.

**Frontend (`templates/storyboard.html`)** — **[ARCHIVO NUEVO]**
- **Scene cards**: Vista completa con Frame A, Frame B, variaciones, selección, aprobación
- **Variation grids**: Grid de 4 variaciones por frame con selección mediante click
- **Cache-busting**: Todas las URLs de imagen incluyen `?t=timestamp` para forzar recarga tras regeneración
- **Prompt display**: Prompts de Frame A y Frame B visibles y editables por click
- **Video prompt display**: Sección azul con video prompt de Kling
- **Duration input**: Duración editable por escena
- **Approval toggle**: Checkbox de aprobación por escena

### 🔄 Image Reload Fix — Polling Mechanism

**Frontend (`storyboard.html`)**
- **`pollForNewImages(sceneNum, frame)`**: **[NUEVO]** Reemplaza dependencia en SSE para recargar imágenes. Consulta `/storyboard/state` cada 2s hasta detectar nuevas variaciones, luego recarga el scene card con cache-busting
- **`regenerateScene()`**: Usa polling en lugar de SSE para detectar nuevas imágenes
- **`regenerateSingleFrame()`**: Usa polling para detectar nuevas imágenes del frame específico
- **`loadSceneState()`**: Incluye `window._imgCacheBust = Date.now()` para forzar recarga
- **`buildVariationGrid()`**: Aplica cache-busting a todas las URLs de imagen

### 📝 Per-Scene Prompt Regeneration

**Frontend (`storyboard.html`)**
- **Botón "📝 Regen Prompt"**: Nuevo botón por scene card que regenera image prompts solo para esa escena
- **`regenerateScenePrompt(sceneNum)`**: **[NUEVO]** Llama a la API, muestra spinner giratorio en los prompt divs ("🔄 Regenerating prompt..."), y recarga la página al completar
- **Visual feedback**: Prompt areas muestran spinner amarillo durante generación → "✅ Updated! Reloading..." en verde al completar

### 🎨 Object Consistency Rules

**Backend (`story_engine.py`)**
- **Regla 13 — OBJECT & PROP CONSISTENCY**: Todo objeto descrito en Frame A debe usar exactamente los mismos adjetivos descriptivos en Frame B (edad, color, condición, tamaño, material)
- **Regla 14 — RE-DESCRIBE**: Cada prompt se renderiza independientemente — Frame B debe re-describir todos los objetos clave sin asumir que se leyó Frame A
- **Regla 15 — INVENTORY**: Mantener inventario mental de todos los props (vehículos, armas, contenedores, ropa, estructuras) y usar adjetivos idénticos

### 🔧 SSE Stale Events Fix

**Backend (`app.py`)**
- **Progress stream cleanup**: `GET /api/project/<id>/progress` ahora limpia `_progress_streams[project_id]` al abrir nueva conexión SSE. Antes, eventos `complete` sobrantes de operaciones anteriores se leían inmediatamente, causando que modales mostraran "✅ All done!" al instante

### 🎬 Video Generation UI Improvements

**Frontend (`storyboard.html`)**
- **Frame selection validation**: Modal que lista escenas con frames no seleccionados antes de generar videos
- **Video prompt spinner**: Al generar video prompts, cada scene card aprobada muestra "🔄 Generating video prompt..." en amarillo con animación
- **Button states**: Botón "Generate Video Prompts" se deshabilita y muestra spinner durante generación

### 📁 Archivos Modificados

| Archivo | Tipo | Cambios |
|---------|------|---------|
| `app.py` | MODIFY | Nuevos endpoints: regenerate-prompt, SSE cleanup, backend state clear on regen |
| `story_engine.py` | MODIFY | Reglas 13-15 de consistencia de objetos en image prompts |
| `templates/storyboard.html` | NEW | Página completa de storyboard con polling, prompt regen, spinners |

---

## 2026-02-14 Night — Frame A/B Image Prompts + Video Prompts + Continuity Systems

### 🖼️ Image Prompts — Reescritura Frame A / Frame B

**Backend (`story_engine.py`)**
- **`generate_scene_image_prompts()`**: Reemplaza `generate_phase_prompts()` — genera **2 prompts por escena** (Frame A = apertura, Frame B = cierre)
- **Regla 12 — Continuity Chaining**: Frame B(N) = Frame A(N+1) — misma imagen, misma pose, misma ropa
- **Cross-chapter bridge**: El último Frame B de cada capítulo se pasa como contexto al primer Frame A del capítulo siguiente
- **Batched por capítulo**: 1 llamada API por capítulo (max_tokens=20000)
- **Auto-evaluación**: `evaluate_image_prompt_continuity()` se ejecuta al final automáticamente

### 🎬 Video Prompts — Acción Frame A → Frame B

**Backend (`story_engine.py`)**
- **`generate_video_prompts()`**: Genera 1 video prompt por escena describiendo la acción/movimiento del clip
- **Contexto visual**: Si `prompts.json` existe, inyecta text de Frame A/B como contexto a cada escena
- **Cross-chapter bridge**: Usa el video prompt real del capítulo anterior (no el `end_state`)
- **Auto-evaluación**: `evaluate_video_prompt_continuity()` (batch=5, truncado 80 chars)

### 🔗 Sequential Chaining Fix (Imagen + Video)

**Backend (`story_engine.py`)**
- **`fix_weak_image_prompt_transitions()`**: Reescrita con **sequential chaining** — procesa weak transitions una a una en orden de escena, propagando cada fix como contexto al siguiente
- **`fix_weak_video_prompt_transitions()`**: Misma lógica de sequential chaining
- **Evita efecto dominó**: Antes, arreglar 5→6 rompía 6→7. Ahora el nuevo Frame A(6) se pasa como contexto al fix de 6→7
- **max_tokens=2000** para evitar truncado de respuesta

**Backend (`app.py`)**
- Endpoint `POST /fix-image-transitions`: Carga weak transitions, llama fix secuencial, re-evalúa, guarda
- Endpoint `POST /fix-video-transitions`: Mismo patrón
- `api_generate_video_prompts`: Carga `prompts.json` y pasa como `prompts_data` a `generate_video_prompts`

**Frontend (`app.js`)**
- `renderPrompts()`: Score de continuidad + panel de weak transitions + botón Fix
- `renderVideoPrompts()`: Mismo patrón para video prompts
- `fixWeakVideoTransitions()`: Llama endpoint de fix, muestra progreso, recarga datos

### 📚 Documentación

- **`SHOW_BIBLE.md`**: Paso 5 reescrito con sistema Frame A/B completo, Paso 6 añadido para video prompts
- **`CHANGELOG.md`**: Actualizado con todos los cambios de esta sesión

---

## 2026-02-14 Late — Phase-Based Image Prompts + G-Labs Integration

### 🎨 Image Prompts — Reescritura Completa (Por Capítulo)

**Backend (`story_engine.py`)**
- **`generate_phase_prompts()`**: Reemplaza `generate_scene_prompts()` — genera 1 prompt ultra-detallado por capítulo de narración (no por escena)
- Fusiona fases multi-parte (ej: "Raising the Walls Part 1" + "Part 2" → un solo prompt)
- Cada prompt describe solo la **ESCENA DE APERTURA** del capítulo, no un resumen
- **Sin nombres propios** en los prompts: usa "the man", "the character", "he" — las imágenes de referencia se adjuntan por separado
- Usa narración + escenas como contexto para mood/setting

**Backend (`app.py`)**
- Endpoint `POST /api/project/<id>/generate-prompts` actualizado para pasar datos de narración
- **`GET /api/project/<id>/download-prompts`**: Nuevo endpoint — descarga `.txt` con un prompt por línea, formato G-Labs
- Cada línea del TXT incluye **filenames de referencia** al inicio (`ref1.png ref2.png ...`) para auto-attach en G-Labs

**Frontend (`app.js`)**
- **`renderPrompts()`** reescrito: cards por capítulo con colores (misma paleta que narración)
- Stats header: total chapters + total words
- `btnMap` y `toggleStepButtons()` actualizados para regenerate + download
- **`downloadPrompts()`**: Nueva función para descarga del TXT

**Frontend (`index.html`)**
- **Botón `btnRegeneratePrompts`**: "↻ Regenerate" junto a Generate
- **Botón `btnDownloadPrompts`**: "📥 Download TXT" para G-Labs

### 👤 Character References — Nombres Simplificados

- Archivos renombrados de `ref_1_{label}.png` → `ref1.png`, `ref2.png`, ..., `ref5.png`
- Compatible con G-Labs auto-attach por filename

---

### 👤 Character References — Full System with Visual Consistency

**Backend (`story_engine.py`)**
- **`generate_image_with_ref()`**: Nueva función que pasa un `PIL.Image` como parte del `contents` a Nanobanana Pro, permitiendo usar una imagen de referencia para mantener consistencia de personaje
- **`generate_character_references()` reescrito**: Genera la imagen 1 (retrato completo) sin referencia como base, luego genera imágenes 2-5 pasando la imagen 1 como referencia con instrucciones de consistencia ("same face, body build, hair, beard, clothing")
- **`_build_character_ref_prompts()`**: Prompts actualizados con reglas de consistencia — prompt 1 describe ropa en detalle extremo, prompts 2-5 deben repetir la misma ropa
- **Limpieza en regeneración**: Se eliminan archivos de imagen anteriores del directorio `character_refs/` antes de generar nuevos, evitando archivos huérfanos
- **Pillow** añadido como dependencia (`PIL.Image` para cargar la imagen base de referencia)

**Backend (`app.py`)**
- **`GET /api/project/<id>/download-refs`**: Nuevo endpoint que genera un ZIP en memoria con todas las imágenes de `character_refs/` y lo devuelve como descarga (`{titulo}-character-refs.zip`)

**Frontend (`app.js`)**
- **Lightbox**: Click en imagen de referencia → overlay full-size. Cierre con ×, Escape, o click fuera
- **Cache-busting**: URLs de imagen incluyen `?t=timestamp` para forzar recarga tras regeneración
- **Botón Regenerate**: "↻ Regenerate" con spinner durante generación (mismo patrón que story/scenes/narration)
- **Step pill navigation**: Click en cualquier step pill scrollea suavemente a la sección correspondiente
- **Visibilidad de sección**: `refsSection` visible si narration O character_refs están completados

**Frontend (`index.html`)**
- **Botón `btnRegenerateRefs`**: Añadido junto a `btnGenerateRefs`
- **Botón `btnDownloadRefs`**: "📥 Download ZIP" para descargar todas las referencias como archivo comprimido

**Estilos (`style.css`)**
- **Lightbox overlay**: Fondo semi-transparente, imagen centrada, botón de cierre, caption
- **Image cards hover**: Efecto de elevación al pasar el cursor

---

## 2026-02-13 — Late Session

### 🎙️ Narration System — Full Overhaul

**Backend (`story_engine.py`)**
- **JSON Repair**: New `_repair_truncated_json()` helper auto-fixes truncated Gemini JSON responses (closes open strings/brackets)
- **Model Switch**: Intro, breaks, and close generation now use `GEMINI_MODEL_FLASH` instead of Pro to avoid thinking-token overhead
- **Increased max_tokens**: Break/close/intro generation uses `max_tokens=4000` to prevent `MAX_TOKENS` truncation
- **Breaks per chapter**: One presenter break generated per original chapter (cliffhanger style)
- **Simplified break prompts**: Removed large `narration_style` block from break/close prompts, replaced with concise style instruction
- **Presenter intro**: Forced 3rd-person perspective ("A retired teacher..." not "I'm a retired teacher...")
- **Phase name cleaning**: Strips "Phase X:" prefix from phase names in both backend and frontend

**Backend (`app.py`)**
- **New endpoint `GET /api/project/<id>/download-script`**: Server-side TXT generation with proper `Content-Disposition` header, sanitized filename from project title

**Frontend (`app.js`)**
- **Phase color consistency**: Same chapter parts (Part 1, Part 2) share the same border color via `chapterColorMap`
- **Presenter labels**: Intro → "📢 Presenter Intro", Close → "📢 Presenter Outro", breaks numbered (#1, #2, etc.)
- **Download script**: Uses `fetch()` + data URI for cross-browser filename support (server generates content, client controls filename)
- **Phase title cleanup**: `cleanPhaseName()` helper strips "Phase X:" prefix

**UI (`index.html`)**
- **Full episode type labels in sidebar**: "BUILD BEFORE DEADLINE" instead of just "BUILD" (matches JS `EPISODE_TYPE_LABELS`)

---



### 🔧 Continuity Fixes — Weak Transitions System

**Nuevo sistema para detectar y corregir transiciones débiles entre escenas.**

#### Backend (`app.py`, `story_engine.py`)
- **Evaluación de continuidad mejorada**: Reducido de 80 a 30 pares muestreados para evitar content filters de Gemini. Prompt simplificado.
- **Debug logging en `generate_json`**: Ahora registra `block_reason` cuando Gemini devuelve `None` (content filter, token limit, etc.)
- **Nuevo endpoint `POST /api/project/<id>/fix-transitions`**: 
  - Lee las weak transitions guardadas en `scenes.json`
  - Llama a `refine_weak_transitions()` para regenerar solo las escenas problemáticas
  - Re-evalúa la continuidad completa con `evaluate_scene_continuity()`
  - Guarda los resultados actualizados
  - Ejecuta en background thread con progress streaming

#### Frontend (`app.js`, `style.css`)
- **Panel expandible de weak transitions**: Clic en "X weak transitions ▾" despliega panel con detalles de cada transición (escena A → B + issue)
- **Botón "🔧 Fix Weak Transitions"**: Lanza el fix desde la UI, muestra spinner + progreso en consola
- **Función `fixWeakTransitions()`**: Gestión completa de estado (disable button, spinner, reload on complete)
- **Escenas débiles destacadas**: Filas con borde rojo + ⚠ en la tabla de escenas

---

### 🎨 UI — Sticky Navigation

- **Header unificado**: Título del episodio + barra de pasos ahora dentro de un contenedor `.sticky-nav` que permanece fijo al hacer scroll
- Layout: título arriba, step pills debajo, ambos siempre visibles

---

## 2026-02-12

### 📖 Story DNA Enrichment

- Integración de material de investigación no utilizado (arquetipos virales, patrones de Alone TV, escenarios reales) en `STORY_DNA.md`
- Re-incorporación del ejemplo JSON de output para asegurar que Gemini sigue el formato correcto

---

## 2026-02-11

### 🧹 App Cleanup — GenAIPro Removal

- Eliminado el sistema de créditos GenAIPro
- Eliminados los pasos de generación de imágenes y video integrados (pasos 4 y 5 originales)
- Ahora se usa G-Labs Automation para imagen/video

---

## 2026-02-09

### 🖼️ Image Generation Testing

- Tests de generación de imágenes con Imagen (Nanobanana Pro)
- Análisis de costes Freepik API vs Vertex AI

---

## 2026-02-06

### 🎙️ Narration System Refinements

- Reglas estilísticas "Wild America": frases cortas, crudeza emocional, vocabulario variado
- Avatar breaks más misteriosos y atmosféricos
- Fix del import `google-genai` (SDK correcto instalado)
- Narración con fases codificadas por color en la UI

---

## 2026-02-03

### 📋 Documentation

- Documentación completa de features implementadas
- Limpieza de proyectos de test

---

## 2026-02-02

### 💰 Video Generation Cost Optimization

- Análisis de costes Modal (Starter vs Team)
- Optimización de GPU (A100 vs H100, fallbacks)
- Configuración de buffer containers y scaledown windows

---

## 2026-01-30

### 📊 Analysis Steps Visualization

- Fases del análisis de script visibles en la barra de progreso
- Backend y frontend actualizados para mostrar: lectura, identificación, verificación, resumen

---

## 2026-01-29

### 🎥 Video Generation Improvements

- Errores específicos por video mostrados en cada card
- Logging detallado en consola web
- Icono de regeneración individual por video generado
