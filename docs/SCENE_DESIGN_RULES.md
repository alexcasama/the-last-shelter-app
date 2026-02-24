# Reglas de Diseño de Escenas — The Last Shelter

Documento de referencia para la construcción de escenas del storyboard.
Aprendido durante la producción del INTRO (Ep. 01).

---

## 1. Duración realista

| Regla | Explicación |
|-------|-------------|
| **Contar las palabras** | ~2.5 palabras/segundo en narración. Una frase de 25 palabras = ~10s mínimo |
| **No escenas de 5s con mucho texto** | Si hay más de 1 frase de diálogo, la escena necesita mínimo 7-8s |
| **No escenas de 5s con una sola frase corta** | "This won't be a game" no justifica una escena sola de 5s — queda cutre |
| **B-roll puro: 3-6s** | Sin diálogo, basta con pocos segundos para establecer |
| **Presenter intenso: 7-12s** | Jack hablando a cámara con energía |
| **Multishot: 12-15s** | Escenas con múltiples cortes necesitan tiempo |

## 2. Multishot scenes (intercortes)

Cuando hay mucho texto o la acción es compleja, NO crear múltiples escenas cortas. Crear **una sola escena multishot**:

```
Tipo: PRESENTER (o el dominante)
Acción: "Multishot: [corte 1] → [corte 2] → [corte 3]"
```

**Ejemplos correctos:**
- ✅ Jack habla serio intercalado con montaje de Erik construyendo (Scene 10)
- ✅ Helicóptero aterriza → Jack habla → baja → camina a ruinas (Scene 13)

**Ejemplos incorrectos:**
- ❌ Escena solo de Jack mirando fijo diciendo "This won't be a game" (cutre, vacía)
- ❌ 4s de helicóptero bajando + 12s de Jack caminando como dos escenas separadas

## 3. Campo "Acción" como guía de director

La **Acción** es lo que el usuario/editor escribe. Debe ser:
- En **español**
- Breve y descriptivo (1-2 líneas)
- Describir QUÉ PASA, no cómo se ve
- La IA genera automáticamente la descripción visual + cámara a partir de esto

```
✅ "Jack se inclina agresivo, señala a cámara con urgencia"
✅ "Cortes rápidos: Erik tala, carga, mide. Solo. El reloj corre."
❌ "Medium shot of Jack leaning forward with aggressive energy" (esto lo genera la IA)
```

## 4. Estructura de actos en la intro

| Acto | Función | Escenas típicas |
|------|---------|-----------------|
| **Hook** | Enganchar al espectador | 2-3 escenas: aerial + presenter energético |
| **Backstory** | Contexto emocional | 2-3 escenas: flashbacks + bridge de ruinas |
| **Stakes** | Subir la tensión | 3-4 escenas: presenter urgente + anticipatorio + bridge amenazante |
| **Challenge** | Definir el reto | 2-3 escenas: multishot presenter + anticipatorio montaje |
| **Arrival** | Resolución y tagline | 1-2 escenas: multishot llegada + tagline final |

## 5. Tipos de escena y cuándo usarlos

| Tipo | Cuándo | Con diálogo | Duración típica |
|------|--------|-------------|-----------------|
| **BRIDGE** | Establecer lugar/mood, transiciones | No | 3-6s |
| **PRESENTER** | Jack habla a cámara | Sí | 7-15s |
| **FLASHBACK** | Eventos pasados, backstory | Voice-over | 8-12s |
| **ANTICIPATORIO** | Preview de lo que veremos | Voice-over o no | 5-8s |
| **NARRATED** | Footage con narración encima | Sí | 8-15s |

## 6. Idiomas

| Campo | Idioma | Razón |
|-------|--------|-------|
| **Acción** | 🇪🇸 Español | Guía interna para el editor |
| **Descripción visual** | 🇪🇸 Español | El editor necesita entenderlo |
| **Cámara** | 🇪🇸 Español | Ídem |
| **Narración** | 🇬🇧 Inglés | Es el diálogo del show (en inglés) |
| **Prompt de imagen** | 🇬🇧 Inglés | Se envuelve automáticamente en inglés para Gemini |

## 7. Flujo de trabajo del editor

1. El editor escribe solo la **Acción** (en español) y la **Narración**
2. Elige el **Tipo** y la **Duración** del dropdown
3. La IA genera automáticamente:
   - Descripción visual detallada (en español)
   - Instrucción de cámara (en español)
   - Imagen 16:9 con referencia de personaje si aplica

## 8. Anti-patrones a evitar

- ❌ Escenas con una sola frase corta que no justifican su existencia
- ❌ Dividir una acción continua en dos escenas cuando es un solo momento
- ❌ B-roll de más de 6s sin ninguna narración
- ❌ Texto de narración que no cabe en la duración asignada
- ❌ Escenas de presenter idénticas consecutivas sin variación visual
- ❌ Descripciones visuales genéricas ("un hombre en el bosque")
