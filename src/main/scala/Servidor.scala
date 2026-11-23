import com.sun.net.httpserver.{HttpServer, HttpExchange, HttpHandler}
import java.net.InetSocketAddress
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets
import java.net.{URI, URLEncoder}
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration

object Servidor {
  val PUERTO = 8080
  private val clienteHttp = HttpClient.newBuilder()
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
        val query = ex.getRequestURI.getQuery
        val texto =
          if (query != null && query.startsWith("texto="))
            java.net.URLDecoder.decode(query.substring(6), "UTF-8")
          else ""
        val limpio = texto.toLowerCase.replaceAll("[^a-záéíóúñü0-9 ]", "").trim
        val resp   = traducirConPython(limpio)
        val bytes  = resp.getBytes(StandardCharsets.UTF_8)
        ex.getResponseHeaders.set("Content-Type", "application/json; charset=UTF-8")
        ex.sendResponseHeaders(200, bytes.length)
        ex.getResponseBody.write(bytes)
        ex.close()
      }
    })

    servidor.start()
    println("=" * 50)
    println(s"Servidor activo en http://localhost:$PUERTO")
    println("=" * 50)

    // ⬇️ ESTA LÍNEA ES LA CLAVE: mantiene el proceso vivo hasta Ctrl+C
    Thread.currentThread().join()
  }

  def traducirConPython(texto: String): String = {
    if (texto.isEmpty) return jsonError("Texto vacío", "")

    val textoCodificado = URLEncoder.encode(texto, "UTF-8")
    val url = URI.create(s"http://127.0.0.1:5001/traducir?texto=$textoCodificado")
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

  private def jsonError(mensaje: String, detalle: String): String =
    s"""{"error":${escapeJsonString(mensaje)},"detalle":${escapeJsonString(detalle)},"traduccion":""}"""

  private def escapeJsonString(texto: String): String =
    "\"" + texto.replace("\\", "\\\\")
      .replace("\"", "\\\"")
      .replace("\n", "\\n")
      .replace("\r", "\\r") + "\""
}