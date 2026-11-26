import pymupdf
import unittest

import servidor


class PruebasVocabularioYReglas(unittest.TestCase):
    def test_traduce_parrafo_tecnico_en_ambas_direcciones(self):
        ingles = (
            "The administrator of an organization detects anomalous behavior: "
            "a computer is sending a large number of TCP SYN packets to a server, "
            "but many connections never complete the session establishment."
        )
        espanol = (
            "El administrador de una organización detecta un comportamiento "
            "anómalo: una computadora está enviando una gran cantidad de "
            "paquetes TCP SYN hacia un servidor, pero muchas conexiones nunca "
            "llegan a completar el establecimiento de la sesión."
        )

        self.assertEqual(
            servidor.traducir_texto_con_formato(ingles, "en-es"),
            "El administrador de una organización detecta un comportamiento "
            "anómalo: una computadora está enviando una gran cantidad de "
            "paquetes TCP SYN a un servidor, pero muchas conexiones nunca "
            "completan el establecimiento de la sesión.",
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(espanol, "es-en"),
            "The administrator of an organization detects anomalous behavior: "
            "a computer is sending a large number of TCP SYN packets to a server, "
            "but many connections never complete the session setup.",
        )

    def test_repara_salida_mixta_del_ejemplo_en_ambas_direcciones(self):
        texto_mixto = (
            "The administrator of a organización detecta a comportamiento "
            "anómalo: a computadora está enviando a gran cantidad of paquetes "
            "TCP SYN hacia a servidor, but muchas conexiones never llegan to "
            "completar the establecimiento of la sesión."
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(texto_mixto, "en-es"),
            "El administrador de una organización detecta un comportamiento "
            "anómalo: una computadora está enviando una gran cantidad de "
            "paquetes TCP SYN a un servidor, pero muchas conexiones nunca "
            "llegan a completar el establecimiento de la sesión.",
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(texto_mixto, "es-en"),
            "The administrator of an organization detects anomalous behavior: "
            "a computer is sending a large number of TCP SYN packets to a server, "
            "but many connections never complete the session setup.",
        )

    def test_traduce_ataques_y_conserva_siglas(self):
        ingles = (
            "This is a SYN Flood attack, a form of denial of service (DoS). "
            "It may also be DDoS if multiple devices participate."
        )
        espanol = (
            "Este es un ataque SYN Flood, una forma de denegación de servicio "
            "(DoS). También puede ser DDoS si participan varios dispositivos."
        )

        self.assertEqual(
            servidor.traducir_texto_con_formato(ingles, "en-es"),
            espanol,
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(
                "Tengo dos libros.", "es-en"
            ),
            "I have two books.",
        )

    def test_regla_de_edad_funciona_en_ambos_idiomas(self):
        self.assertEqual(
            servidor.traducir_texto_con_formato("I am five years old.", "en-es"),
            "Yo tengo cinco años.",
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato("Tengo cinco años.", "es-en"),
            "I am five years old.",
        )

    def test_traduce_vocabulario_de_proyectos_en_ambas_direcciones(self):
        ingles = (
            "Mateo committed to deliver a clean database, but it was not "
            "delivered and he did not notify the team."
        )
        espanol = (
            "Mateo se comprometió a entregar una base de datos limpia, pero "
            "no se entregó y no avisó al equipo."
        )

        self.assertEqual(
            servidor.traducir_texto_con_formato(ingles, "en-es"),
            espanol,
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(espanol, "es-en"),
            "Mateo committed to deliver a clean database, but it was not "
            "delivered and did not notify the team.",
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(
                "On Tuesday, Valeria wrote Mateo a message. "
                "It was marked as seen with no response.",
                "en-es",
            ),
            "El martes, Valeria le escribió a Mateo un mensaje. "
            "Figuraba como visto sin respuesta.",
        )
        self.assertEqual(
            servidor.traducir_texto_con_formato(
                "El martes, Valeria le escribió a Mateo un mensaje. "
                "El mensaje figuraba como visto y no recibió respuesta.",
                "es-en",
            ),
            "On Tuesday, Valeria sent Mateo a message. "
            "The message was marked as seen and received no response.",
        )

    def test_refluye_pdf_cuando_el_texto_no_cabe_en_su_caja(self):
        original = pymupdf.open()
        pagina = original.new_page(width=200, height=200)
        pagina.insert_text(
            (20, 30),
            "hello Σ × ÷",
            fontname="china-s",
            fontsize=1,
        )

        traducido = pymupdf.open(
            stream=servidor.traducir_pdf(original.tobytes(), "en-es"),
            filetype="pdf",
        )
        try:
            self.assertEqual(traducido.page_count, 1)
            texto = traducido[0].get_text()
            self.assertIn("hola", texto.lower())
            self.assertIn("Σ", texto)
            self.assertIn("×", texto)
            self.assertIn("÷", texto)
        finally:
            traducido.close()
            original.close()

    def test_crea_paginas_de_continuacion_sin_perder_texto(self):
        palabras = 1500
        original = pymupdf.open()
        pagina = original.new_page(width=612, height=792)
        texto = " ".join(["behavior"] * palabras)
        restante = pagina.insert_textbox(
            pymupdf.Rect(20, 20, 592, 772),
            texto,
            fontname="helv",
            fontsize=5,
        )
        self.assertGreaterEqual(restante, 0)

        traducido = pymupdf.open(
            stream=servidor.traducir_pdf(original.tobytes(), "en-es"),
            filetype="pdf",
        )
        try:
            texto_traducido = " ".join(
                pagina.get_text() for pagina in traducido
            )
            self.assertGreater(traducido.page_count, 1)
            self.assertEqual(
                texto_traducido.lower().split().count("comportamiento"),
                palabras,
            )
        finally:
            traducido.close()
            original.close()


if __name__ == "__main__":
    unittest.main()
