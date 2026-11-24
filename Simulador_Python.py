# Proyecto integrador de Programación - 4.º C
# Benjamín Oller, Lucca García y Fausto Monserrat
# Requisitos: Python 3.10+, customtkinter, pyserial y pillow.
# Demo: python Simulador_Python.py --demo
# Real: python Simulador_Python.py --puerto COM3 (o /dev/ttyACM0)
"""Puente Arduino -> Python: mensajes seriales y variables para Tkinter.

Protocolo esperado: S1:EVENTO:VALOR, S2:EVENTO:VALOR, etc.
Ejemplos: S1:STEP:3, S2:COMPLETE:1, S3:RGB:1,0,1, S4:TARGET:ABC.
"""

from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event, Thread
from typing import Optional
import argparse
import time
import math
import base64
from io import BytesIO


@dataclass
class EstadoSector:
    nombre: str
    estado: str = "PENDIENTE"
    paso: int = 0
    completado: bool = False
    error_en: Optional[int] = None
    objetivo: str = ""
    rgb: Optional[tuple[int, int, int]] = None
    color_jugador: Optional[tuple[int, int, int]] = None


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
            sector.color_jugador = None

        elif evento in {"READY", "RETRY"}:
            sector.estado = "EN CURSO"
            if evento == "RETRY":
                sector.paso = 0
                sector.error_en = None

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

        elif evento == "COLOR" and codigo == "S3":
            try:
                canales = tuple(int(x.strip()) for x in valor.split(","))
            except ValueError:
                return False
            if len(canales) != 3 or any(not 0 <= x <= 255 for x in canales):
                return False
            sector.color_jugador = canales

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

    def actualizar(self, estado: EstadoJuego, procesar: bool = True) -> list[str]:
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
                if procesar:
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
    "S3:START:1", "S3:TARGET:147,76,203", "S3:COLOR:62,120,160",
    "S3:RGB:0,0,0", "S3:COLOR:147,76,203", "S3:RGB:1,1,1", "S3:COMPLETE:1",
    "S4:START:1", "S4:TARGET:ABCD", "S4:STEP:1", "S4:STEP:5", "S4:COMPLETE:1",
]

import customtkinter as ctk
from PIL import Image



COLORES = {
    "fondo": "#09121D",
    "panel": "#142333",
    "card": "#1B2D40",
    "borde": "#2E4355",
    "texto": "#ECF4FC",
    "secundario": "#A8BBCD",
    "cyan": "#60D8E9",
    "verde": "#6AE7B0",
    "rojo": "#FF8088",
    "amarillo": "#F8CE77",
}

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
}

DATOS_SECTORES = (
    (1, "Memoria", "Repetí la secuencia de ocho luces", 8),
    (2, "Desafío musical", "Repetí las cuatro notas", 4),
    (3, "Colores RGB", "Igualá el color objetivo", 3),
    (4, "Código Morse", "Ingresá puntos y rayas", None),
)



# Imagen Morse incluida dentro del archivo para no depender de un PNG externo.
IMAGEN_MORSE_BASE64 = (
    "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"
    "vbQgr1+urwG8mtq61T/8+PJDP/cw+Z6OKpyY93St37j5iutu8n+/S5jJ8n2hsBTsTW81NT4vl5QkKdP3FE6qczqdr77xtvfy6665"
    "0tWkjhk1Uvapqi+/9mZwRzTF+XzjlX8eLd7p+u/wvu27Nn+7+IN37r7zdl9drMPhuOv39x4vK/e/26+Wr/h23YZAi5EkadCA/Buu"
    "verdNxet/vqLG6+7Jjpa3BENAPBP0Eb2sksutFgssqsWf/6lxzMbP1n8ua9BhfnnzVPxSe7CMuPp6upyPPCnv151/c1+JpcNS3Fx"
    "8X7WNjX5/CjZ36t8fwAtSVKCj2nzNfLOfz7wnocru2+fuXPOknwMx27YtCXQR6O5hd/5bGpq+uVtd37y2RdKNr7l9rvKeup3/eiX"
    "m/PgfX/4ZsmnY0+T+esCAMQnaiN78YW+Vn34iec9yBWVJ3w9YTUlJXnOWWeqWJiYzHi6oqKs/3f3nc8983ik3Yli8z0zqCRJrW2t"
    "Qeyzxatx7M7PXKRaaGxs+s8HH3svv+mGazMyeqs465ZLOJ1Pe1fXex98NOf8Sz7/cqnCl9TU1F585fXbduwM5bh5/XLffeOVi+af"
    "F8pOAMAQIjaykyaM8zXBzfGyctkp0z/yatfcwn5CWfOeLqvVeu45cz7/+L2IenpFe4fPh6BKkhTvd3zRl4R4f6/q8HtELbzy2pve"
    "o/6TJ45/6L57vG/MKq+o/HJp8HNWhM35PFZ6/PKrb7zjf/+vvKIyoBdWnTx52dU3PvTnR0+dagz66DExMY8/8hDjsgBMR8RG1s98"
    "qN7jiy6LP19it9tlV808fYaf6UvDgNlPV0J8/N+feXzGtCl6HtRAbX7HCBMTg/nYulevXn7WtrYGMyoZioOHDq9eu857+bnnyEzU"
    "//qb/+7qcgR9rLA5n/3z+r339qv33fO/QVzeY7fb//nyq9Nmzb33jw/v2r03uAJiYmL+9Md7g3stABhFuGv84+Js558719daX8+m"
    "qm9oWLFqzVmzZnqvioqyXjz//H++tEi1EtV23U0/lf1XXwnRTpf3e4mLs2VmZIwfd9oN1141YdxY2VdFR0U9+eifzpw7389kQwEd"
    "VGQnq/3dfpTRO5gbs9LT0/we0YCrkBXeUN/e3v7WO8HMuuUWTuczOirqRwuuHzFs6IKf/qKtzeccsb40Nja9+sbbr77xdt8+WadP"
    "nzp1yqTxY08L6NKdEcOHzTx9+opVgc2862KuX0MAYUO4Edl5c89OTEyUXbV3f3HxgRJfL/T3/NXwnbtA/NPV1tZeerzsw48XX37N"
    "guf/+ZKvzbIyM2+87ioVjyus8ooKP2uHDi0IYp/Dh/l8IoAkSRUBflStiuUrVimZG/ijTz+vrasL5UDhdz6nTJ746J8fDGUPlSeq"
    "3n3/o9/+7p6Zc84fM3HGTT/95d+e/+e2HTuVzLQ1+8wzQjk0AOhMuBFZP9doDh9aeLQ4mHsahhUWFI0YvntPkJ+4icxEp8vpdD7y"
    "2FMzz5jh6zlMl1184XMv+Ox0w8ahw0c7Ozt9zeFfMHhQbGxsoHP4jxg+zM/a/cU+/57RjsPhePWNt+/9/V3+NwvlNi8XU5xP92il"
    "zWbL7ttn+tTJ//Pjm/yMlV54/rnfrFj9nw9l7pkLVH1Dw/IVq5avWPXoE8/07ZN17VVX/PTHC/xcBDxxvPzHJgAgJrFGZF0Rr8We"
    "rwjHQVnTnS6n0/npYp+TChUMGZya4u+58+Ghs7Nzn+9Z+qOjo2eePj2gHcbExMyc4e8lO3btDmiHavn3e+97z8PVXSizbrmZ63y2"
    "t7cfOXrsjbffPWf+pV9/s9LPlvfcfWdyclLQB5JVeaLqiWeenX/p1X5uC/N+6BoAiEysRvbSi+ZbrZqUdNH888Jv0m8znq7DR4/6"
    "Wetr+oUws+qHj6jwEOgsSLNnnp6SkuxrbenxslAe/xuKxsam9z/8xM8Gr7wW6nCsixnPZ1tb+y9vu8PPxT+909N+8dMfh34gbyUH"
    "D/1r0Wu+1qamhv8fkwDCiViN7GWX+JwPNUTpaWmzzzxdo50bxYyny2rx97+c/7vFw8aSZV/7WXvuOXMKhgxWuCur1fqrX/6Pnw2W"
    "frU8gMrUJjsPl0tF5Ykvl3ylylFMej5bW9t+94f7/Fy3etON1/buna7W4brbtt3nRUdB3GQGAAYSqJEdO2b04EEDtdt/mE0oa9LT"
    "NWBAvp+1jU3BT4RpIlu37/BznWV0VNQf7/29r0e1ebj6iktHjyzys8Hb74Y0J0CISg4e8nUn+2tvvO3xzLmgmfd8bt2+w88TvBLi"
    "43/245t8rY2Ksr796r98PZvav7i4OF+rQrz3DgB0JlAjq/XcAmfNmpme5m9WHXMx4+myWq0Xnj/PzwaR87haP5/tSpI0ferkB/7f"
    "73vcyfSpk/94r7/NVq9dZ8idXt298tqb3gtDn3XLg3nP51MLn3M4fE6je8N1V/v6NbRIlqlTJr3zxiv/fu2l6VMnK+zUXc45e7av"
    "VdV+pzMDANGI0sjGxsbOP89fixO66OjoCy84V9ND6MaMp8tisfzhd78tLBjia4Pq6pqqiGlk33v/w5KDh/xscON11zzzxF98NjEW"
    "y43XXfPi8wv9TJ7vdDofeezJUAsN2dffrPS+qDT0Wbc8mPd8Hjx0+NPPv/S1NiE+/n98D8q6TJk88c1FL67++ovf/voWJVeZ33Dt"
    "VZdePN/X2k1btva4BwAQhyj3P80560xfN1g4HI6JM2YrHyd46P7/u+Fa+RlJL7/kItnxIT/eeOWfAW0vSdKUM86uqDwR6KsCIuzp"
    "8maz2bIyMyaMH3vjtVePGzvGz5ZLvlruZ2jKDzF/Rv51dTnu/r8/vvPGy35u17vogvPOmDHto08++2LpV0eOHK2uqU3q1atPn6zT"
    "p0+99KILhg8b6v8Qi15/a+euPWoXHjCHw3HG2YHdbhUEU5/PZ579x/zz5vkaUr3x+qv/8eLLdfX1/nfSLzfntl/9/LZf/fzwkaOb"
    "tmzbtHnr/gMH6urqa2prW1pa4uMT+uVkjxs75vJLLho/7jQ/+1m5em1w78KMv4YAwoAojayfKzLXb9gU0Kddn37+pa/ObNTIEYUF"
    "Q/zcKWwWwp6uIP4xc+nqcrz+1jvBvdakNm7e8vSzz99+6y/9bJOWmnrTDdfedMO1ge587779f370iRCqMx/zns8DJQc//3LpefPk"
    "H9GXmJDwkx/d+OgTzyjc28AB+QMH5Ac3g97xsvL1GzcH8UIAMIoQlxZkZPQ+w/dcj34+d5O1YeNmP51cGEwoG5an61+vvBqWT6zw"
    "76mFz6ky6b2H8orKm376ywi8/dy85/Ppvz3vZ/qCm2+4Vp8plh998pnOzk4dDgQAahGikb3kwguio6JkV3V1OT7/cmlAe3M4HJ8v"
    "WeZr7cUXnh8VJcS7Dlr4na6PPv3sL48/rfVRxHTn3fe++e/3VNzhocNHLrvmxsoTVSru00RMej73FR/wM4lYYmLiT26+QdMCJEla"
    "vmKVnydXA4CYhGjp/NyA/+36DTW1Ad8UsviLJb5WZWVmnj59WqA7FEo4na7W1rbHn/7bbXfcbbfbtTuKyBwOx+/v/eO9f3y4vV2F"
    "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"
    "j5845R9/e1Lh35Ca/vjyBw664tob4uLiXd/26pU0ZtyEoSOKnn7szycU/98Y6GnvrvFUw85tW04bP3HajJnvvPmqx9pxE6fYbLaa"
    "6pP79+3xX4MhP5oQIyjQ925IegCAm0CNbJ++2ZIktbW11tZU63zolpaWdWtWbtuyqab6ZENDfUJC4oCBg+ZdcHHf7JxrF/z4iUce"
    "VL6r6WfMqj5Z9fH775Qc2N/W+t9/eAI9xLTTz2yor/vwvbf37d0tOZ2Fw4ouueLq1LT0m376i78+fJ//Mcgrrr4hN69/Z2fHJx+8"
    "t23Lxra2try8/AsvvXLm7Dlav33lQnmDyk2cMr1//oCOjo6P/vPvPbt2NDU1Jib26t07Y/TY8R6zXig/CYGe3suuuq5g6DCHw/HF"
    "4o82rVvb1NSY1Sf7vAsvGTFy9HnzL6mqrNixbUv37X39L+RLQPWcdc55Z8w6u6Oj/Zuvlm7dtL6utiYuPqFw6PDzL7o0f+Cgy66+"
    "7o1XXlRyYjX98Z0x6+zqk1Vvv/bykcMHOzs6hxQOu/zq65KSU+ZffPmLzz0jSdLmDes2b1jnf9aCQE+7hzUrl582fuK4iZM/fv9d"
    "jw5y6owzJElau2pFjxOnGPKjCT2CAnrvhqQHALgJ1MgmJCZKktTS3Oy96tIrr5sxc1b3JRvXre0+nBaixR/9p/u3pxrqd2zbcvhg"
    "yf/e+2C/vPx+/fO9P2Lzxd7Z+dwzj9fV1oR4CKfT+c+/P11edtz17c7tW6qqKu/6w/0ZmVnjJ05Z73u+ocysPmPGTZAk6b23X9+4"
    "bq1r4eFDJc898/jv73soJTVNi7d/xqw5F19+lSRJv//tLQrn5Q36DQYkO6efJEnr1676dvUK15JTDfWnGuoPHyrx2FLhSQj09GZm"
    "9Rk/aaokSZ98+N6Kr5a4FpaXlf7r+YU/+9XthcNGnHvBxR4dla//hWQFVE+vpKQ5886XJOmVF/7u/ky8o6Nj04Zvy44f++3/3jtu"
    "wuTPPv5AyaE1/fE1NzU989if3ZOK7Ny+JSo66sYf/WzosBFR0dFKPmQP4rR7OFhSXFFelp2TO27i5LWrvnEv758/oF9evt1u37Bu"
    "dY81GPKjCT2CAnrvKoYnAAQhcp/s1aPGxlOHDx6QJCl/wCDlr9q4/luFLYj/Q+zcvsXdJbicqCjftmWTJElFo8b42eeIUWMsFktt"
    "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"
    "qwmTpmb16XvplddeeuW17i2/+vKzs845z/8Rd27fcvDA/sEFQ8+df/G58y92Lz9RUV5TUz1i5OjQ31QQh1i76ptJU2fc9NNfdl/Y"
    "2tKy6MXnOzs9xz88vPf265l9+uTk5l165XWXXnmde/nK5UtddzuFWJsqFL7BUH6ykiQl9koaMXL05KkzvFd9+uF77ukLAjoJAZ1e"
    "SZLe+/frqenpg4cUnn/hpedfeGn3VV8u/nj71s09vgv/Aqpn6ReLY21xs84+Z9zEyeMmTvZYq/xDbeX/f4b4E/Rj84ZvZ8ycndd/"
    "wO/ve9i1pPsjatU67Q6H49vVK885/0Kr1Xr4UInHpGP+GfKjkRXcr3mP792o9AAAN+EaWUmSdmzbsm/PrgmTpw0bMTK3X15irySr"
    "1drS3HyisvxgSfGm9d96P/qrva1t4eOPnHP+hUWjTktOSWlrbT1y+ODXSz5vaKjv8R9Lp9P5j2efOmvuueMmTE7vnWHv7KypOblj"
    "6+Zvvlpy2VXXq/KOgjjEwQPFq1d8PefcC4YUDE1I7NXc1Lh3984vP/ukvq62x8M1Nzc989gjs+fMGzthUnp6746OjuOlR1cuX3bs"
    "6BHvfz51ePuyFL7BUH6ykiS99dpLI0aOKRo1pm92TmpaWpQ1qqGh/sihg2tWLu/+TISATkJAp9f1Fp57+rFJU2eMnzQlJ6dfrM3W"
    "3NR0+FDJqm+WHSo5ENTJC74ep9P56Yfvbd28YfrpZw4uGJqSmmaxSKcaGupqa/bv3b1z+1aFB1X+/2eIP0E/jh098uJzz5x51jm5"
    "/fLiExI87vdX8bR/u2blOedfKEnS2pXfBPRCQ340soL+Nff/3o1KDwBws6TljVC+dV7hdxO4lhZ7ztoNtdz5h/tycvNee+mFrZs3"
    "GF2LJsL+DYa3CPzxFQ4b8fNbf9vc1PTHe+70npg2vEXyewegvyD6TLFu9gIA0cycPUeSpA3rVkdgJxfJ7x2AKYh4aQEAiCA2Nnby"
    "tNOHF41yOBxrAryuwOwi+b0DMBEaWQDwlJSc8sc/P+7+duXyZd6X5oerSH7vAEyHRhYA5Dmdzvq62o3r1i75/BOja9FbJL93ACbC"
    "zV4AAAAwHjd7AQAAIFLQyAIAAMCUaGQBAABgSjSyAAAAMCUaWQAAAJgSjSwAAABMiUYWAAAApkQjCwAAAFOikQUAAIAp0cgCAADA"
    "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"
    "RCELAAAATfr/pwv8uNqvZDIAAAAASUVORK5CYII="
)

class PanelIntegrador(ctk.CTk):
    def __init__(self, demo: bool, puerto: str | None, segundos: int = 180):
        super().__init__()
        self.demo = demo
        self.puerto = puerto
        self.segundos = segundos
        self.inicio_partida = None
        self.resultado = None
        self.restante = segundos
        self.estado = EstadoJuego()
        self.receptor = None
        self._cerrado = False
        self._tarea = None
        self._indice_demo = 0
        self._log_lineas = []
        self.tarjetas = {}

        self.title("Operación Desactivación | Monitor de sectores")
        self.geometry("1240x800")
        self.minsize(1010, 700)
        self.configure(fg_color=COLORES["fondo"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._crear_interfaz()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        if self.demo:
            self._configurar_modo_demo()
        else:
            self._configurar_modo_real()

    def _crear_interfaz(self):
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", padx=26, pady=(20, 8))
        cabecera.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecera, text="OPERACIÓN DESACTIVACIÓN",
            font=("Arial", 29, "bold"), text_color=COLORES["texto"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            cabecera, text="Proyecto integrador · Arduino + Python · 4.º C",
            font=("Arial", 14), text_color=COLORES["secundario"],
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))

        self.etiqueta_conexion = ctk.CTkLabel(
            cabecera, text="INICIANDO", font=("Arial", 12, "bold"),
            fg_color=COLORES["card"], text_color=COLORES["amarillo"],
            corner_radius=15, width=168, height=38,
        )
        self.etiqueta_conexion.grid(row=0, column=1, rowspan=2, padx=(15, 0))

        self.etiqueta_partida = ctk.CTkLabel(
            cabecera, text="", font=("Arial", 14, "bold"),
            text_color=COLORES["cyan"], anchor="w",
        )
        self.etiqueta_partida.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(3, 4))

        principal = ctk.CTkFrame(self, fg_color="transparent")
        principal.grid(row=1, column=0, sticky="nsew", padx=22, pady=(5, 20))
        principal.grid_columnconfigure(0, weight=3)
        principal.grid_columnconfigure(1, weight=2)
        principal.grid_rowconfigure(0, weight=1)

        izquierda = ctk.CTkFrame(
            principal, fg_color=COLORES["panel"], corner_radius=19,
            border_width=1, border_color=COLORES["borde"],
        )
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        izquierda.grid_columnconfigure(0, weight=1)
        izquierda.grid_columnconfigure(1, weight=1)
        izquierda.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            izquierda, text="ESTADO DE LOS SECTORES",
            font=("Arial", 17, "bold"), text_color=COLORES["texto"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(17, 10))

        for indice, (numero, nombre, descripcion, maximo) in enumerate(DATOS_SECTORES):
            tarjeta = ctk.CTkFrame(
                izquierda, fg_color=COLORES["card"],
                corner_radius=15, border_width=1, border_color=COLORES["borde"],
                height=165,
            )
            tarjeta.grid(row=1 + indice // 2, column=indice % 2,
                         sticky="nsew", padx=(16 if indice % 2 == 0 else 6,
                                               16 if indice % 2 == 1 else 6), pady=6)
            tarjeta.grid_propagate(False)
            tarjeta.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                tarjeta, text=f"S{numero}  ·  {nombre}",
                font=("Arial", 16, "bold"), text_color=COLORES["texto"],
            ).grid(row=0, column=0, padx=15, pady=(13, 2), sticky="w")
            etiqueta_estado = ctk.CTkLabel(
                tarjeta, text="PENDIENTE", font=("Arial", 12, "bold"),
                text_color=COLORES["secundario"],
            )
            etiqueta_estado.grid(row=1, column=0, padx=15, sticky="w")
            detalle = ctk.CTkLabel(
                tarjeta, text=descripcion, font=("Arial", 12),
                text_color=COLORES["secundario"],
                wraplength=240, justify="left",
            )
            detalle.grid(row=2, column=0, sticky="w", padx=15, pady=(5, 4))
            barra = ctk.CTkProgressBar(
                tarjeta, height=9, corner_radius=8, progress_color=COLORES["cyan"],
                fg_color="#324357",
            )
            barra.grid(row=3, column=0, sticky="ew", padx=15,
                       pady=(4, 4) if numero == 3 else (8, 12))
            barra.set(0)

            if numero == 3:
                franja_rgb = ctk.CTkFrame(tarjeta, fg_color="transparent")
                franja_rgb.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 6))
                franja_rgb.grid_columnconfigure(0, weight=1)
                franja_rgb.grid_columnconfigure(1, weight=1)
                self.color_muestra = ctk.CTkLabel(
                    franja_rgb, text="MUESTRA", width=80, height=26,
                    fg_color="#344357", text_color="#FFFFFF", corner_radius=7,
                    font=("Arial", 11, "bold"),
                )
                self.color_muestra.grid(row=0, column=0, sticky="ew", padx=(0, 3))
                self.color_actual = ctk.CTkLabel(
                    franja_rgb, text="TU COLOR", width=80, height=26,
                    fg_color="#344357", text_color="#FFFFFF", corner_radius=7,
                    font=("Arial", 11, "bold"),
                )
                self.color_actual.grid(row=0, column=1, sticky="ew", padx=(3, 0))

            self.tarjetas[numero] = (etiqueta_estado, detalle, barra, descripcion, maximo)

        panel_serial = ctk.CTkFrame(izquierda, fg_color=COLORES["card"], corner_radius=13)
        panel_serial.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=16, pady=(12, 16))
        panel_serial.grid_columnconfigure(0, weight=1)
        panel_serial.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            panel_serial, text="REGISTRO SERIAL", font=("Arial", 13, "bold"),
            text_color=COLORES["texto"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))
        self.registro = ctk.CTkTextbox(
            panel_serial, font=("Consolas", 12), fg_color="#101B28",
            text_color=COLORES["cyan"], corner_radius=9, wrap="none", height=116,
        )
        self.registro.grid(row=1, column=0, sticky="nsew", padx=12, pady=(3, 12))
        self.registro.configure(state="disabled")

        derecha = ctk.CTkScrollableFrame(
            principal, fg_color=COLORES["panel"], corner_radius=19,
            border_width=1, border_color=COLORES["borde"],
        )
        derecha.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        derecha.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            derecha, text="GUÍA · CÓDIGO MORSE", font=("Arial", 18, "bold"),
            text_color=COLORES["texto"],
        ).grid(row=0, column=0, padx=16, pady=(17, 4))

        self.objetivo = ctk.CTkLabel(
            derecha, text="PALABRA OBJETIVO: —", font=("Arial", 15, "bold"),
            text_color=COLORES["amarillo"],
        )
        self.objetivo.grid(row=1, column=0, padx=14, pady=(0, 2))

        imagen_original = Image.open(BytesIO(base64.b64decode(IMAGEN_MORSE_BASE64))).convert("RGB")
        self.imagen_morse = ctk.CTkImage(
            light_image=imagen_original, dark_image=imagen_original, size=(355, 525),
        )
        ctk.CTkLabel(
            derecha, text="", image=self.imagen_morse,
        ).grid(row=2, column=0, padx=10, pady=(5, 5))

        nota = "DEMO · Los datos son simulados" if self.demo else "SERIAL · Datos de Arduino físico"
        self.nota = ctk.CTkLabel(
            derecha, text=nota, font=("Arial", 12),
            text_color=COLORES["secundario"],
        )
        self.nota.grid(row=3, column=0, padx=12, pady=(0, 10))

        if self.demo:
            ctk.CTkButton(
                cabecera, text="Repetir demo", command=self._reiniciar_demo,
                width=126, height=39, fg_color="#235F76", hover_color="#347B90",
                corner_radius=12,
            ).grid(row=0, column=2, rowspan=2, padx=(12, 0))

        self._refrescar()

    def _configurar_modo_demo(self):
        self.etiqueta_conexion.configure(
            text="DEMO · SIN ARDUINO", text_color=COLORES["amarillo"],
        )
        self._tarea = self.after(500, self._siguiente_demo)

    def _siguiente_demo(self):
        self._tarea = None
        if self._cerrado:
            return
        self._actualizar_partida()
        if self.resultado or self._indice_demo >= len(MENSAJES_DEMO):
            self._refrescar()
            return
        mensaje = MENSAJES_DEMO[self._indice_demo]
        self._indice_demo += 1
        if self.estado.procesar_mensaje(mensaje):
            self._agregar_registro(mensaje)
        self._refrescar()
        self._tarea = self.after(450, self._siguiente_demo)

    def _reiniciar_demo(self):
        if self._tarea is not None:
            self.after_cancel(self._tarea)
            self._tarea = None
        self.estado = EstadoJuego()
        self.inicio_partida = None
        self.resultado = None
        self.restante = self.segundos
        self._indice_demo = 0
        self._log_lineas.clear()
        self._mostrar_registro()
        self._refrescar()
        self._tarea = self.after(400, self._siguiente_demo)

    def _configurar_modo_real(self):
        self.receptor = ReceptorArduino(self.puerto)
        try:
            self.receptor.iniciar()
            self.estado.conexion = "CONECTADO"
            self.etiqueta_conexion.configure(
                text=f"ARDUINO · {self.puerto}", text_color=COLORES["verde"],
            )
        except RuntimeError as exc:
            self.estado.conexion = "DESCONECTADO"
            self.estado.error_conexion = str(exc)
            self.etiqueta_conexion.configure(
                text="ERROR DE CONEXIÓN", text_color=COLORES["rojo"],
            )
            self._agregar_registro(f"ERROR: {exc}")
        self._tarea = self.after(100, self._leer_arduino)

    def _leer_arduino(self):
        self._tarea = None
        if self._cerrado:
            return
        self._actualizar_partida()
        for mensaje in self.receptor.actualizar(self.estado, procesar=self.resultado is None):
            self._agregar_registro(mensaje)
        if self.estado.conexion == "DESCONECTADO":
            self.etiqueta_conexion.configure(
                text="ARDUINO DESCONECTADO", text_color=COLORES["rojo"],
            )
            if self.estado.error_conexion:
                texto_error = f"ERROR: {self.estado.error_conexion}"
                if not self._log_lineas or self._log_lineas[-1] != texto_error:
                    self._agregar_registro(texto_error)
        self._refrescar()
        self._tarea = self.after(100, self._leer_arduino)

    def _agregar_registro(self, mensaje):
        self._log_lineas.append(mensaje)
        self._log_lineas = self._log_lineas[-60:]
        self._mostrar_registro()

    def _mostrar_registro(self):
        self.registro.configure(state="normal")
        self.registro.delete("1.0", "end")
        self.registro.insert("end", "\n".join(self._log_lineas))
        self.registro.see("end")
        self.registro.configure(state="disabled")

    def _actualizar_partida(self):
        # El tiempo se mide desde el primer mensaje reconocido de Arduino.
        # No modifica el circuito: el resultado de la partida se gestiona en Python.
        if self.resultado is not None:
            return
        if self.inicio_partida is None and self.estado.ultimo_mensaje:
            self.inicio_partida = time.monotonic()
        if self.inicio_partida is not None:
            self.restante = max(0, math.ceil(self.segundos - (time.monotonic() - self.inicio_partida)))
            if self.restante == 0:
                self.resultado = "MISIÓN FALLIDA"
            elif all(getattr(self.estado, f"sector{i}").completado for i in range(1, 5)):
                self.resultado = "MISIÓN COMPLETADA"

    def _refrescar(self):
        self._actualizar_partida()
        minutos, segundos = divmod(self.restante, 60)
        completos = sum(getattr(self.estado, f"sector{i}").completado for i in range(1, 5))
        situacion = self.resultado or ("EN CURSO" if self.inicio_partida is not None else "ESPERANDO DATOS")
        color = COLORES["rojo"] if self.resultado == "MISIÓN FALLIDA" else COLORES["verde"] if self.resultado else COLORES["cyan"]
        self.etiqueta_partida.configure(text=f"TIEMPO {minutos:02d}:{segundos:02d}    ·    {completos}/4 SECTORES    ·    {situacion}", text_color=color)
        for numero, _, _, _ in DATOS_SECTORES:
            sector = getattr(self.estado, f"sector{numero}")
            etiqueta_estado, detalle, barra, descripcion, maximo = self.tarjetas[numero]

            if numero == 2 and not self.estado.sector1.completado:
                color, avance, nombre_estado = COLORES["secundario"], 0.0, "BLOQUEADO"
            elif sector.completado:
                color, avance, nombre_estado = COLORES["verde"], 1.0, "COMPLETADO"
            elif sector.estado == "ERROR / REINTENTO":
                color, avance, nombre_estado = COLORES["rojo"], 0.0, "ERROR · REINTENTO"
            elif sector.estado == "EN CURSO" or sector.rgb is not None or sector.objetivo:
                color, nombre_estado = COLORES["cyan"], "EN CURSO"
                if numero == 3:
                    avance = (sum(sector.rgb) / 3) if sector.rgb else 0.0
                elif numero == 4:
                    total_simbolos = sum(len(MORSE.get(letra, "")) for letra in sector.objetivo)
                    avance = sector.paso / total_simbolos if total_simbolos else 0.0
                else:
                    avance = sector.paso / maximo if maximo else 0.0
            else:
                color, avance, nombre_estado = COLORES["secundario"], 0.0, "PENDIENTE"

            texto_detalle = descripcion
            if numero == 2 and not self.estado.sector1.completado:
                texto_detalle = "Completá Memoria para habilitarlo"
            elif numero in (1, 2) and sector.paso:
                texto_detalle = f"Paso {sector.paso} de {maximo}"
            elif numero == 3 and sector.rgb:
                r, g, b = sector.rgb
                texto_detalle = f"Coincidencias RGB: {r} / {g} / {b}"
            elif numero == 4 and sector.objetivo:
                texto_detalle = f"Objetivo: {sector.objetivo} · símbolos {sector.paso}"

            etiqueta_estado.configure(text=nombre_estado, text_color=color)
            detalle.configure(text=texto_detalle)
            barra.configure(progress_color=color)
            barra.set(max(0.0, min(1.0, avance)))

        # El color de referencia existe solo en esta interfaz.
        rgb = self.estado.sector3
        try:
            componentes = tuple(int(x) for x in rgb.objetivo.split(","))
            objetivo = componentes if len(componentes) == 3 and all(0 <= x <= 255 for x in componentes) else None
        except ValueError:
            objetivo = None

        for etiqueta, datos, titulo in (
            (self.color_muestra, objetivo, "MUESTRA"),
            (self.color_actual, rgb.color_jugador, "TU COLOR"),
        ):
            if datos is None:
                etiqueta.configure(text=titulo, fg_color="#344357", text_color="#FFFFFF")
                continue
            rojo, verde, azul = datos
            color = f"#{rojo:02X}{verde:02X}{azul:02X}"
            brillo = (rojo * 299 + verde * 587 + azul * 114) // 1000
            etiqueta.configure(
                text=titulo, fg_color=color,
                text_color="#101820" if brillo >= 150 else "#FFFFFF",
            )

        palabra = self.estado.sector4.objetivo or "—"
        self.objetivo.configure(text=f"PALABRA OBJETIVO: {palabra}")

    def _cerrar(self):
        self._cerrado = True
        if self._tarea is not None:
            self.after_cancel(self._tarea)
            self._tarea = None
        if self.receptor is not None:
            self.receptor.cerrar()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description="Monitor Arduino en CustomTkinter")
    modos = parser.add_mutually_exclusive_group(required=True)
    modos.add_argument("--demo", action="store_true", help="Demostración sin placa física")
    modos.add_argument("--puerto", help="Puerto serie: COM3, /dev/ttyACM0, etc.")
    parser.add_argument("--segundos", type=int, default=180, help="Duración de la partida (180 por defecto)")
    args = parser.parse_args()
    if args.segundos <= 0:
        parser.error("--segundos debe ser mayor que cero")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    PanelIntegrador(demo=args.demo, puerto=args.puerto, segundos=args.segundos).mainloop()


if __name__ == "__main__":
    main()
