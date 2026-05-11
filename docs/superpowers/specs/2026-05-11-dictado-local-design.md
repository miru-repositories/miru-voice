# Dictado Local — Diseño de App estilo Wispr Flow

**Fecha:** 2026-05-11
**Autor:** Aaron Flores (con Claude)
**Estado:** Borrador — pendiente revisión
**Alcance:** Uso personal, Windows con RTX 3080

---

## 1. Visión

Una app nativa de Windows que captura voz al sostener una tecla (push-to-talk), transcribe con baja latencia (<500ms desde que terminas de hablar) y pega el texto corregido en cualquier aplicación activa. Equivalente funcional a Wispr Flow, pero corriendo 100% local en la RTX 3080, sin AWS, sin costos recurrentes, sin que el audio salga de la máquina.

### Objetivos

- **Latencia end-to-end:** 300-600ms desde fin de habla hasta texto pegado
- **Costo operativo:** $0/mes (solo electricidad)
- **Privacidad:** audio nunca sale de la máquina
- **Idiomas:** español e inglés con auto-detect
- **Footprint:** ~6GB VRAM en uso, ~3GB descarga inicial

### No-objetivos (YAGNI)

- Soporte cross-platform en Fase 1 (Mac Intel queda fuera)
- Multi-usuario / cloud sync
- Mobile companion
- Modelos custom fine-tuned

---

## 2. Por qué NO la arquitectura cloud original

La propuesta inicial era AWS SageMaker con dos endpoints GPU (Whisper + Llama-3-8B), FastAPI en EC2, WebSockets. Problemas para uso personal:

- **Costo:** ml.g5.xlarge × 2 instancias 24/7 ≈ $1,500-2,000 USD/mes
- **Latencia de red:** +100-300ms de round-trip Windows→AWS→Windows
- **Privacidad:** audio sale de la máquina
- **Complejidad operativa:** SageMaker endpoints, gateway, lambda, secretos AWS
- **Overkill del modelo:** Llama-3-8B para eliminar muletillas es un mazo para una tachuela

La RTX 3080 con 10GB VRAM corre el stack equivalente sin compromisos de calidad perceptibles.

---

## 3. Arquitectura

### 3.1 Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    PROCESO ÚNICO (Python)                    │
│                                                              │
│  ┌──────────┐    ┌────────┐    ┌────────────┐               │
│  │ Hotkey   │───▶│ WASAPI  │───▶│ Silero VAD │               │
│  │ Listener │    │ Capture │    │  (CPU)     │               │
│  └──────────┘    └────────┘    └─────┬──────┘               │
│       ▲                              │                       │
│       │                              ▼                       │
│  ┌────┴─────┐              ┌──────────────────┐             │
│  │ Tray UI  │              │ faster-whisper   │             │
│  │ (estado) │              │ distil-large-v3  │ ← GPU 3GB   │
│  └──────────┘              │ (streaming int8) │             │
│       ▲                    └─────────┬────────┘             │
│       │                              │                       │
│       │                    ┌─────────▼────────┐             │
│       │                    │ Regex + Phi-3-   │             │
│       │                    │ mini Q4 (cond.)  │ ← GPU 3GB   │
│       │                    └─────────┬────────┘             │
│       │                              │                       │
│       │                    ┌─────────▼────────┐             │
│       └────────────────────│ Clipboard +      │             │
│                            │ SendInput(Ctrl+V)│             │
│                            └──────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Flujo de datos (latencia objetivo)

```
t=0ms     Sueltas Right Alt (o VAD detecta pausa de 400ms)
t=10ms    Último chunk de audio entra al buffer
t=20ms    faster-whisper recibe los últimos 1-2s
t=200ms   Transcripción cruda lista
t=210ms   Regex pass elimina muletillas obvias
t=220ms   Phi-3-mini procesa (si necesario) — streaming
t=400ms   Texto final pegado en la app activa via Ctrl+V
```

Mientras hablas, el sistema produce transcripciones parciales cada vez que el VAD detecta una micro-pausa. Al final, el flush solo procesa los últimos 1-2s, no todo el dictado.

---

## 4. Componentes

### 4.1 `hotkey.py`

**Responsabilidad:** Detectar push-to-talk.

**Interfaz pública:**
- `start(on_press_callback, on_release_callback)` — registra listener global
- Modos: `hold` (graba mientras sostienes) y `toggle` (tap para empezar/parar)
- Tecla default: `Right Alt` (configurable)

**Dependencias:** `pynput.keyboard`

**Notas:** El hotkey solo emite eventos. No graba ni habla con el ASR directamente — eso lo orquesta `main.py`.

### 4.2 `audio_capture.py`

**Responsabilidad:** Capturar audio del micrófono con la mínima latencia posible.

**Interfaz pública:**
- `AudioCapture(samplerate=16000, blocksize=320)` — clase con `start()`/`stop()`
- Emite chunks de 20ms (320 samples) a una `asyncio.Queue`

**Dependencias:** `sounddevice` con WASAPI exclusive mode

**Por qué `sounddevice` y no `pyaudio`:** `pyaudio` en Windows usa MME por default (~200ms latencia). `sounddevice` con WASAPI exclusive da ~10ms.

### 4.3 `vad.py`

**Responsabilidad:** Detectar inicio/fin de habla.

**Interfaz pública:**
- `VAD()` — clase con método `process(chunk) -> SpeechEvent`
- Eventos: `SPEECH_START`, `SPEECH_END`, `SPEECH_CONTINUE`

**Dependencias:** `silero-vad` (PyTorch CPU)

**Notas:** Corre en CPU (es minúsculo, ~5ms por chunk). Se usa para:
1. Detectar fin de frase automático (pausa >400ms)
2. Hacer flush incremental al ASR mientras hablas

### 4.4 `asr.py`

**Responsabilidad:** Transcripción speech-to-text.

**Interfaz pública:**
- `ASR(model="distil-whisper-large-v3", device="cuda", compute_type="int8")`
- `transcribe_chunk(audio_chunk) -> PartialTranscript` (streaming)
- `transcribe_final(full_audio) -> FinalTranscript`

**Dependencias:** `faster-whisper` (CTranslate2 backend)

**Por qué `distil-whisper-large-v3` y no `whisper-large-v3-turbo`:**
- 6× más rápido que `whisper-large-v3`
- Calidad WER prácticamente igual (~9% vs ~8.5% en LibriSpeech)
- Footprint: 756MB en int8

**Auto-detect idioma:** habilitado. El primer segmento define el idioma; subsiguientes pueden cambiar.

### 4.5 `postprocess.py`

**Responsabilidad:** Limpiar y formatear la transcripción.

**Pipeline de 2 etapas:**

**Etapa 1 — Regex (siempre, 0ms):**
- Elimina muletillas: `\b(eh|este|o sea|pues|ajá|mmm|este…)\b`
- Comandos de voz literales:
  - `"nueva línea"` → `\n`
  - `"punto y aparte"` → `.\n\n`
  - `"coma"` → `,`
  - `"borra eso último"` → trigger especial al injector
  - `"código <texto>"` → `` `<texto>` ``
- Capitalización de inicio de oración

**Etapa 2 — LLM (condicional, ~150-300ms):**
- Solo si la frase tiene >20 palabras o detecta gramática rota
- `Phi-3-mini-4k-instruct` Q4_K_M via `llama-cpp-python`
- System prompt estricto:
  > "Eres un asistente de dictado. Corrige gramática y puntuación del texto adjunto. Mantén el idioma original. NO agregues introducciones, comentarios ni explicaciones. Devuelve SOLO el texto corregido."
- Temperature: 0.1
- Max tokens: 2× input

**Interfaz pública:**
- `PostProcessor()` con `process(raw_text, force_llm=False) -> CleanText`

### 4.6 `injector.py`

**Responsabilidad:** Pegar el texto final en la app activa.

**Estrategia primaria — Clipboard paste:**
1. Guardar contenido actual del clipboard
2. `OpenClipboard` → `SetClipboardData(CF_UNICODETEXT, text)`
3. `SendInput` simula `Ctrl+V`
4. Restaurar clipboard original (con delay de 100ms)

**Estrategia fallback — Typing:**
- Si el clipboard no responde o la app activa está en blacklist (ej. algunos terminales) → `pynput.keyboard.Controller().type(text)`

**Interfaz pública:**
- `inject(text, mode="auto")` — modos: `auto`, `paste`, `type`

**Dependencias:** `pywin32`, `pynput`

### 4.7 `app_context.py`

**Responsabilidad:** Detectar qué app está activa para aplicar reglas contextuales.

**Interfaz pública:**
- `get_active_app() -> AppContext` — retorna `{exe_name, window_title, app_class}`
- `get_rules_for(app_context) -> dict` — lee reglas del config

**Ejemplos de reglas:**
- `code.exe`: formatear código entre backticks si es snippet
- `slack.exe`: mantener tono casual, no corregir slang
- `winword.exe`: capitalización formal

**Dependencias:** `pywin32` (`GetForegroundWindow`, `GetWindowText`)

### 4.8 `tray.py`

**Responsabilidad:** UI mínima en system tray.

**Estados visualizados:**
- 🔵 Idle
- 🟢 Listening (grabando)
- 🟡 Transcribing
- 🔴 Error

**Menú:**
- Settings (abre config.toml en editor)
- Pause / Resume
- Historial (últimas 20 transcripciones)
- Quit

**Dependencias:** `pystray`, `Pillow`

### 4.9 `config.py`

**Responsabilidad:** Cargar/guardar configuración.

**Ubicación:** `%APPDATA%\dictado\config.toml`

**Schema:**
```toml
[hotkey]
key = "alt_r"
mode = "hold"  # hold | toggle

[asr]
model = "distil-whisper-large-v3"
compute_type = "int8"
language = "auto"  # auto | es | en

[postprocess]
use_llm = true
llm_model = "phi-3-mini-4k-instruct-q4"
llm_min_words = 20

[injector]
mode = "auto"  # auto | paste | type
blacklist_apps = []

[app_rules.code]
exe = "code.exe"
format_code_blocks = true
```

### 4.10 `main.py`

**Responsabilidad:** Orquesta el ciclo de vida.

**Loop principal (asyncio):**
1. Cargar modelos a VRAM (al startup, ~15s)
2. Iniciar tray
3. Registrar hotkey listener
4. En cada press: iniciar audio capture + VAD pipeline
5. Stream parcial al ASR; final al postprocess; resultado al injector
6. Actualizar tray state

---

## 5. Stack técnico

| Capa | Tecnología | Versión | Justificación |
|---|---|---|---|
| Lenguaje | Python | 3.11+ | Ecosistema ML, asyncio maduro |
| Audio | `sounddevice` | latest | WASAPI exclusive, ~10ms latencia |
| VAD | `silero-vad` | latest | <5ms inferencia CPU |
| ASR | `faster-whisper` | latest | CTranslate2 backend, 6× speedup |
| Modelo ASR | `distil-whisper/distil-large-v3` | — | 756MB int8, calidad casi igual a large-v3 |
| LLM runtime | `llama-cpp-python` | latest con CUDA | Q4_K_M, streaming |
| Modelo LLM | `Phi-3-mini-4k-instruct` | Q4_K_M | 2.3GB, 50 tok/s en RTX 3080 |
| GPU | CUDA Toolkit | 12.x | Driver 591.86 ya soporta |
| Hotkey | `pynput` | latest | Solo para listener global |
| Inyección | `pywin32` | latest | Win32 API directa |
| Tray | `pystray` + `Pillow` | latest | Minimal |
| Empaquetado | `PyInstaller` | latest | `--onefile` → .exe standalone |
| Config | `tomli` + `tomli-w` | latest | TOML stdlib en 3.11+ |

---

## 6. Manejo de errores

| Escenario | Comportamiento |
|---|---|
| Modelo no descargado al primer arranque | Descargar al startup con progress bar en tray |
| CUDA OOM | Fallback a `distil-whisper-small` automáticamente; notificar en tray |
| Audio device desconectado | Reintentar con device default cada 2s; notificar |
| Hotkey ya en uso por otra app | Detectar conflicto en startup y pedir nueva tecla |
| LLM hangs (>2s) | Timeout → entregar solo regex-pass + log warning |
| Clipboard injection falla | Fallback automático a typing mode |
| App activa no detectable | Saltarse reglas contextuales, usar default |

Todos los errores se loggean a `%APPDATA%\dictado\logs\dictado.log` con rotación diaria.

---

## 7. Testing

### Unit tests
- `postprocess.py`: regex elimina muletillas, comandos de voz mapean correcto
- `config.py`: TOML carga/guarda sin perder campos
- `app_context.py`: parsea correctamente window titles

### Integration tests
- Audio file → ASR → texto esperado (corpus de 20 frases ES + 20 EN)
- Latencia end-to-end con audio pre-grabado: p50 <500ms, p95 <800ms

### Manual smoke tests (golden path)
1. Dictar 10 palabras en Notepad → texto aparece sin errores
2. Dictar mezclando ES/EN → idioma detectado correctamente
3. Sostener tecla 30s → no se cuelga
4. Usar comandos de voz ("nueva línea", "coma") → mapean correcto
5. Cambiar de app activa entre Slack y VS Code → reglas aplican

### No haremos
- E2E con `pyautogui` para validar el paste (frágil)
- Benchmarks contra Wispr Flow oficial (no es el punto)

---

## 8. Plan de fases

### Fase 1 — MVP funcional (1-2 días)
- `hotkey.py`, `audio_capture.py`, `asr.py`, `injector.py` (solo paste), `main.py` mínimo
- Sin VAD, sin LLM, sin tray, sin config
- Criterio de aceptación: sostener Right Alt, hablar, soltar, texto aparece en Notepad

### Fase 2 — Calidad de transcripción (1-2 días)
- `vad.py` para fin de frase automático
- `postprocess.py` solo etapa regex
- `tray.py` con estados visuales
- Criterio: latencia <800ms, muletillas eliminadas

### Fase 3 — Inteligencia (2-3 días)
- `postprocess.py` etapa LLM con Phi-3-mini
- Comandos de voz
- `app_context.py` + reglas por app
- Criterio: latencia <600ms en frases <20 palabras, corrección semántica en frases largas

### Fase 4 — Polish y distribución (1 día)
- `config.py` completo
- Empaquetado `.exe` con PyInstaller
- Auto-start con Windows (opcional)
- Criterio: instalable con 1 click, funciona en arranque limpio

---

## 9. Decisiones explícitas

| Decisión | Alternativa rechazada | Razón |
|---|---|---|
| `distil-whisper-large-v3` | `whisper-large-v3-turbo` | 6× más rápido, calidad casi idéntica |
| `faster-whisper` (CT2) | `transformers` directo | 4× speedup gratis |
| `Phi-3-mini` Q4 | `Llama-3-8B` Q4 | Phi-3 más rápido en RTX 3080 (50 vs 30 tok/s), suficiente calidad para esta tarea |
| 100% local | AWS SageMaker | $0/mes vs $1,500/mes; latencia mejor |
| Python | Rust/C++ nativo | Prototipo rápido, ecosistema ML; portable si después escalas |
| Push-to-talk como default | Always-on VAD | Más reliable, evita transcripciones accidentales |
| Clipboard paste | `pynput.type()` | Instantáneo vs 10ms/char |
| TOML config | JSON/YAML | Editable a mano sin errores de sintaxis |
| Single process | Cliente/servidor | YAGNI para uso personal |

---

## 10. Riesgos conocidos

| Riesgo | Mitigación |
|---|---|
| RTX 3080 ocupada por otro proceso (juego, ML) | Detectar VRAM disponible al startup, degradar a CPU si <4GB |
| `distil-whisper` mete errores en jerga técnica | Permitir override a `whisper-large-v3` en config |
| Phi-3-mini agrega texto no deseado pese a system prompt | Validar output: si crece >2× del input, descartar y usar solo regex |
| Clipboard paste pisa contenido importante | Snapshot + restore con delay; opción de desactivar en config |
| Auto-start con Windows lentifica boot | Lazy-load de modelos (no al startup, sino al primer hotkey) |

---

## 11. Métricas de éxito

- **Latencia p50:** <500ms desde fin de habla hasta texto pegado
- **WER:** <10% en español, <8% en inglés (vs corpus de test)
- **Uptime:** 8h continuas sin reinicio
- **VRAM:** <7GB en estado estable
- **Tiempo a primer uso desde install:** <5 minutos (incluyendo descarga de modelos)

---

## 12. Próximos pasos

1. Usuario revisa y aprueba este spec
2. Crear plan de implementación detallado (writing-plans)
3. Setup del repo: estructura, dependencias, CI mínimo
4. Implementar Fase 1
