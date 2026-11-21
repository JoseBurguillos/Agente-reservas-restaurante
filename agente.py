import sqlite3

from langchain_core.tools import tool
from langchain_ollama import ChatOllama 
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver


modelo=ChatOllama(model="qwen2.5:7b",temperature=0) #Creamos el modelo

@tool #Gracias a esto le permite al LLM poder tenerlo, para que cuendo le pregunten algo sepa que hay que ejecutar
def consultar_reserva(reserva_id: str) -> str:  #Creamos el metodo
    #Debajo debemos de poner la descripción del metodo
    #y en la linea de abajo de la descripcion le damos la instrucción
    """Consulta los datos de una reserva del restaurante a partir de su número de reserva.
    Úsala cuando el cliente pregunte por una reserva que ya tiene hecha y dé su número (por ejemplo, R001)."""
    
    numero = int(reserva_id[1:])                                 # "R003" → 3

    conexion = sqlite3.connect("restaurante.db")
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT nombre, dia, hora, personas FROM reservas WHERE id = ?",
        (numero,)
    )
    fila = cursor.fetchone()                           # una fila, o None si no existe
    conexion.close()

    if fila is None:
        return f"No existe la reserva con el id: {reserva_id}"
    nombre, dia, hora, personas = fila
    return f"La reserva con el id {reserva_id} es de {nombre} el dia {dia} a las {hora} con {personas} personas"
    
    
@tool
def cancelar_reserva(reserva_id:str)-> str:
    """
    cancela (borra) una reserva a partir de su número.
    Usala cuando el cliente pida cancelar una reserva y dé su número (por ejemplo, R001).
    """
    
    numero = int(reserva_id[1:]) # "R003" → 3
    
    conexion = sqlite3.connect("restaurante.db")
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre, dia, hora FROM reservas WHERE id = ?", (numero,))
    fila = cursor.fetchone()

    if fila is None:
        conexion.close()                               # cerrar ANTES de salir
        return f"No existe la reserva {reserva_id}. No se ha cancelado nada."
    
    nombre, dia, hora = fila
    
    cursor.execute("DELETE FROM reservas WHERE id = ?", (numero,))
    conexion.commit()
    conexion.close()

    return f"Reserva {reserva_id} cancelada: era de {nombre}, el {dia} a las {hora}."
    
    
    
@tool
def hacer_reserva(nombre:str| None=None, dia:str| None=None, hora:str| None=None,personas:int | None=None)->str:
    """Crea una reserva nueva en el restaurante y devuelve su número de reserva.
    Úsala cuando el cliente quiera reservar mesa. 
    Necesitas los 4 datos: nombre,día, hora y número de personas. Si falta alguno, pídeselo al cliente antes
    de usarla; no te lo inventes."""
    
    if nombre is None:
        return "No se ha creado la reserva: falta el nombre. Pregúntaselo al cliente."
    if dia is None:
        return "No se ha creado la reserva: falta el día. Pregúntaselo al cliente."
    if hora is None:
        return "No se ha creado la reserva: falta la hora. Pregúntaselo al cliente."
    if personas is None:
        return "No se ha creado la reserva: falta el número de personas. Pregúntaselo al cliente."
    
    conexion = sqlite3.connect("restaurante.db")
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO reservas (nombre,dia,hora,personas) VALUES (?,?,?,?)",
        (nombre,dia,hora,personas)
    )
    conexion.commit()                  
    nuevo_id = cursor.lastrowid
    conexion.close()                   

    id_reserva = f"R{nuevo_id:03d}" # Convierte el id de la BD al formato del cliente: 4 → "R004" (:03d = entero con 3 cifras y ceros delante)
    
    return f"Reserva realizada con exito el id es {id_reserva} a nombre de {nombre} el día {dia} a las {hora} y {personas} personas"
    

modelo_con_tools=modelo.bind_tools([consultar_reserva,cancelar_reserva,hacer_reserva]) #Creamos el modelo con herramientas, añadiendole las funciones entre corchetes porque pueden ser varias

PROMPT_AGENTE = """Eres el asistente de reservas de un restaurante. Atiendes a los clientes de forma amable, clara y breve, y siempre en español.

Reglas:
- Para consultar una reserva, usa la herramienta consultar_reserva.
- Para cancelar una reserva, DEBES usar la herramienta cancelar_reserva. Escribir que la cancelas no la cancela: solo se cancela si usas la herramienta.
- Nunca digas que has hecho una acción (cancelar, consultar...) si no has usado la herramienta correspondiente y has recibido su confirmación.
- Si el cliente te pide varias cosas, usa todas las herramientas necesarias antes de darle la respuesta final.
- No inventes datos de reservas: usa solo la información que te devuelvan las herramientas.
- Si una herramienta dice que la reserva no existe, díselo al cliente.
- Si necesitas el número de reserva, búscalo primero en la conversación (por ejemplo, si acabas de crear una reserva). Solo si no ha aparecido nunca, pídeselo al cliente. No lo adivines.
- Para hacer una reserva, DEBES usar la herramienta hacer_reserva. Necesitas que el cliente te diga los 4 datos: nombre, día, hora y número de personas. Si falta alguno, pregúntaselo. Nunca supongas ningún dato (tampoco el número de personas, ni siquiera 1 o 2).
- Cuando tengas los 4 datos, ANTES de usar hacer_reserva, resume la reserva al cliente y pregúntale si la confirmas. Solo usa hacer_reserva cuando el cliente confirme (por ejemplo, "sí", "vale", "confirmo"). Si el cliente corrige algún dato, vuelve a resumir con el dato corregido y pide confirmación otra vez.

Ejemplos:

Cliente: "Quería una mesa para el viernes a las 20:30, a nombre de Ana"
Asistente (SIN usar ninguna herramienta): "¡Claro, Ana! ¿Para cuántas personas sería la mesa?"

Cliente: "Reserva para 3 personas el domingo a las 14:00, a nombre de Pedro"
Asistente (SIN usar ninguna herramienta): "Perfecto, Pedro: mesa para 3 personas el domingo a las 14:00. ¿Te la confirmo?"
Cliente: "Sí"
Asistente: usa hacer_reserva con nombre="Pedro", dia="domingo", hora="14:00", personas=3
"""

def agente(state:MessagesState):
    respuesta=modelo_con_tools.invoke([SystemMessage(PROMPT_AGENTE)]+state["messages"])#Le pasamos la conversacion
    return{
        "messages":[respuesta] #Añadimos la respuesta al la lista de mensajes
    }


def tools_condition(state):
    ultimo=state["messages"][-1] #vemos el ultimo mensaje de mensajes que es el que pedira la funcion 
    if ultimo.tool_calls: #Si la pide returneamos tools
        return "tools"
    else: #y si no se acaba el ciclo
        return END

grafo=StateGraph(MessagesState)

grafo.add_node("agente", agente)
grafo.add_node("tools", ToolNode([consultar_reserva,cancelar_reserva,hacer_reserva]))

grafo.add_edge(START, "agente")
grafo.add_conditional_edges("agente", tools_condition)
grafo.add_edge("tools", "agente")

app=grafo.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "user-1"}}

while True:
    pregunta=input("¿Que quieres hacer?")
    
    if pregunta=="salir":
        break
    
    resultado=app.invoke({"messages":[HumanMessage(pregunta)]},config=config)
    
    print(resultado["messages"][-1].content)
    
