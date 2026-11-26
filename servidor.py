import base64
import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from typing import Dict, List
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

DICCIONARIO_ES_EN = {traduccion: palabra for palabra, traduccion in DICCIONARIO.items()}
DICCIONARIO_ES_EN.update({
    "hola": "hello", "adiós": "goodbye", "gracias": "thanks",
    "yo": "i", "tú": "you", "él": "he", "ella": "she",
    "nosotros": "we", "ellos": "they", "mi": "my", "tu": "your",
    "su": "their", "nuestro": "our", "el": "the", "un": "a",
    "una": "a", "es": "is", "son": "are", "soy": "am",
    "era": "was", "eran": "were", "tengo": "have", "tiene": "has",
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
})


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


def proponer_traduccion(tokens: List[str], direccion: str = "en-es") -> List[str]:
    diccionario = DICCIONARIO if direccion == "en-es" else DICCIONARIO_ES_EN
    propuesta = [diccionario.get(token, token) for token in tokens]

    if direccion == "es-en":
        return propuesta

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
    direccion = validar_direccion(solicitud.direccion)
    texto = limpiar_texto(solicitud.texto)
    if not texto:
        return JSONResponse(
            status_code=400,
            content={"error": "Texto vacío", "traduccion": ""},
        )

    tokens = tokenizar(texto)
    propuesta = proponer_traduccion(tokens, direccion)
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


def traducir_texto_con_formato(texto: str, direccion: str) -> str:
    diccionario = DICCIONARIO if direccion == "en-es" else DICCIONARIO_ES_EN

    def traducir_palabra(coincidencia: re.Match[str]) -> str:
        palabra = coincidencia.group(0)
        traduccion = diccionario.get(palabra.lower(), palabra.lower())
        if palabra.isupper():
            return traduccion.upper()
        if palabra[0].isupper():
            return traduccion.capitalize()
        return traduccion

    return re.sub(r"[a-záéíóúüñ]+", traducir_palabra, texto, flags=re.IGNORECASE)


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


def traducir_pdf(contenido: bytes, direccion: str) -> bytes:
    documento = pymupdf.open(stream=contenido, filetype="pdf")
    bloques_traducidos = 0
    try:
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
                pagina.add_redact_annot(rectangulo, fill=(1, 1, 1), cross_out=False)

            if bloques:
                pagina.apply_redactions(images=0)
                bloques_traducidos += len(bloques)
                for rectangulo, texto, tamano, color in bloques:
                    while tamano >= 5:
                        espacio_restante = pagina.insert_textbox(
                            rectangulo,
                            texto,
                            fontname="helv",
                            fontsize=tamano,
                            color=color,
                        )
                        if espacio_restante >= 0:
                            break
                        tamano -= 0.5
                    if tamano < 5:
                        raise HTTPException(
                            status_code=422,
                            detail="La traducción no cabe en el diseño del PDF.",
                        )

        if bloques_traducidos == 0:
            raise HTTPException(
                status_code=422,
                detail="El PDF no contiene texto seleccionable; los PDF escaneados requieren OCR.",
            )
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
