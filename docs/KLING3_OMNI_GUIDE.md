# KLING VIDEO 3.0 Omni — Guía del Modelo

Resumen extraído de la guía oficial: https://app.klingai.com/global/quickstart/klingai-video-3-omni-model-user-guide

---

## 1. Mejoras de Capacidad (VIDEO 3.0 Omni vs anteriores)

| Feature | Detalle |
|---------|---------|
| **Audio Nativo** | Salida audio-visual nativa sincronizada |
| **Multi-shot** | Vídeos de múltiples tomas en una sola generación |
| **Duración** | Hasta **15 segundos** (antes 10s) |
| **Elementos** | Subir o grabar personajes con voz vinculada |
| **Resolución** | 1080p y 720p |

---

## 2. Elements 3.0: Consistencia de Personajes y Voz

Clave para mantener consistencia del presentador (Jack Harlan).

- **Captura Visual y de Audio:** Creas un "Character Asset" subiendo un vídeo de **3-8 segundos**. El modelo extrae rasgos del personaje y su **voz original**
- **Vinculación de Voz:** Puedes vincular una voz a un `@Character`. Una vez creado, la voz queda ligada al sujeto — no necesitas especificarla en el prompt; el modelo sincroniza labios automáticamente
- **Consistencia Multimodal:** Combinar múltiples elementos (ej: `@Element1` para Jack y `@Element2` para entorno). El modelo "bloquea" las características de cada uno para mantener consistencia en todas las tomas
- **Límites de imágenes:** Hasta 7 imágenes (min 300px, máx 10MB, .jpg/.png)
- **Límites de vídeos:** 1 vídeo (3s-10s, máx 200MB, hasta 2K)
- **Combinación:** Si usas vídeo de referencia, solo hasta 4 imágenes/elementos adicionales. Sin vídeo, hasta 7

---

## 3. Storyboard Narration 3.0: Control Multi-shot

Control preciso sobre la estructura del vídeo generado.

### Formato de Prompt — Dos opciones:

#### Opción A: Por Shot con duración
```
Shot 1 (3s): Wide shot of @Element2. Cold morning light. @Element1 walks into frame.
Shot 2 (2s): Close-up of @Element1's profile. He looks down and asks, "You still haven't decided which road to take?"
Shot 3 (4s): Medium shot. @Element1 turns to camera with serious expression.
```

#### Opción B: Por Timestamp
```
[00:00 - 00:02] Medium shot: @Goro stands at the bar.
[00:02 - 00:05] Close-up: @Goro lights a cigarette.
[00:05 - 00:08] Wide shot: The bar is dimly lit.
```

### Control disponible por toma:
- **Framing:** Wide shot, close-up, mid-shot, etc.
- **Ángulos de cámara:** Especificables por shot
- **Movimientos de cámara:** Pan, tilt, zoom, etc.
- **Contenido narrativo:** Diálogo, acciones, emociones
- **Audio:** Describir sonidos específicos (ej: *"Audio: The faint crackle of a cigarette"*)

---

## 4. Guía de Prompts con Elementos

### Uso de @Element
Se usa `@ElementN` en la descripción de cada toma para posicionar o dar acción a un personaje/lugar predefinido.

### Ejemplo Real de la Guía:
> *Shot 2 (2s): Cut to a close-up of @Element1's profile. He looks down and asks, "You still haven't decided which road to take?"*

### Tips de Prompt:
- Describir el framing primero (Wide shot, Close-up, etc.)
- Incluir acciones claras del personaje
- Usar comillas para diálogo (`He says: "..."`)
- Describir el ambiente/iluminación
- Especificar movimientos de cámara si se desean

---

## 5. Precios (Créditos por segundo)

| Configuración | Créditos/s |
|--------------|-----------|
| **1080p + Audio Nativo ON** | 12 |
| **1080p + Audio Nativo OFF** | 8 |
| **720p + Audio Nativo ON** | 9 |
| **Vídeo como entrada (I2V) 1080p** | 16 |

---

## 6. Implicaciones para The Last Shelter

Para automatizar la generación de vídeo:

1. **Registrar a Jack como Elemento con voz** — usar un clip de 3-8s como referencia
2. **Usar formato `Shot X (Ys):`** para construir la narrativa de ~15 segundos
3. **Referenciar con `@Element1` y `@Element2`** — consistencia garantizada entre tomas
4. **Audio Nativo** — el modelo sincroniza labios del presentador automáticamente
5. **Multicámara** — podemos especificar cambios de plano (wide, close-up, medium) dentro del mismo clip de 15s
