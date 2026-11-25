import threading
import time

import requests


class ServicioNoDisponible(Exception):
    pass


class CircuitoAbierto(ServicioNoDisponible):
    pass


class Resiliencia:
    def __init__(self, intentos=3, espera=0.2, fallas_para_abrir=3, segundos_abierto=5.0, reloj=time.monotonic, dormir=time.sleep):
        self.intentos = max(1, intentos)
        self.espera = espera
        self.fallas_para_abrir = max(1, fallas_para_abrir)
        self.segundos_abierto = segundos_abierto
        self.reloj = reloj
        self.dormir = dormir
        self._fallas = {}
        self._abierto_hasta = {}
        self._cerrojo = threading.Lock()

    def estado(self, nombre):
        with self._cerrojo:
            hasta = self._abierto_hasta.get(nombre)
            return "abierto" if hasta is not None and self.reloj() < hasta else "cerrado"

    def _registrar_exito(self, nombre):
        with self._cerrojo:
            self._fallas[nombre] = 0
            self._abierto_hasta.pop(nombre, None)

    def _registrar_falla(self, nombre):
        with self._cerrojo:
            self._fallas[nombre] = self._fallas.get(nombre, 0) + 1
            if self._fallas[nombre] >= self.fallas_para_abrir:
                self._abierto_hasta[nombre] = self.reloj() + self.segundos_abierto
                self._fallas[nombre] = 0
                return True
        return False

    def llamar(self, nombre, enviar, idempotente=True, estados_fallidos=(502, 503, 504)):
        if self.estado(nombre) == "abierto":
            raise CircuitoAbierto(f"El servicio {nombre} está en pausa por fallas seguidas")
        ultimo = None
        for intento in range(self.intentos):
            reintentable = True
            try:
                respuesta = enviar()
            except requests.ConnectionError as exc:
                ultimo = exc
            except requests.RequestException as exc:
                ultimo = exc
                reintentable = idempotente
            else:
                if respuesta.status_code not in estados_fallidos:
                    self._registrar_exito(nombre)
                    return respuesta
                ultimo = ServicioNoDisponible(f"El servicio {nombre} respondió {respuesta.status_code}")
                reintentable = idempotente
            abierto = self._registrar_falla(nombre)
            if abierto or not reintentable or intento == self.intentos - 1:
                break
            self.dormir(self.espera * (2**intento))
        raise ServicioNoDisponible(f"El servicio {nombre} no responde: {ultimo}")
