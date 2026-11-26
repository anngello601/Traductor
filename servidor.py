import base64
import io
import json
import os
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
import uvicorn

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pymupdf
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pydantic import BaseModel

PUERTO = 5001
URL_PROLOG = "http://127.0.0.1:5002/traducir"
TAMANO_MAXIMO_ARCHIVO = 10 * 1024 * 1024
FUENTE_PDF = "china-s"
ARCHIVO_FUENTE_PDF = None
rutas_fuente = [
    (
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "tahoma.ttf",
        "Tahoma",
    ),
    (
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
        "SegoeUI",
    ),
    (
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        "Arial",
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        "DejaVuSans",
    ),
    (
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        "LiberationSans",
    ),
]
for ruta_fuente, nombre_fuente in rutas_fuente:
    if ruta_fuente.is_file():
        FUENTE_PDF = nombre_fuente
        ARCHIVO_FUENTE_PDF = str(ruta_fuente)
        break

DICCIONARIO = {
    "hello": "hola", "hi": "hola", "goodbye": "adiós", "thanks": "gracias",
    "i": "yo", "you": "tú", "he": "él", "she": "ella", "we": "nosotros",
    "they": "ellos", "my": "mi", "your": "tu", "his": "su", "her": "su",
    "our": "nuestro", "their": "su", "the": "el", "a": "un", "an": "un",
    "is": "es", "are": "son", "am": "soy", "was": "era", "were": "eran",
    "have": "tener", "has": "tiene", "want": "quiero", "need": "necesito",
    "like": "gusta", "love": "amo", "name": "nombre", "house": "casa",
    "home": "hogar", "dog": "perro", "cat": "gato", "book": "libro",
    "books": "libros",
    "water": "agua", "car": "coche", "friend": "amigo", "food": "comida",
    "year": "año", "years": "años", "old": "viejo", "cat": "gato", "cats": "gatos",
    "big": "grande", "small": "pequeño", "good": "bueno", "bad": "malo",
    "red": "rojo", "blue": "azul", "green": "verde", "black": "negro",
    "white": "blanco", "and": "y", "or": "o", "but": "pero",
    "in": "en", "on": "en", "at": "en", "to": "a", "from": "de",
    "of": "de", "with": "con", "for": "para",
    "zero": "cero", "one": "uno", "two": "dos", "three": "tres",
    "four": "cuatro", "five": "cinco", "six": "seis", "seven": "siete",
    "eight": "ocho", "nine": "nueve", "ten": "diez", "eleven": "once",
    "twelve": "doce", "thirteen": "trece", "fourteen": "catorce",
    "fifteen": "quince", "sixteen": "dieciséis", "seventeen": "diecisiete",
    "eighteen": "dieciocho", "nineteen": "diecinueve", "twenty": "veinte",
    "thirty": "treinta", "forty": "cuarenta", "fifty": "cincuenta",
    "sixty": "sesenta", "seventy": "setenta", "eighty": "ochenta",
    "ninety": "noventa", "hundred": "cien", "thousand": "mil",
    "million": "millón", "first": "primero", "second": "segundo",
    "third": "tercero", "fourth": "cuarto", "fifth": "quinto",
    "administrator": "administrador", "administrators": "administradores",
    "organization": "organización",
    "organizations": "organizaciones", "detect": "detectar", "detects": "detecta",
    "detected": "detectó", "detecting": "detectando",
    "anomalous": "anómalo", "abnormal": "anómalo",
    "behavior": "comportamiento", "behaviour": "comportamiento",
    "computer": "computadora", "computers": "computadoras",
    "send": "enviar", "sends": "envía", "sending": "enviando", "sent": "envió",
    "large": "grande", "number": "número", "amount": "cantidad",
    "packet": "paquete", "packets": "paquetes", "server": "servidor",
    "servers": "servidores", "many": "muchos", "connection": "conexión",
    "connections": "conexiones", "never": "nunca", "reach": "llegar",
    "reaches": "llega", "complete": "completar", "completes": "completa",
    "completed": "completó", "establishment": "establecimiento",
    "session": "sesión", "sessions": "sesiones", "attack": "ataque",
    "attacks": "ataques", "flood": "inundación", "service": "servicio",
    "distributed": "distribuido", "network": "red", "client": "cliente",
    "clients": "clientes", "request": "solicitud", "requests": "solicitudes",
    "response": "respuesta",     "responses": "respuestas",
    "suspicious": "sospechoso", "unusual": "inusual", "malicious": "malicioso",
    "traffic": "tráfico", "device": "dispositivo", "devices": "dispositivos",
    "multiple": "múltiples", "several": "varios", "failed": "fallido",
    "failure": "fallo", "fails": "falla", "establish": "establecer",
    "establishes": "establece", "establishing": "estableciendo",
    "handshake": "apretón de manos",
    "because": "porque", "while": "mientras", "during": "durante",
    "before": "antes", "after": "después", "between": "entre",
    "without": "sin", "not": "no", "cannot": "no puede", "can": "puede",
    "could": "podría", "might": "podría", "may": "puede",
    "will": "va", "would": "haría", "be": "ser",
    "this": "este", "these": "estos",
    "that": "ese", "those": "esos", "some": "algunos",
    "each": "cada", "every": "cada", "all": "todos", "other": "otro",
    "then": "entonces", "also": "también",
    "which": "que", "what": "qué", "when": "cuando", "where": "donde",
    "who": "quién", "why": "por qué", "how": "cómo",
    "it": "ello", "occur": "ocurrir", "occurs": "ocurre",
    "occurring": "ocurriendo", "happen": "suceder", "happens": "sucede",
    "participate": "participar", "participates": "participa",
    "participating": "participando", "teams": "equipos", "team": "equipo",
    "toward": "hacia", "towards": "hacia",
    "tcp": "TCP", "syn": "SYN", "dos": "DoS", "ddos": "DDoS",
}

DICCIONARIO.update({
    "assignment": "tarea", "integrated": "integrado", "case": "caso",
    "conflict": "conflicto", "agreement": "acuerdo", "agree": "acordar",
    "project": "proyecto", "delayed": "retrasado", "delay": "retraso",
    "task": "tarea", "committed": "comprometió", "deliver": "entregar",
    "delivery": "entrega", "database": "base de datos", "clean": "limpio",
    "notify": "avisar", "notified": "avisó", "wrote": "escribió",
    "message": "mensaje", "messages": "mensajes", "marked": "marcado",
    "seen": "visto", "read": "leído", "reply": "respuesta",
    "response": "respuesta", "record": "registro", "chat": "chat",
    "silence": "silencio", "indicate": "indicar", "indicated": "indicó",
    "overwhelmed": "agobiado", "obligation": "obligación",
    "obligations": "obligaciones", "part-time": "medio tiempo",
    "shift": "turno", "shifts": "turnos", "extra": "extra",
    "confirmation": "confirmación", "confirm": "confirmar",
    "fact": "hecho", "facts": "hechos", "interpretation": "interpretación",
    "interpretations": "interpretaciones", "assumption": "supuesto",
    "assumptions": "supuestos", "statement": "enunciado",
    "justification": "justificación", "reason": "razón",
    "reasons": "razones", "deadline": "fecha límite",
    "submission": "entrega", "submit": "entregar", "submitted": "entregado",
    "representative": "representante", "career": "carrera",
    "semester": "ciclo", "participated": "participó", "member": "integrante",
    "members": "integrantes", "teamwork": "trabajo en equipo",
    "manager": "gerente", "coordinator": "coordinador",
    "employability": "empleabilidad", "campus": "campus",
    "proposal": "propuesta", "propose": "proponer", "solution": "solución",
    "solutions": "soluciones", "negotiate": "negociar",
    "negotiation": "negociación", "communicate": "comunicar",
    "communication": "comunicación", "listen": "escuchar",
    "listening": "escucha", "respectful": "respetuoso",
    "assertive": "asertivo", "issue": "problema", "option": "opción",
    "options": "opciones", "criteria": "criterios", "commitment": "compromiso",
    "follow-up": "seguimiento", "available": "disponible",
    "shared": "compartido", "compromise": "compromiso",
    "clarify": "aclarar", "responsible": "responsable",
    "responsibility": "responsabilidad", "impact": "impacto",
    "interest": "interés", "interests": "intereses", "parties": "partes",
    "party": "parte", "attitude": "actitud", "cause": "causa",
    "consequence": "consecuencia", "consequences": "consecuencias",
    "resolve": "resolver", "resolution": "resolución",
    "mediate": "mediar", "mediator": "mediador", "collaborate": "colaborar",
    "collaboration": "colaboración", "schedule": "cronograma",
    "progress": "progreso", "pending": "pendiente", "completed": "completado",
    "responsibilities": "responsabilidades", "tomorrow": "mañana",
    "impact": "impacto", "works": "trabaja", "worked": "trabajó",
    "received": "recibió", "receive": "recibir", "there": "allí",
    "as": "como", "wasn't": "no fue",
    "monday": "lunes", "tuesday": "martes", "wednesday": "miércoles",
    "thursday": "jueves", "friday": "viernes", "saturday": "sábado",
    "sunday": "domingo",
})

DICCIONARIO_ES_EN = {traduccion: palabra for palabra, traduccion in DICCIONARIO.items()}
DICCIONARIO_ES_EN.update({
    "hola": "hello", "adiós": "goodbye", "gracias": "thanks",
    "yo": "i", "tú": "you", "él": "he", "ella": "she",
    "nosotros": "we", "ellos": "they", "mi": "my", "tu": "your",
    "su": "their", "nuestro": "our", "el": "the", "un": "a",
    "una": "a", "es": "is", "son": "are", "soy": "am",
    "era": "was", "eran": "were", "tengo": "I have", "tienes": "you have",
    "tiene": "has", "tenemos": "we have", "tienen": "they have",
    "quiero": "want", "necesito": "need", "gusta": "like",
    "amo": "love", "casa": "house", "hogar": "home",
    "perro": "dog", "gato": "cat", "libro": "book", "libros": "books",
    "agua": "water", "coche": "car", "amigo": "friend",
    "comida": "food", "año": "year", "años": "years",
    "grande": "big", "pequeño": "small", "bueno": "good", "malo": "bad",
    "rojo": "red", "azul": "blue", "verde": "green", "negro": "black",
    "blanco": "white", "y": "and", "o": "or", "pero": "but",
    "en": "in", "a": "to", "de": "of", "con": "with", "para": "for",
    "cero": "zero", "uno": "one", "dos": "two", "tres": "three",
    "cuatro": "four", "cinco": "five", "seis": "six", "siete": "seven",
    "ocho": "eight", "nueve": "nine", "diez": "ten",
    "nombre": "name", "ciudad": "city", "escuela": "school",
    "profesor": "teacher", "estudiante": "student", "día": "day",
    "noche": "night", "tiempo": "time", "hombre": "man", "mujer": "woman",
    "niño": "boy", "niña": "girl", "mundo": "world", "vida": "life",
    "amor": "love", "trabajo": "work", "feliz": "happy", "triste": "sad",
    "hermoso": "beautiful", "feo": "ugly", "rápido": "fast", "lento": "slow",
    "muy": "very", "bien": "well", "mal": "bad", "siempre": "always",
    "nunca": "never", "aquí": "here", "allí": "there", "ahora": "now",
    "hoy": "today", "mañana": "tomorrow", "ayer": "yesterday",
    "sin": "without", "por": "by", "porque": "because", "si": "if",
    "sí": "yes", "perdón": "sorry",
    "estoy": "I am", "está": "is", "estás": "are", "estamos": "are",
    "están": "are", "soy": "I am", "eres": "are", "somos": "are",
    "administrador": "administrator", "administradora": "administrator",
    "organización": "organization", "organizaciones": "organizations",
    "detecta": "detects", "detectan": "detect", "detectar": "detect",
    "detectó": "detected", "detectando": "detecting",
    "anómalo": "anomalous", "anómala": "anomalous", "comportamiento": "behavior",
    "computadora": "computer", "computadoras": "computers",
    "enviar": "send", "envía": "sends", "enviando": "sending", "envió": "sent",
    "gran": "large", "número": "number", "cantidad": "amount",
    "paquete": "packet", "paquetes": "packets", "servidor": "server",
    "servidores": "servers", "muchos": "many", "muchas": "many",
    "conexión": "connection", "conexiones": "connections", "nunca": "never",
    "llegar": "reach", "llega": "reaches", "llegan": "reach",
    "completar": "complete", "completa": "completes", "completan": "complete",
    "completó": "completed", "establecimiento": "establishment",
    "sesión": "session", "sesiones": "sessions", "ataque": "attack",
    "ataques": "attacks", "inundación": "flood", "servicio": "service",
    "distribuido": "distributed", "distribuida": "distributed", "red": "network",
    "cliente": "client", "clientes": "clients", "solicitud": "request",
    "solicitudes": "requests", "respuesta": "response", "respuestas": "responses",
    "sospechoso": "suspicious", "sospechosa": "suspicious", "inusual": "unusual",
    "malicioso": "malicious", "tráfico": "traffic", "dispositivo": "device",
    "dispositivos": "devices", "múltiples": "multiple", "varios": "several",
    "fallido": "failed", "fallo": "failure", "falla": "fails",
    "establecer": "establish", "establece": "establishes",
    "estableciendo": "establishing", "apretón": "handshake", "hacia": "to",
    "mientras": "while", "durante": "during", "antes": "before",
    "después": "after", "entre": "between", "cada": "every",
    "entonces": "then", "también": "also", "quién": "who",
    "qué": "what", "cuándo": "when", "dónde": "where", "por qué": "why",
    "participar": "participate", "participa": "participates",
    "participan": "participate", "participando": "participating",
    "equipo": "team", "equipos": "teams", "podría": "could",
    "ocurrir": "occur", "ocurre": "occurs", "ocurriendo": "occurring",
    "suceder": "happen", "sucede": "happens", "ello": "it",
})
DICCIONARIO_ES_EN.update({
    "tarea": "assignment", "integrado": "integrated", "caso": "case",
    "conflicto": "conflict", "acuerdo": "agreement", "acordar": "agree",
    "proyecto": "project", "retrasado": "delayed", "retrasada": "delayed",
    "retraso": "delay", "comprometió": "committed", "comprometerse": "commit",
    "entregar": "deliver", "entrega": "delivery", "base de datos": "database",
    "limpio": "clean", "limpia": "clean", "avisar": "notify",
    "avisó": "notified", "escribió": "wrote", "mensaje": "message",
    "mensajes": "messages", "marcado": "marked", "marcada": "marked",
    "visto": "seen", "leído": "read", "respuesta": "response",
    "registro": "record", "silencio": "silence", "indicar": "indicate",
    "indicaría": "would indicate", "agobiado": "overwhelmed",
    "agobiada": "overwhelmed", "obligación": "obligation",
    "obligaciones": "obligations", "medio tiempo": "part-time",
    "turno": "shift", "turnos": "shifts", "extra": "extra",
    "confirmación": "confirmation", "confirmar": "confirm",
    "hecho": "fact", "hechos": "facts", "interpretación": "interpretation",
    "interpretaciones": "interpretations", "supuesto": "assumption",
    "supuestos": "assumptions", "enunciado": "statement",
    "justificación": "justification", "razón": "reason", "razones": "reasons",
    "fecha límite": "deadline", "representante": "representative",
    "carrera": "career", "ciclo": "semester", "participó": "participated",
    "integrante": "member", "integrantes": "members",
    "trabajo en equipo": "teamwork", "gerente": "manager",
    "coordinador": "coordinator", "coordinadora": "coordinator",
    "empleabilidad": "employability", "propuesta": "proposal",
    "proponer": "propose", "solución": "solution", "soluciones": "solutions",
    "negociar": "negotiate", "negociación": "negotiation",
    "comunicar": "communicate", "comunicación": "communication",
    "escuchar": "listen", "escucha": "listening", "respetuoso": "respectful",
    "respetuosa": "respectful", "asertivo": "assertive", "asertiva": "assertive",
    "problema": "issue", "opción": "option", "opciones": "options",
    "criterios": "criteria", "compromiso": "commitment",
    "seguimiento": "follow-up", "disponible": "available",
    "compartido": "shared", "compartida": "shared", "aclarar": "clarify",
    "responsable": "responsible", "responsabilidad": "responsibility",
    "responsabilidades": "responsibilities", "impacto": "impact",
    "trabaja": "works", "trabajó": "worked", "trabajar": "work",
    "recibió": "received", "recibir": "receive", "quedó": "was left",
    "hubo": "was",
    "interés": "interest", "intereses": "interests", "partes": "parties",
    "parte": "party", "actitud": "attitude", "causa": "cause",
    "consecuencia": "consequence", "consecuencias": "consequences",
    "resolver": "resolve", "resolución": "resolution", "mediar": "mediate",
    "mediador": "mediator", "colaborar": "collaborate",
    "colaboración": "collaboration", "cronograma": "schedule",
    "progreso": "progress", "pendiente": "pending", "completado": "completed",
    "lunes": "Monday", "martes": "Tuesday", "miércoles": "Wednesday",
    "jueves": "Thursday", "viernes": "Friday", "sábado": "Saturday",
    "domingo": "Sunday",
})

REGLAS_FRASE = {
    "en-es": [
        ("on monday", "el lunes"),
        ("on tuesday", "el martes"),
        ("on wednesday", "el miércoles"),
        ("on thursday", "el jueves"),
        ("on friday", "el viernes"),
        ("on saturday", "el sábado"),
        ("on sunday", "el domingo"),
        ("there was no response", "no hubo respuesta"),
        ("wrote mateo a message", "le escribió a Mateo un mensaje"),
        ("it was marked as seen", "figuraba como visto"),
        ("was marked as seen", "figuraba como visto"),
        ("with no response", "sin respuesta"),
        ("a clean database", "una base de datos limpia"),
        ("but it was not delivered", "pero no se entregó"),
        ("it was not delivered", "no se entregó"),
        ("he did not notify the team", "no avisó al equipo"),
        ("to the team", "al equipo"),
        ("works part-time", "trabaja medio tiempo"),
        ("has extra shifts", "tiene turnos extra"),
        ("is overwhelmed by", "está agobiado por"),
        ("assignment 4 integrated case from conflict to agreement", "tarea 4: caso integrador, del conflicto al acuerdo"),
        ("from conflict to agreement", "del conflicto al acuerdo"),
        ("facts, interpretations, and assumptions", "hechos, interpretaciones y supuestos"),
        ("the project that was delayed", "el proyecto que se retrasó"),
        ("committed to deliver", "se comprometió a entregar"),
        ("clean database", "base de datos limpia"),
        ("was not delivered", "no se entregó"),
        ("did not notify", "no avisó"),
        ("was marked as seen", "figuraba como visto"),
        ("no response", "sin respuesta"),
        ("part-time", "medio tiempo"),
        ("extra shifts", "turnos extra"),
        ("would indicate that", "indicaría que"),
        ("overwhelmed by other obligations", "agobiado por otras obligaciones"),
        ("needs confirmation", "necesita confirmación"),
        ("active listening", "escucha activa"),
        ("conflict resolution", "resolución de conflictos"),
        ("reach an agreement", "llegar a un acuerdo"),
        ("proposed agreement", "acuerdo propuesto"),
        ("next steps", "próximos pasos"),
        ("follow up", "dar seguimiento"),
        ("take responsibility for", "asumir la responsabilidad de"),
        ("meet the deadline", "cumplir con la fecha límite"),
        ("delay in delivery", "retraso en la entrega"),
        ("communication channel", "canal de comunicación"),
        ("the establishment of the session", "el establecimiento de la sesión"),
        ("the establecimiento of la sesión", "el establecimiento de la sesión"),
        ("distributed denial of service", "denegación de servicio distribuida"),
        ("distributed denial-of-service", "denegación de servicio distribuida"),
        ("it may also be a ddos if multiple devices participate", "también puede ser un ataque DDoS si participan varios dispositivos"),
        ("it may also be ddos if multiple devices participate", "también puede ser DDoS si participan varios dispositivos"),
        ("may also be a ddos if multiple devices participate", "también puede ser un ataque DDoS si participan varios dispositivos"),
        ("it may also be ddos if multiple teams participate", "también puede ser DDoS si participan varios equipos"),
        ("it can also be a ddos if", "también puede ser un ataque DDoS si"),
        ("a large amount of", "una gran cantidad de"),
        ("a form of denial of service", "una forma de denegación de servicio"),
        ("denial of service", "denegación de servicio"),
        ("denial-of-service", "denegación de servicio"),
        ("ddos attack", "ataque DDoS"),
        ("dos attack", "ataque DoS"),
        ("syn flood attack", "ataque SYN Flood"),
        ("three-way handshake", "apretón de manos de tres vías (Three-Way Handshake)"),
        ("a large number of", "una gran cantidad de"),
        ("large number of", "gran cantidad de"),
        ("anomalous behavior", "un comportamiento anómalo"),
        ("abnormal behavior", "un comportamiento anómalo"),
        ("the session establishment", "el establecimiento de la sesión"),
        ("session establishment", "establecimiento de la sesión"),
        ("session setup", "configuración de la sesión"),
        ("an administrator", "un administrador"),
        ("the administrator", "el administrador"),
        ("an organization", "una organización"),
        ("the organization", "la organización"),
        ("i have", "yo tengo"),
        ("we have", "nosotros tenemos"),
        ("a computer", "una computadora"),
        ("the computer", "la computadora"),
        ("a server", "un servidor"),
        ("the server", "el servidor"),
        ("many connections", "muchas conexiones"),
        ("multiple devices participate", "participan varios dispositivos"),
        ("tcp syn packets", "paquetes TCP SYN"),
        ("syn packets", "paquetes SYN"),
        ("never reach to complete", "nunca llegan a completar"),
        ("never reach", "nunca llegan"),
        ("never complete", "nunca completan"),
        ("is sending", "está enviando"),
        ("are sending", "están enviando"),
        ("a form of", "una forma de"),
        ("a gran cantidad of", "una gran cantidad de"),
        ("a comportamiento anómalo", "un comportamiento anómalo"),
        ("a organización", "una organización"),
        ("a computadora", "una computadora"),
        ("hacia a servidor", "a un servidor"),
        ("but muchas conexiones", "pero muchas conexiones"),
        ("never llegan to completar", "nunca llegan a completar"),
        ("many conexiones", "muchas conexiones"),
        ("a connection", "una conexión"),
        ("the connection", "la conexión"),
        ("a session", "una sesión"),
        ("the session", "la sesión"),
        ("a request", "una solicitud"),
        ("the request", "la solicitud"),
    ],
    "es-en": [
        ("el lunes", "on Monday"),
        ("el martes", "on Tuesday"),
        ("el miércoles", "on Wednesday"),
        ("el jueves", "on Thursday"),
        ("el viernes", "on Friday"),
        ("el sábado", "on Saturday"),
        ("el domingo", "on Sunday"),
        ("el mensaje figuraba como visto", "the message was marked as seen"),
        ("no recibió respuesta", "received no response"),
        ("no hubo respuesta", "there was no response"),
        ("pero no se entregó", "but it was not delivered"),
        ("y no avisó al equipo", "and did not notify the team"),
        ("no avisó al equipo", "did not notify the team"),
        ("al equipo", "to the team"),
        ("una base de datos limpia", "a clean database"),
        ("trabaja medio tiempo", "works part-time"),
        ("tiene turnos extra", "has extra shifts"),
        ("está agobiado por", "is overwhelmed by"),
        ("quedó sin respuesta", "received no response"),
        ("tarea 4 caso integrador del conflicto al acuerdo", "assignment 4 integrated case from conflict to agreement"),
        ("del conflicto al acuerdo", "from conflict to agreement"),
        ("hechos interpretaciones y supuestos", "facts interpretations and assumptions"),
        ("el proyecto que se retrasó", "the project that was delayed"),
        ("se comprometió a entregar", "committed to deliver"),
        ("base de datos limpia", "clean database"),
        ("no se entregó", "was not delivered"),
        ("no avisó", "did not notify"),
        ("figuraba como visto", "was marked as seen"),
        ("sin respuesta", "no response"),
        ("medio tiempo", "part-time"),
        ("turnos extra", "extra shifts"),
        ("indicaría que", "would indicate that"),
        ("agobiado por otras obligaciones", "overwhelmed by other obligations"),
        ("necesita confirmación", "needs confirmation"),
        ("escucha activa", "active listening"),
        ("resolución de conflictos", "conflict resolution"),
        ("llegar a un acuerdo", "reach an agreement"),
        ("acuerdo propuesto", "proposed agreement"),
        ("próximos pasos", "next steps"),
        ("dar seguimiento", "follow up"),
        ("asumir la responsabilidad de", "take responsibility for"),
        ("cumplir con la fecha límite", "meet the deadline"),
        ("retraso en la entrega", "delay in delivery"),
        ("canal de comunicación", "communication channel"),
        ("denegación de servicio distribuida", "distributed denial of service"),
        ("the establecimiento of la sesión", "the session setup"),
        ("también puede ser ddos si participan múltiples equipos", "it can also be DDoS if multiple teams participate"),
        ("también puede ser ddos si participan varios equipos", "it can also be DDoS if multiple teams participate"),
        ("también puede ser un ataque ddos si", "it can also be a DDoS if"),
        ("una forma de denegación de servicio", "a form of denial of service"),
        ("un comportamiento anómalo", "anomalous behavior"),
        ("apretón de manos de tres vías", "three-way handshake"),
        ("el establecimiento de la sesión", "the session setup"),
        ("establecimiento de la sesión", "session setup"),
        ("una gran cantidad de", "a large number of"),
        ("gran cantidad de", "large number of"),
        ("una cantidad grande de", "a large amount of"),
        ("comportamiento anómalo", "anomalous behavior"),
        ("comportamiento anormal", "abnormal behavior"),
        ("ataque syn flood", "SYN Flood attack"),
        ("ataque ddos", "DDoS attack"),
        ("ataque dos", "DoS attack"),
        ("denegación de servicio", "denial of service"),
        ("a gran cantidad of", "a large number of"),
        ("a comportamiento anómalo", "anomalous behavior"),
        ("a organización", "an organization"),
        ("a computadora", "a computer"),
        ("hacia a servidor", "to a server"),
        ("but muchas conexiones", "but many connections"),
        ("never llegan to completar", "never complete"),
        ("yo estoy", "I am"),
        ("yo soy", "I am"),
        ("el administrador", "the administrator"),
        ("una organización", "an organization"),
        ("la organización", "the organization"),
        ("una computadora", "a computer"),
        ("la computadora", "the computer"),
        ("un servidor", "a server"),
        ("el servidor", "the server"),
        ("muchas conexiones", "many connections"),
        ("participan varios dispositivos", "multiple devices participate"),
        ("paquetes tcp syn", "TCP SYN packets"),
        ("nunca llegan a completar", "never complete"),
        ("está enviando", "is sending"),
        ("están enviando", "are sending"),
        ("yo tengo", "I have"),
        ("nosotros tenemos", "we have"),
        ("una forma de", "a form of"),
        ("hacia un servidor", "to a server"),
        ("una conexión", "a connection"),
        ("la conexión", "the connection"),
        ("una sesión", "a session"),
        ("la sesión", "the session"),
        ("una solicitud", "a request"),
        ("la solicitud", "the request"),
    ],
}


class SolicitudTraduccion(BaseModel):
    texto: str
    direccion: str = "en-es"


app = FastAPI(title="Traductor Python NLP")


def limpiar_texto(texto: str) -> str:
    texto = texto.lower().strip()
    return re.sub(r"[^a-záéíóúñü0-9 ]", "", texto)


def tokenizar(texto: str) -> List[str]:
    return [token for token in texto.split() if token]


def validar_direccion(direccion: str) -> str:
    if direccion not in {"en-es", "es-en"}:
        raise HTTPException(
            status_code=400,
            detail="Dirección no válida. Usa 'en-es' o 'es-en'.",
        )
    return direccion


def conservar_mayusculas(
    origen: str,
    traduccion: str,
    inicio_oracion: bool = False,
) -> str:
    if origen.isupper():
        return traduccion.upper()
    primera_palabra = origen.split(maxsplit=1)[0]
    if (
        not inicio_oracion
        and len(primera_palabra) > 1
        and sum(caracter.isupper() for caracter in primera_palabra) > 1
    ):
        return traduccion
    if origen[:1].isupper():
        return traduccion[:1].upper() + traduccion[1:]
    return traduccion


def traducir_token(palabra: str, diccionario: Dict[str, str]) -> str:
    if palabra in {"DoS", "DOS"}:
        return "DoS"
    if palabra in {"DDoS", "DDOS", "Ddos", "ddos"}:
        return "DDoS"
    if palabra.lower() in {"tcp", "syn", "http", "https"}:
        return palabra.upper()

    traduccion = diccionario.get(palabra.lower(), palabra.lower())
    return conservar_mayusculas(palabra, traduccion)


def traducir_texto_con_formato(texto: str, direccion: str) -> str:
    diccionario = DICCIONARIO if direccion == "en-es" else DICCIONARIO_ES_EN
    frases_guardadas = {}

    def guardar_traduccion(match: re.Match[str], traduccion: str) -> str:
        marcador = f"\ue000{len(frases_guardadas)}\ue001"
        prefijo = texto[:match.start()].rstrip()
        inicio_oracion = not prefijo or prefijo[-1] in ".!?:"
        frases_guardadas[marcador] = conservar_mayusculas(
            match.group(0), traduccion, inicio_oracion
        )
        return marcador

    if direccion == "en-es":
        edad = re.compile(r"\bi am\s+([\wáéíóúüñ]+)\s+years old\b", re.IGNORECASE)
        texto = edad.sub(
            lambda match: conservar_mayusculas(
                match.group(0), f"yo tengo {match.group(1)} años"
            ),
            texto,
        )
    else:
        edad = re.compile(
            r"\b(?:yo\s+)?tengo\s+([\wáéíóúüñ]+)\s+años\b",
            re.IGNORECASE,
        )
        texto = edad.sub(
            lambda match: conservar_mayusculas(
                match.group(0), f"I am {match.group(1)} years old"
            ),
            texto,
        )
        texto = re.sub(
            r"\ble escribió a ([A-ZÁÉÍÓÚÜÑ][\wáéíóúüñ-]*) un mensaje\b",
            lambda match: guardar_traduccion(
                match, f"sent {match.group(1)} a message"
            ),
            texto,
            flags=re.IGNORECASE,
        )

    for frase, traduccion in sorted(
        REGLAS_FRASE[direccion],
        key=lambda regla: len(regla[0]),
        reverse=True,
    ):
        palabras = r"\s+".join(re.escape(palabra) for palabra in frase.split())
        patron = re.compile(rf"(?<!\w){palabras}(?!\w)", re.IGNORECASE)

        texto = patron.sub(
            lambda match: guardar_traduccion(match, traduccion),
            texto,
        )

    def traducir_coincidencia(coincidencia: re.Match[str]) -> str:
        return traducir_token(coincidencia.group(0), diccionario)

    texto = re.sub(r"[a-záéíóúüñ]+", traducir_coincidencia, texto, flags=re.IGNORECASE)
    for marcador, traduccion in frases_guardadas.items():
        texto = texto.replace(marcador, traduccion)
    return texto


def proponer_traduccion(tokens: List[str], direccion: str = "en-es") -> List[str]:
    return traducir_texto_con_formato(" ".join(tokens), direccion).split()


def validar_con_prolog(texto: str, propuesta: List[str]) -> Dict[str, object]:
    cuerpo = json.dumps(
        {"texto": texto, "propuesta": propuesta},
        ensure_ascii=False,
    ).encode("utf-8")
    solicitud = urllib.request.Request(
        URL_PROLOG,
        data=cuerpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(solicitud, timeout=5) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=503,
            detail=f"Servicio Prolog no disponible: {error}",
        ) from error


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "servicio": "python"}


@app.post("/traducir")
def traducir(solicitud: SolicitudTraduccion) -> JSONResponse:
    direccion = validar_direccion(solicitud.direccion)
    texto = solicitud.texto.strip()
    if not texto:
        return JSONResponse(
            status_code=400,
            content={"error": "Texto vacío", "traduccion": ""},
        )

    tokens = tokenizar(limpiar_texto(texto))
    propuesta = traducir_texto_con_formato(texto, direccion).split()
    resultado = validar_con_prolog(texto, propuesta)
    return JSONResponse(content={
        "traduccion": resultado["traduccion"],
        "propuesta_python": " ".join(propuesta),
        "validacion": resultado,
        "tokens": tokens,
    })


@app.get("/traducir")
def traducir_get(texto: str = "", direccion: str = "en-es") -> JSONResponse:
    return traducir(SolicitudTraduccion(texto=texto, direccion=direccion))


def traducir_parrafo_docx(parrafo, direccion: str) -> None:
    runs = parrafo.runs
    texto = "".join(run.text for run in runs)
    if not texto.strip():
        return

    traducido = traducir_texto_con_formato(texto, direccion)
    if runs:
        run_destino = next((run for run in runs if run.text), runs[0])
        run_destino.text = traducido
        for run in runs:
            if run is not run_destino:
                run.text = ""
    else:
        parrafo.add_run(traducido)


def traducir_tabla_docx(tabla, direccion: str, celdas_vistas: set) -> None:
    for fila in tabla.rows:
        for celda in fila.cells:
            identidad = id(celda._tc)
            if identidad in celdas_vistas:
                continue
            celdas_vistas.add(identidad)
            traducir_contenedor_docx(celda, direccion, celdas_vistas)


def traducir_contenedor_docx(contenedor, direccion: str, celdas_vistas: set) -> None:
    for parrafo in contenedor.paragraphs:
        traducir_parrafo_docx(parrafo, direccion)
    for tabla in contenedor.tables:
        traducir_tabla_docx(tabla, direccion, celdas_vistas)


def traducir_docx(contenido: bytes, direccion: str) -> bytes:
    documento = Document(io.BytesIO(contenido))
    celdas_vistas = set()
    traducir_contenedor_docx(documento, direccion, celdas_vistas)
    for seccion in documento.sections:
        for contenedor in (
            seccion.header, seccion.footer,
            seccion.first_page_header, seccion.first_page_footer,
            seccion.even_page_header, seccion.even_page_footer,
        ):
            traducir_contenedor_docx(contenedor, direccion, celdas_vistas)
    salida = io.BytesIO()
    documento.save(salida)
    return salida.getvalue()


def _insertar_texto_pdf(
    pagina: pymupdf.Page,
    rectangulo: pymupdf.Rect,
    texto: str,
    tamano_fuente: float,
    color: Tuple[float, float, float] = (0, 0, 0),
) -> float:
    argumentos = {
        "fontname": FUENTE_PDF,
        "fontsize": tamano_fuente,
        "color": color,
    }
    if ARCHIVO_FUENTE_PDF:
        argumentos["fontfile"] = ARCHIVO_FUENTE_PDF
    return pagina.insert_textbox(rectangulo, texto, **argumentos)


def _pdf_texto_cabe(texto: str, ancho: float, alto: float, tamano_fuente: float) -> bool:
    prueba = pymupdf.open()
    try:
        pagina = prueba.new_page(width=ancho, height=alto)
        margen = min(40.0, ancho * 0.08, alto * 0.08)
        restante = _insertar_texto_pdf(
            pagina,
            pymupdf.Rect(margen, margen, ancho - margen, alto - margen),
            texto,
            tamano_fuente,
        )
        return restante >= 0
    finally:
        prueba.close()


def _escribir_texto_refluido(
    pagina: pymupdf.Page,
    rectangulo: pymupdf.Rect,
    texto: str,
    tamano_fuente: float,
) -> None:
    if _insertar_texto_pdf(pagina, rectangulo, texto, tamano_fuente) < 0:
        raise HTTPException(
            status_code=422,
            detail="No se pudo ajustar todo el texto traducido al PDF.",
        )


def _dividir_parrafo_pdf(
    parrafo: str,
    ancho: float,
    alto: float,
    tamano_fuente: float,
) -> List[str]:
    partes = []
    actual = ""
    for palabra in parrafo.split():
        candidato = f"{actual} {palabra}".strip()
        if _pdf_texto_cabe(candidato, ancho, alto, tamano_fuente):
            actual = candidato
            continue
        if not actual:
            raise HTTPException(
                status_code=422,
                detail="Una palabra del PDF es demasiado larga para redistribuirla.",
            )
        partes.append(actual)
        if not _pdf_texto_cabe(palabra, ancho, alto, tamano_fuente):
            raise HTTPException(
                status_code=422,
                detail="Una palabra del PDF es demasiado larga para redistribuirla.",
            )
        actual = palabra
    if actual:
        partes.append(actual)
    return partes


def _crear_pdf_refluido(
    paginas: List[Tuple[float, float, List[str]]],
) -> bytes:
    salida = pymupdf.open()
    tamano_fuente = 10
    try:
        for ancho, alto, parrafos in paginas:
            if not parrafos:
                salida.new_page(width=ancho, height=alto)
                continue

            texto_pagina = []
            for parrafo in parrafos:
                candidato = "\n\n".join(texto_pagina + [parrafo])
                if _pdf_texto_cabe(candidato, ancho, alto, tamano_fuente):
                    texto_pagina.append(parrafo)
                    continue

                if texto_pagina:
                    pagina = salida.new_page(width=ancho, height=alto)
                    margen = min(40.0, ancho * 0.08, alto * 0.08)
                    _escribir_texto_refluido(
                        pagina,
                        pymupdf.Rect(margen, margen, ancho - margen, alto - margen),
                        "\n\n".join(texto_pagina),
                        tamano_fuente,
                    )
                    texto_pagina = []

                partes = _dividir_parrafo_pdf(
                    parrafo, ancho, alto, tamano_fuente
                )
                texto_pagina.extend(partes)
                while len(texto_pagina) > 1:
                    primera = texto_pagina.pop(0)
                    pagina = salida.new_page(width=ancho, height=alto)
                    margen = min(40.0, ancho * 0.08, alto * 0.08)
                    _escribir_texto_refluido(
                        pagina,
                        pymupdf.Rect(margen, margen, ancho - margen, alto - margen),
                        primera,
                        tamano_fuente,
                    )

            if texto_pagina:
                pagina = salida.new_page(width=ancho, height=alto)
                margen = min(40.0, ancho * 0.08, alto * 0.08)
                _escribir_texto_refluido(
                    pagina,
                    pymupdf.Rect(margen, margen, ancho - margen, alto - margen),
                    "\n\n".join(texto_pagina),
                    tamano_fuente,
                )
        return salida.tobytes()
    finally:
        salida.close()


def traducir_pdf(contenido: bytes, direccion: str) -> bytes:
    documento = pymupdf.open(stream=contenido, filetype="pdf")
    try:
        paginas_traducidas = []
        bloques_traducidos = 0
        for pagina in documento:
            bloques = []
            for bloque in pagina.get_text("dict")["blocks"]:
                if bloque.get("type") != 0:
                    continue
                lineas = [
                    "".join(span["text"] for span in linea["spans"])
                    for linea in bloque["lines"]
                ]
                texto = "\n".join(lineas)
                if not texto.strip():
                    continue
                spans = [
                    span
                    for linea in bloque["lines"]
                    for span in linea["spans"]
                ]
                rectangulo = pymupdf.Rect(bloque["bbox"])
                tamano = max(6, min(18, max(span["size"] for span in spans)))
                color_entero = spans[0]["color"]
                color = (
                    ((color_entero >> 16) & 255) / 255,
                    ((color_entero >> 8) & 255) / 255,
                    (color_entero & 255) / 255,
                )
                bloques.append((
                    rectangulo,
                    traducir_texto_con_formato(texto, direccion),
                    tamano,
                    color,
                ))
            paginas_traducidas.append(
                (pagina.rect.width, pagina.rect.height, bloques)
            )
            bloques_traducidos += len(bloques)

        if bloques_traducidos == 0:
            raise HTTPException(
                status_code=422,
                detail="El PDF no contiene texto seleccionable; los PDF escaneados requieren OCR.",
            )

        necesita_reflujo = False
        for pagina, (_, _, bloques) in zip(documento, paginas_traducidas):
            if not bloques:
                continue
            for rectangulo, _, _, _ in bloques:
                pagina.add_redact_annot(rectangulo, fill=(1, 1, 1), cross_out=False)
            pagina.apply_redactions(images=0)
            for rectangulo, texto, tamano, color in bloques:
                while tamano >= 5:
                    espacio_restante = _insertar_texto_pdf(
                        pagina,
                        rectangulo,
                        texto,
                        tamano,
                        color,
                    )
                    if espacio_restante >= 0:
                        break
                    tamano -= 0.5
                if tamano < 5:
                    necesita_reflujo = True
                    break
            if necesita_reflujo:
                break

        if necesita_reflujo:
            paginas_texto = [
                (
                    ancho,
                    alto,
                    [
                        re.sub(r"\s+", " ", texto).strip()
                        for _, texto, _, _ in bloques
                    ],
                )
                for ancho, alto, bloques in paginas_traducidas
            ]
            return _crear_pdf_refluido(paginas_texto)
        return documento.tobytes()
    finally:
        documento.close()


def nombre_seguro(nombre: str) -> str:
    base = nombre.replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[^a-zA-Z0-9._ -]", "_", base).strip(" .") or "archivo"


@app.post("/traducir-archivo")
def traducir_archivo(
    contenido: bytes = Body(..., media_type="application/octet-stream"),
    nombre: str = "",
    direccion: str = "en-es",
) -> JSONResponse:
    direccion = validar_direccion(direccion)
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(contenido) > TAMANO_MAXIMO_ARCHIVO:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB.")

    nombre = nombre_seguro(nombre)
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension not in {"txt", "docx", "pdf"}:
        raise HTTPException(
            status_code=415,
            detail="Formato no compatible. Sube un archivo .txt, .docx o .pdf.",
        )

    try:
        if extension == "txt":
            texto = contenido.decode("utf-8-sig")
            traducido = traducir_texto_con_formato(texto, direccion)
            salida = traducido.encode("utf-8")
        elif extension == "docx":
            salida = traducir_docx(contenido, direccion)
        else:
            salida = traducir_pdf(contenido, direccion)
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="El archivo TXT debe estar codificado en UTF-8.") from error
    except (zipfile.BadZipFile, PackageNotFoundError) as error:
        raise HTTPException(status_code=422, detail="El archivo Word no es un DOCX válido.") from error
    except pymupdf.FileDataError as error:
        raise HTTPException(status_code=422, detail="El archivo PDF no es válido.") from error

    stem = nombre.rsplit(".", 1)[0]
    nombre_salida = f"{stem}-traducido.{extension}"
    tipo_mime = {
        "txt": "text/plain; charset=utf-8",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
    }[extension]
    return JSONResponse(content={
        "nombre": nombre_salida,
        "tipo_mime": tipo_mime,
        "contenido": base64.b64encode(salida).decode("ascii"),
        "direccion": direccion,
    })


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PUERTO)
