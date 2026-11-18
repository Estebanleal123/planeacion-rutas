"""Arranca el simulador de la exposición.

    py -3 simulador.py
    py -3 simulador.py --probar
"""

import argparse
import json
import sys
import webbrowser

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import modelo

CARPETA = Path(__file__).resolve().parent
PAGINA = CARPETA / "web" / "index.html"
PUERTO = 8765


def _numero(parametros, nombre, defecto, tipo):
    valor = parametros.get(nombre, [None])[0]
    if valor is None or valor == "":
        return defecto
    return tipo(valor)


def calcular(parametros):
    semilla = parametros.get("semilla", [None])[0]
    return modelo.planear(
        tecnico_id=parametros.get("tecnico", ["mariana"])[0],
        lam=_numero(parametros, "lam", 3.0, float),
        c=_numero(parametros, "c", 45, int),
        umbral=_numero(parametros, "umbral", 0.90, float),
        jornada=_numero(parametros, "jornada", 480, int),
        servicio=_numero(parametros, "servicio", 40, int),
        vecinos=_numero(parametros, "vecinos", 3, int),
        p_repuesto=_numero(parametros, "p", 0.30, float),
        semilla=int(semilla) if semilla not in (None, "") else None,
    )


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        return

    def _enviar(self, codigo, cuerpo, tipo):
        datos = cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._enviar(200, PAGINA.read_text(encoding="utf-8"), "text/html; charset=utf-8")
            return
        if url.path == "/api/plan":
            try:
                resultado = calcular(parse_qs(url.query))
            except (KeyError, ValueError) as exc:
                self._enviar(
                    400,
                    json.dumps({"error": str(exc)}, ensure_ascii=False),
                    "application/json; charset=utf-8",
                )
                return
            self._enviar(
                200,
                json.dumps(resultado, ensure_ascii=False),
                "application/json; charset=utf-8",
            )
            return
        if url.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self._enviar(404, "No encontrado", "text/plain; charset=utf-8")


def servir(abrir):
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    direccion = f"http://127.0.0.1:{PUERTO}"
    print(f"\nSimulador listo en {direccion}", flush=True)
    print("Deja esta ventana abierta durante la exposición. Ctrl+C lo cierra.\n", flush=True)
    if abrir:
        webbrowser.open(direccion)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSimulador cerrado.")
    finally:
        servidor.server_close()


def main():
    parser = argparse.ArgumentParser(description="Simulador de rutas para Matemática Discreta")
    parser.add_argument("--probar", action="store_true", help="solo imprime el caso de la diapositiva")
    parser.add_argument("--sin-navegador", action="store_true", help="no abre el navegador")
    args = parser.parse_args()

    resultado = modelo.verificar()
    print(modelo.informe(resultado))
    if args.probar:
        return
    servir(abrir=not args.sin_navegador)


if __name__ == "__main__":
    main()
