from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event, Thread
from typing import Optional
import argparse
import time


@dataclass
class EstadoSector:
    nombre: str
    estado: str = "PENDIENTE"
    paso: int = 0
    completado: bool = False
    error_en: Optional[int] = None
    objetivo: str = ""
    rgb: Optional[tuple[int, int, int]] = None


@dataclass
class EstadoJuego:
    sector1: EstadoSector = field(default_factory=lambda: EstadoSector("Memoria"))
    sector2: EstadoSector = field(default_factory=lambda: EstadoSector("Musical"))
    sector3: EstadoSector = field(default_factory=lambda: EstadoSector("RGB"))
    sector4: EstadoSector = field(default_factory=lambda: EstadoSector("Morse"))
    ultimo_mensaje: str = ""
    conexion: str = "SIN CONEXION"
    error_conexion: str = ""

    def procesar_mensaje(self, mensaje: str) -> bool:
        """Actualiza las variables del juego a partir de una linea recibida.

        Devuelve True si la linea tiene un formato y evento reconocido.
        """
        mensaje = mensaje.strip()
        partes = mensaje.split(":", 2)
        if len(partes) != 3 or partes[0] not in {"S1", "S2", "S3", "S4"}:
            return False

        codigo, evento, valor = partes
        sector = getattr(self, "sector" + codigo[1])
        evento = evento.upper()

        if evento == "START":
            sector.estado = "EN CURSO"
            sector.paso = 0
            sector.completado = False
            sector.error_en = None
            sector.rgb = None
            sector.objetivo = ""

        elif evento == "STEP":
            if not valor.isdecimal():
                return False
            sector.paso = int(valor)
            sector.error_en = None
            sector.estado = "EN CURSO"

        elif evento == "FAIL":
            if not valor.isdecimal():
                return False
            sector.error_en = int(valor)
            sector.paso = 0
            sector.estado = "ERROR / REINTENTO"

        elif evento == "COMPLETE":
            if valor != "1":
                return False
            sector.completado = True
            sector.estado = "COMPLETADO"
            sector.error_en = None

        elif evento == "TARGET":
            sector.objetivo = valor

        elif evento == "RGB":
            try:
                canales = tuple(int(x.strip()) for x in valor.split(","))
            except ValueError:
                return False
            if len(canales) != 3 or any(x not in (0, 1) for x in canales):
                return False
            sector.rgb = canales

        else:
            return False

        self.ultimo_mensaje = mensaje
        return True


class ReceptorArduino:
    """Lee serial en otro hilo para no bloquear la interfaz Tkinter."""

    def __init__(self, puerto: str, baudios: int = 9600):
        self.puerto = puerto
        self.baudios = baudios
        self.cola: Queue[tuple[str, str]] = Queue()
        self._detener = Event()
        self._serie = None
        self._hilo: Optional[Thread] = None

    def iniciar(self) -> None:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("Falta pyserial: python -m pip install pyserial") from exc

        try:
            self._serie = serial.Serial(self.puerto, self.baudios, timeout=0.2)
        except serial.SerialException as exc:
            raise RuntimeError(f"No se pudo abrir {self.puerto}: {exc}") from exc

        self._detener.clear()
        self._hilo = Thread(target=self._leer, daemon=True)
        self._hilo.start()

    def _leer(self) -> None:
        while not self._detener.is_set():
            try:
                datos = self._serie.readline()
            except Exception as exc:
                if not self._detener.is_set():
                    self.cola.put(("ERROR", str(exc)))
                return
            if datos:
                texto = datos.decode("utf-8", errors="replace").strip()
                if texto:
                    self.cola.put(("DATO", texto))

    def actualizar(self, estado: EstadoJuego) -> list[str]:
        """Llamar desde el hilo principal de Tkinter (por ejemplo, en after())."""
        recibidos = []
        while True:
            try:
                tipo, contenido = self.cola.get_nowait()
            except Empty:
                break
            if tipo == "ERROR":
                estado.conexion = "DESCONECTADO"
                estado.error_conexion = contenido
            else:
                recibidos.append(contenido)
                estado.procesar_mensaje(contenido)
        return recibidos

    def cerrar(self) -> None:
        self._detener.set()
        if self._hilo and self._hilo.is_alive():
            self._hilo.join(timeout=0.5)
        if self._serie and self._serie.is_open:
            self._serie.close()


MENSAJES_DEMO = [
    "S1:START:1", "S1:STEP:1", "S1:STEP:2", "S1:STEP:8", "S1:COMPLETE:1",
    "S2:START:1", "S2:STEP:1", "S2:STEP:2", "S2:STEP:3", "S2:STEP:4", "S2:COMPLETE:1",
    "S3:START:1", "S3:RGB:1,0,1", "S3:RGB:1,1,1", "S3:COMPLETE:1",
    "S4:START:1", "S4:TARGET:ABC", "S4:STEP:1", "S4:STEP:5", "S4:COMPLETE:1",
]


def resumen(estado: EstadoJuego) -> str:
    return " | ".join(
        f"S{i}={getattr(estado, f'sector{i}').estado}"
        for i in range(1, 5)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Lee y guarda estados de Arduino en variables Python")
    opciones = parser.add_mutually_exclusive_group(required=True)
    opciones.add_argument("--demo", action="store_true", help="Probar sin Arduino fisico")
    opciones.add_argument("--puerto", help="Puerto serial, ej. /dev/ttyACM0 o COM3")
    args = parser.parse_args()
    estado = EstadoJuego()

    if args.demo:
        for mensaje in MENSAJES_DEMO:
            estado.procesar_mensaje(mensaje)
            print(f"{mensaje:<20} -> {resumen(estado)}")
        print("\nVariables: estado.sector1, estado.sector2, estado.sector3, estado.sector4")
        return

    lector = ReceptorArduino(args.puerto)
    try:
        lector.iniciar()
        estado.conexion = "CONECTADO"
        print(f"Conectado a {args.puerto} a 9600 baudios. Ctrl+C para salir.")
        while estado.conexion == "CONECTADO":
            for mensaje in lector.actualizar(estado):
                print(f"{mensaje:<20} -> {resumen(estado)}")
            time.sleep(0.05)
        print("Error de conexion:", estado.error_conexion)
    except RuntimeError as exc:
        print(exc)
    except KeyboardInterrupt:
        print("\nLectura detenida.")
    finally:
        lector.cerrar()

if __name__ == "__main__":
    main()
