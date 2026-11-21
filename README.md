# 🍽️ Agente de reservas para un restaurante

Agente conversacional que gestiona las reservas de un restaurante: **consulta, crea y cancela reservas** hablando en lenguaje natural. Está construido con **LangGraph** siguiendo el patrón **ReAct**, usa un modelo local con **Ollama** y guarda las reservas en **SQLite**.

A diferencia de un RAG, que solo busca información y responde, este agente **decide qué acción hacer y la ejecuta** sobre una base de datos real.

## ✨ Características

- **Tool calling**: el modelo decide qué herramienta usar y con qué argumentos, a partir de lo que dice el cliente.
- **Patrón ReAct**: bucle *razonar → actuar → observar* (agente → herramientas → agente) hasta tener la respuesta.
- **Memoria conversacional**: recuerda la conversación (`MemorySaver` + `thread_id`), así que puede juntar datos que el cliente da en varios mensajes.
- **Confirmación antes de actuar** (*human in the loop*): antes de crear una reserva, resume los datos y pide confirmación.
- **Persistencia en SQLite**: las reservas siguen ahí al cerrar y volver a abrir el programa.
- **Consultas parametrizadas** (`?`) para evitar inyección SQL, ya que los argumentos de las herramientas los genera el modelo a partir del texto del cliente.
- **Modelo local**: funciona sin conexión a la nube, con `qwen2.5:7b` en Ollama.

## 🏗️ Arquitectura

```
            ┌──────────────────────────────┐
            │                              │
START ──→ agente ──(¿pide herramienta?)──→ tools
            │            no                   │
            ↓                                 │
           END          ←─────────────────────┘
                     (vuelve al agente con el resultado)
```

| Pieza | Papel |
|---|---|
| **Ollama** + `qwen2.5:7b` | Ejecuta el modelo en local. El modelo decide si responder o usar una herramienta |
| **LangChain** (`@tool`, `bind_tools`) | Convierte las funciones de Python en herramientas que el modelo puede pedir |
| **LangGraph** | Orquesta el flujo: el bucle agente ↔ herramientas, la condición de parada y la memoria |
| **SQLite** | Guarda las reservas en el archivo `restaurante.db` |

### Herramientas

| Herramienta | Qué hace | SQL |
|---|---|---|
| `consultar_reserva(reserva_id)` | Devuelve los datos de una reserva | `SELECT` |
| `hacer_reserva(nombre, dia, hora, personas)` | Crea una reserva y devuelve su número | `INSERT` |
| `cancelar_reserva(reserva_id)` | Comprueba que existe y la borra | `SELECT` → `DELETE` |

Los números de reserva se muestran al cliente con el formato `R004`, mientras que en la base de datos el `id` es un entero `AUTOINCREMENT`, que nunca reutiliza un número borrado.

## 📁 Estructura

```
Agente restaurante/
├── agente.py          # herramientas, prompt, grafo LangGraph y bucle de chat
├── crear_db.py        # crea la tabla y mete 3 reservas de ejemplo (ejecutar una vez)
├── requirements.txt
└── .gitignore         # excluye .venv/, __pycache__/ y restaurante.db
```

## 🚀 Cómo ejecutarlo

### 1. Requisitos
- Python 3.13
- [Ollama](https://ollama.com/) instalado y en marcha, con el modelo descargado:
```bash
ollama pull qwen2.5:7b
```

### 2. Instalar dependencias
```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 3. Crear la base de datos (solo la primera vez)
```bash
python crear_db.py
```
Crea `restaurante.db` con 3 reservas de ejemplo (R001, R002 y R003). Si lo ejecutas otra vez, las reservas se duplican: borra `restaurante.db` antes de repetirlo.

### 4. Hablar con el agente
```bash
python agente.py
```
Escribe `salir` para terminar.

## 💬 Ejemplo de conversación

```
Tú: quiero reservar una mesa
Agente: ¿Podrías decirme el nombre, el día y la hora, y cuántas personas serán?
Tú: antonio, para el viernes
Agente: Perfecto, Antonio. ¿A qué hora te gustaría reservar y cuántas personas serán?
Tú: a las 14:00
Agente: Genial, Antonio. ¿Podrías decirme cuántas personas serán?
Tú: 3
Agente: Reserva para 3 personas el viernes a las 14:00. ¿Te la confirmo?
Tú: si
Agente: Se ha realizado tu reserva con éxito. El número de tu reserva es R004...
```

El agente junta datos de varios mensajes, pregunta lo que falta sin inventarlo y solo crea la reserva después de la confirmación.

## 🧠 Decisiones de diseño y lo aprendido

**El modelo inventaba datos.** Cuando el cliente no decía cuántas personas eran, el modelo rellenaba `personas: 1` y creaba la reserva. Se probaron varias capas:

| Intento | Resultado |
|---|---|
| Docstring de la herramienta: *"no te lo inventes"* | ❌ Lo ignoraba |
| Parámetro opcional (`int \| None = None`) + comprobación en el código | ❌ Seguía mandando `1` |
| Regla explícita en el prompt del sistema | ❌ Lo ignoraba |
| **Ejemplos *few-shot* en el prompt** | ✅ Empezó a preguntar |
| **Confirmación antes de reservar** | ✅ Si algo sale mal, el cliente lo ve antes de que se guarde |

Conclusiones:
- A un modelo pequeño le cuesta seguir **instrucciones**, pero imita bien los **ejemplos**.
- Las reglas importantes **no se dejan solo en el prompt**: el código valida (`if ... is None`) y la base de datos también (`NOT NULL`).
- El agente también **alucinaba acciones**: decía que había cancelado una reserva sin llamar a la herramienta. Se corrigió con reglas en el prompt del sistema, y se comprueba mirando el estado real de la base de datos.

## ⚠️ Limitaciones conocidas

- **Modelo de 7B**: a veces pregunta de más (por ejemplo, con *"para 2"* sin decir *"personas"*) o no usa un número de reserva que ya ha salido en la conversación.
- **La memoria vive en la RAM**: al cerrar el programa se olvida la conversación (las reservas sí se conservan en SQLite).
- **Días como texto libre**: se guarda `"viernes"` o `"20"` tal cual lo dice el cliente; no hay fechas reales ni se comprueba la disponibilidad de mesas.
- **Sin límite de personas** ni horario del restaurante.
- Si el modelo manda un número de reserva sin la `R` (por ejemplo `"3"`), la conversión falla.
- **Latencia**: cada turno hace al menos una llamada al modelo local, y varias si usa herramientas.

## 🔮 Próximos pasos

- [ ] Herramienta RAG (`buscar_en_documentos`) con la carta, alérgenos y horarios (*agentic RAG*)
- [ ] Fechas reales y comprobación de disponibilidad
- [ ] Confirmación en el código con `interrupt` de LangGraph
- [ ] API con FastAPI e interfaz con Streamlit
- [ ] Memoria persistente (checkpointer en SQLite)

## 🛠️ Tecnologías

Python · LangChain · LangGraph · Ollama (qwen2.5:7b) · SQLite
