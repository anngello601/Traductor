import com.sun.net.httpserver.{HttpServer, HttpExchange, HttpHandler}
import java.net.InetSocketAddress
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets
import java.net.{URI, URLEncoder}
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration

object Servidor {
  val PUERTO = 8080
  private val TAMANO_MAXIMO_ARCHIVO = 10 * 1024 * 1024
  private val clienteHttp = HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_1_1)
    .connectTimeout(Duration.ofSeconds(5))
    .build()

  def main(args: Array[String]): Unit = {
    val servidor = HttpServer.create(new InetSocketAddress(PUERTO), 0)

    // Ruta raíz: sirve el index.html
    servidor.createContext("/", new HttpHandler {
      def handle(ex: HttpExchange): Unit = {
        try {
          val html = Files.readAllBytes(Paths.get("src/main/resources/index.html"))
          ex.getResponseHeaders.set("Content-Type", "text/html; charset=UTF-8")
          ex.sendResponseHeaders(200, html.length)
          ex.getResponseBody.write(html)
        } catch {
          case e: Exception =>
            val err = jsonError("No se pudo cargar la interfaz", e.getMessage)
              .getBytes(StandardCharsets.UTF_8)
            ex.sendResponseHeaders(500, err.length)
            ex.getResponseBody.write(err)
        } finally ex.close()
      }
    })

    // Ruta pública: Scala coordina Python y Prolog, pero no ejecuta procesos externos.
    servidor.createContext("/traducir", new HttpHandler {
      def handle(ex: HttpExchange): Unit = {
        try {
          val parametros = leerParametros(ex.getRequestURI)
          val texto = parametros.getOrElse("texto", "")
          val direccion = parametros.getOrElse("direccion", "en-es")
          val resp = traducirConPython(texto.trim, direccion)
          responder(ex, 200, resp)
        } finally ex.close()
      }
    })

    servidor.createContext("/traducir-archivo", new HttpHandler {
      def handle(ex: HttpExchange): Unit = {
        try {
          if (ex.getRequestMethod != "POST") {
            responder(ex, 405, jsonError("Método no permitido", "Usa POST"))
          } else {
            val contenido = ex.getRequestBody.readNBytes(TAMANO_MAXIMO_ARCHIVO + 1)
            if (contenido.length > TAMANO_MAXIMO_ARCHIVO) {
              responder(ex, 413, jsonError("Archivo demasiado grande", "Máximo 10 MB"))
            } else if (contenido.isEmpty) {
              responder(ex, 400, jsonError("Archivo vacío", ""))
            } else {
              val parametros = leerParametros(ex.getRequestURI)
              val direccion = parametros.getOrElse("direccion", "en-es")
              val nombre = parametros.getOrElse("nombre", "")
              val (estado, respuesta) = traducirArchivoConPython(contenido, direccion, nombre)
              responder(ex, estado, respuesta)
            }
          }
        } finally ex.close()
      }
    })

    servidor.start()
    println("=" * 50)
    println(s"Servidor activo en http://localhost:$PUERTO")
    println("=" * 50)

    // ⬇️ ESTA LÍNEA ES LA CLAVE: mantiene el proceso vivo hasta Ctrl+C
    Thread.currentThread().join()
  }

  def traducirConPython(texto: String, direccion: String): String = {
    if (texto.isEmpty) return jsonError("Texto vacío", "")

    val textoCodificado = URLEncoder.encode(texto, "UTF-8")
    val direccionCodificada = URLEncoder.encode(direccion, "UTF-8")
    val url = URI.create(
      s"http://127.0.0.1:5001/traducir?texto=$textoCodificado&direccion=$direccionCodificada"
    )
    val request = HttpRequest.newBuilder(url)
      .GET()
      .timeout(Duration.ofSeconds(10))
      .build()

    try {
      val response = clienteHttp.send(
        request,
        HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)
      )
      if (response.statusCode() == 200) response.body().trim
      else jsonError(
        s"Python respondió con código ${response.statusCode()}",
        response.body()
      )
    } catch {
      case _: Exception =>
        jsonError("Servicio Python no disponible", "")
    }
  }

  private def traducirArchivoConPython(
    contenido: Array[Byte],
    direccion: String,
    nombre: String
  ): (Int, String) = {
    val direccionCodificada = URLEncoder.encode(direccion, "UTF-8")
    val nombreCodificado = URLEncoder.encode(nombre, "UTF-8")
    val url = URI.create(
      s"http://127.0.0.1:5001/traducir-archivo?direccion=$direccionCodificada&nombre=$nombreCodificado"
    )
    val request = HttpRequest.newBuilder(url)
      .header("Content-Type", "application/octet-stream")
      .POST(HttpRequest.BodyPublishers.ofByteArray(contenido))
      .timeout(Duration.ofSeconds(30))
      .build()

    try {
      val response = clienteHttp.send(
        request,
        HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)
      )
      (response.statusCode(), response.body().trim)
    } catch {
      case _: Exception =>
        (503, jsonError("Servicio Python no disponible", ""))
    }
  }

  private def leerParametros(uri: URI): Map[String, String] =
    Option(uri.getRawQuery).toSeq
      .flatMap(_.split("&"))
      .flatMap { parametro =>
        parametro.split("=", 2) match {
          case Array(clave, valor) =>
            Some(
              java.net.URLDecoder.decode(clave, "UTF-8") ->
                java.net.URLDecoder.decode(valor, "UTF-8")
            )
          case Array(clave) =>
            Some(java.net.URLDecoder.decode(clave, "UTF-8") -> "")
        }
      }
      .toMap

  private def responder(ex: HttpExchange, estado: Int, contenido: String): Unit = {
    val bytes = contenido.getBytes(StandardCharsets.UTF_8)
    ex.getResponseHeaders.set("Content-Type", "application/json; charset=UTF-8")
    ex.sendResponseHeaders(estado, bytes.length)
    ex.getResponseBody.write(bytes)
  }

  private def jsonError(mensaje: String, detalle: String): String =
    s"""{"error":${escapeJsonString(mensaje)},"detalle":${escapeJsonString(detalle)},"traduccion":""}"""

  private def escapeJsonString(texto: String): String =
    "\"" + texto.replace("\\", "\\\\")
      .replace("\"", "\\\"")
      .replace("\n", "\\n")
      .replace("\r", "\\r") + "\""
}