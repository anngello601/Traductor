import json
import re
import urllib.error
import urllib.request
from typing import Dict, List
import uvicorn

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PUERTO = 5001
URL_PROLOG = "http://127.0.0.1:5002/traducir"

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
}


class SolicitudTraduccion(BaseModel):
    texto: str


app = FastAPI(title="Traductor Python NLP")


def limpiar_texto(texto: str) -> str:
    texto = texto.lower().strip()
    return re.sub(r"[^a-záéíóúñü0-9 ]", "", texto)


def tokenizar(texto: str) -> List[str]:
    return [token for token in texto.split() if token]


def proponer_traduccion(tokens: List[str]) -> List[str]:
    propuesta = [DICCIONARIO.get(token, token) for token in tokens]

    if len(tokens) >= 4 and tokens[:2] == ["i", "am"]:
        for indice in range(2, len(tokens) - 1):
            if tokens[indice:indice + 2] == ["years", "old"]:
                edad = propuesta[2:indice]
                resto = propuesta[indice + 2:]
                propuesta = ["yo", "tengo"] + edad + ["años"] + resto
                break
            if tokens[indice:indice + 2] == ["year", "old"]:
                edad = propuesta[2:indice]
                resto = propuesta[indice + 2:]
                propuesta = ["yo", "tengo"] + edad + ["año"] + resto
                break

    if len(tokens) >= 3 and tokens[:2] == ["i", "have"]:
        propuesta[:2] = ["yo", "tengo"]

    for indice in range(len(propuesta) - 1):
        if propuesta[indice:indice + 2] == ["años", "viejo"]:
            propuesta[indice + 1:indice + 2] = []
            break

    if len(propuesta) >= 2 and propuesta[0] == "yo" and propuesta[1] == "tener":
        propuesta[1] = "tengo"
    elif len(propuesta) >= 2 and propuesta[0] in {"él", "ella"} and propuesta[1] == "tener":
        propuesta[1] = "tiene"
    elif len(propuesta) >= 2 and propuesta[0] == "nosotros" and propuesta[1] == "tener":
        propuesta[1] = "tenemos"
    elif len(propuesta) >= 2 and propuesta[0] == "ellos" and propuesta[1] == "tener":
        propuesta[1] = "tienen"
    if "grande" in propuesta and "casa" in propuesta:
        indice_grande = propuesta.index("grande")
        indice_casa = propuesta.index("casa")
        if indice_casa == indice_grande + 1:
            propuesta[indice_grande], propuesta[indice_casa] = propuesta[indice_casa], propuesta[indice_grande]
            if indice_grande > 0 and propuesta[indice_grande - 1] == "un":
                propuesta[indice_grande - 1] = "una"
    return propuesta


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
    texto = limpiar_texto(solicitud.texto)
    if not texto:
        return JSONResponse(
            status_code=400,
            content={"error": "Texto vacío", "traduccion": ""},
        )

    tokens = tokenizar(texto)
    propuesta = proponer_traduccion(tokens)
    resultado = validar_con_prolog(texto, propuesta)
    return JSONResponse(content={
        "traduccion": resultado["traduccion"],
        "propuesta_python": " ".join(propuesta),
        "validacion": resultado,
        "tokens": tokens,
    })


@app.get("/traducir")
def traducir_get(texto: str = "") -> JSONResponse:
    return traducir(SolicitudTraduccion(texto=texto))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PUERTO)
