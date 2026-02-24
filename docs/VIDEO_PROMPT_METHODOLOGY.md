# VIDEO PROMPT METHODOLOGY — Del Guion a Kling 3

Documento unificado: cómo transformar el script de narración en video prompts para Kling 3 Pro.

---

## PROCESO COMPLETO

```
narration.json (guion aprobado)
      │
      ▼
╔═══════════════════════════════════════════════╗
║  FASE 1: CORTAR EN ESCENAS                   ║
║  Script → bloques de ~16s de narración        ║
║  Distribuidos por fases narrativas             ║
╚═══════════════════════════════════════════════╝
      │
      ▼
╔═══════════════════════════════════════════════╗
║  FASE 2: FRAME A (imagen de inicio)           ║
║  Para cada escena: un prompt de imagen         ║
║  Nanobanana Pro genera la imagen               ║
╚═══════════════════════════════════════════════╝
      │
      ▼
╔═══════════════════════════════════════════════╗
║  FASE 3: VIDEO PROMPT MULTISHOT               ║
║  Del texto narrativo → prompt cinematográfico  ║
║  Con amplificación de acción + multishot       ║
╚═══════════════════════════════════════════════╝
      │
      ▼
╔═══════════════════════════════════════════════╗
║  FASE 4: ENVÍO A KLING O3                     ║
║  Frame A + prompt + elements → video 15s       ║
╚═══════════════════════════════════════════════╝
```

---

## FASE 1: CORTAR EL GUION EN ESCENAS

### Input

`narration.json` contiene:
- `intro` → presentador (Jack Harlan)
- `phases[]` → bloques de narración por fase narrativa
- `breaks[]` → intervenciones del presentador entre fases
- `close` → cierre del presentador

### Lógica de corte

1. **Calcular duración total**: total_words ÷ 150 WPM = duración en minutos
2. **Distribuir escenas por fase**: proporcionalmente al word_count de cada fase
3. **Tamaño de escena**: ~16 segundos de narración = 1 escena = 1 video de 15s
4. **Fases cortas** (< 15s de narración) = 1 sola escena
5. **Fases largas** (> 15s) = dividir en bloques de ~10-15s

### Resultado

Cada escena queda definida con:

```json
{
    "number": 1,
    "type": "narration",
    "phase": "Foundation Work",
    "narration_text": "Elena's truck grinds to a halt. The thin air bites...",
    "duration": 15,
    "elements_used": ["@Element1", "@Element3"]
}
```

### Tipos de escena

| Tipo | Descripción | Elements |
|------|-------------|----------|
| `narration` | Escena narrativa principal | Protagonista + lo que aparezca |
| `narrator_intro` | Jack Harlan presenta el episodio | Narrador (global) |
| `narrator_break` | Jack Harlan hace cliffhanger entre fases | Narrador (global) |
| `narrator_outro` | Cierre de Jack Harlan | Narrador (global) |

---

## FASE 2: GENERAR FRAME A (Imagen de Inicio)

Para cada escena, se genera **una sola imagen** que será el primer frame del video.

### Reglas del Frame A

- Debe representar la **apertura visual** de la escena (lo primero que ve el espectador)
- Incluir la **composición general**, iluminación, ángulo de cámara
- El personaje debe estar en la **posición inicial** de la acción
- Generado con **Nanobanana Pro** a alta resolución

### NO se genera Frame B

- **Sin Frame B.** No se envía imagen final a Kling.
- Kling genera el movimiento libremente a partir del prompt.
- Forzar una imagen final degrada la calidad — le quita libertad al modelo.

---

## FASE 3: VIDEO PROMPT MULTISHOT

Esta es la fase clave. Se transforma el texto narrativo en un **prompt cinematográfico de video con múltiples shots**.

### Principios Fundamentales

#### 1. Escenas largas de 15 segundos
- Aprovechar al máximo la duración de Kling (15s por clip).
- En lugar de clips cortos de 5s, tomas más **cinematográficas y fluidas**.
- Más duración = más tiempo para desarrollar movimiento.

#### 2. Multishot dentro de cada video
- **3-5 shots diferentes** dentro de un solo video de 15s.
- Cambios de ángulo de cámara con "Cut to" entre shots.
- Variedad visual sin necesidad de generar múltiples videos.

#### 3. Todo corte seco entre escenas
- Cada escena es **independiente** con su propia Frame A.
- Transiciones entre escenas = **corte seco** siempre.
- No hay cadenas. No se necesita que el último frame coincida con el primero de la siguiente.

> **La continuidad visual se logra DENTRO de cada escena de 15s** (gracias a multishot + duración larga), y **entre escenas simplemente cortes**.

---

### AMPLIFICACIÓN DE ACCIÓN (Critical)

**Problema:** La narración es voiceover literario — no describe acción visual. Pero el video necesita **dinamismo visual máximo**.

**Solución:** NO cambiar la narración. En el video prompt, **amplificar la acción** con:

| Capa | Qué añadir | Ejemplo |
|------|-----------|---------|
| **Movimiento físico** | Dirección, velocidad, fuerza | "drives the shovel blade downward with both arms" |
| **Reacción del material** | Qué pasa visualmente cuando la acción ocurre | "ice fragments fly upward, frozen soil cracks and yields" |
| **Atmósfera activa** | Clima interactuando con la acción | "snow swirls in gusting wind, breath visible in subzero air" |
| **Consecuencia física** | Esfuerzo muscular, dolor, equilibrio | "shoulders strain, arms trembling from the effort" |
| **Partículas y efectos** | Nieve, chispas, polvo, vapor, fragmentos | "steam rises from his back, sawdust spirals into cold air" |

**Ejemplo concreto:**

Narración:
> *"Elena digs with relentless determination, the shovel biting into frozen earth."*

❌ Video prompt sin amplificar:
> "Woman digs in frozen ground."

✅ Video prompt amplificado:
> "Close-up of gloved hands gripping shovel handle, blade driving into cracked frozen soil with force, ice fragments flying upward, steam rising from effort, snow swirling in background wind, shallow depth of field, film grain."

**Regla:** Cada frase de narración que describe una acción debe convertirse en un prompt con **al menos 3 de las 5 capas de amplificación**.

---

### Reglas para Construir el Prompt

1. **NO redescribir al personaje** — usar `@Element1`. Kling ya tiene las imágenes de referencia.
2. **Evolucionar DESDE Frame A** — no describir lo que ya está visible en la imagen de inicio. Describir CÓMO CAMBIA.
3. **Movimiento explícito** — verbos de acción fuertes con dirección y secuencia.
   - ❌ "@Element1 chops wood."
   - ✅ "@Element1 slowly reaches forward, grips the axe handle, lifts it overhead, then swings it down with force. Wood splinters fly."
4. **Cámara en el tiempo** — cómo se mueve la cámara a lo largo del shot, no solo su posición final.
   - ❌ "Wide shot."
   - ✅ "Camera tracks steadily from behind, matching @Element1's pace, then slows to a stop as he pauses at the ridge, revealing the valley below."
5. **Audio ambiental** — tejer sonidos naturales orgánicamente.
   - "Wind whistles through the pines. Snow crunches underfoot. A distant hawk cry echoes."
6. **Duración** — para 15s, describir progresión y evolución de la acción, no un momento estático.

---

### Formatos de Prompt

Dos estilos válidos. Ambos producen buenos resultados:

#### Estilo 1: Fluido (un solo párrafo con "Cut to")

```
Multi-shot cinematic sequence: Wide aerial establishing shot slowly descending 
toward a weathered dark green pickup truck grinding to a halt on a narrow dirt 
mountain road surrounded by towering ponderosa pine trees, dust cloud rising 
behind it, cold Sierra Nevada morning light. Cut to medium shot through the 
windshield as the woman exhales visible breath in the cold thin air, her hands 
resting on the steering wheel. Cut to slow dramatic tilt upward from the pine 
canopy to reveal massive granite peaks against a vast deep blue sky, golden 
morning light catching the rock faces. Cut to low tracking shot as a brown 
and white dog leaps from the open truck door onto dry earth, tail wagging, 
sniffing the ground eagerly. Final wide shot from behind the woman as she 
steps out and stands beside the truck looking out at the immense wilderness 
stretching endlessly before her, wind gently moving her hair, cinematic 
lighting, realistic motion, shallow depth of field, film look, 4K.
```

#### Estilo 2: Shot-by-shot con timecodes

```
Shot 1 (0-4 seconds) Wide aerial establishing shot slowly descending. A 
weathered dark green pickup truck grinds to a halt on a narrow dirt mountain 
road. Dust rises behind the truck. Towering ponderosa pines frame both sides. 
Cold golden Sierra Nevada morning light cuts through the trees.

Shot 2 (4-7 seconds) Cut to medium shot through the windshield. The woman 
exhales, her breath visible in the thin cold air. Her hands slowly release 
the steering wheel. She gazes outward.

Shot 3 (7-11 seconds) Cut to dramatic slow tilt upward from the pine canopy. 
The camera reveals massive granite peaks against a vast deep blue sky. Golden 
light catches the rock faces. The peaks loom ancient and indifferent.

Shot 4 (11-16 seconds) Cut to low tracking shot at ground level. A brown and 
white dog leaps from the open truck door onto dry earth. Tail wagging, sniffing 
eagerly. The woman steps out behind, standing beside the truck. Wide pull-back 
reveals the immense wilderness stretching endlessly before her. Wind gently 
moves her hair. Cinematic lighting, shallow depth of field, realistic motion, 
film look.
```

---

## FASE 4: ENVÍO A KLING O3

### Datos por escena

| Parámetro | Valor |
|---|---|
| `prompt` | Multishot video prompt (60-150 palabras) |
| `start_image_url` | Frame A generado con Nanobanana Pro |
| `end_image_url` | ❌ **NO se usa** |
| `elements[]` | Personaje, objetos, animal — según la escena |
| `duration` | **15** (máxima duración) |
| `aspect_ratio` | 16:9 |

### Elements

Los Elements son personajes/objetos con imágenes de referencia para consistencia visual:

| Element | Referencia | Cuándo se pasa |
|---------|-----------|----------------|
| **Protagonista** (`@Element1`) | Frontal + ángulos | En escenas de narración |
| **Animal compañero** (`@Element2`) | Referencia del animal | Cuando aparece en la escena |
| **Vehículo** (`@Element3`) | Foto del vehículo | Solo escenas con vehículo |
| **Narrador (Jack Harlan)** | Desde `config/presenter/` | En intro, breaks, outro |

**Límite:** Máximo 4 elements por escena (limitación de Kling 3).

Los elements se guardan por episodio y **solo se pasan cuando la escena los requiere**.

### API Endpoint

```json
{
    "prompt": "Multi-shot cinematic sequence: @Element1 lifts a heavy...",
    "start_image_url": "https://storage.../frame_a_scene_01.png",
    "elements": [
        {
            "frontal_image_url": "https://storage.../protagonist_frontal.png",
            "reference_image_urls": ["https://storage.../protagonist_side.png"]
        }
    ],
    "duration": "15",
    "aspect_ratio": "16:9"
}
```

---

## RESUMEN — ANTES vs AHORA

| Aspecto | Antes (antiguo) | Ahora (multishot) |
|---------|-----------------|---------------------|
| **Frame A** | ✅ Sí | ✅ Sí |
| **Frame B** | ✅ Sí (degradaba calidad) | ❌ Eliminado |
| **Duración** | 5-8s por escena | **15s** por escena |
| **Shots por escena** | 1 shot = 1 video | **3-5 shots** en 1 video |
| **Transiciones** | Chain (frame B → frame A) o cut | **Solo corte seco** |
| **Continuidad** | Entre escenas (complejo) | **Dentro de cada escena** (natural) |
| **Acción en prompt** | Literal del guion | **Amplificada** (5 capas) |
| **Videos por episodio 20min** | ~150 clips | **~40-50 clips** (menos, más largos) |
| **Calidad** | Variable (forzada por Frame B) | **Mayor** (Kling libre) |

---

## ESCENAS DEL NARRADOR (Jack Harlan)

Las escenas del narrador (intro, breaks, outro) siguen un proceso ligeramente diferente:

- **Frame A**: Jack Harlan en entorno exterior (bosque, río, nieve), mirando a cámara
- **Prompt**: Movimiento mínimo — habla a cámara, gestualiza, mira al horizonte
- **Elements**: Solo el narrador global (`config/presenter/`)
- **Audio**: Se genera por separado con ElevenLabs, luego se sincroniza con lip-sync via Kling

---

## PENDING — Implementación

- [ ] Implementar `generate_multishot_prompts()` en `story_engine.py`
- [ ] Integrar con `fal-ai/kling-video/o3/pro/reference-to-video`
- [ ] Lógica de qué elements se pasan por escena (máx 4)
- [ ] Decidir estilo preferido (fluido vs shot-by-shot) después de pruebas
- [ ] Integrar la amplificación de acción como paso automático en el prompt generation
