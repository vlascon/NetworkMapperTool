"""Cifrado portable por contraseña para archivos de levantamiento.

Diseño (decisión del usuario 9-nov-2026: abrir desde cualquier equipo con
el pendrive, protegido por contraseña):

- KDF: scrypt (memory-hard) con sal aleatoria por archivo. Los parámetros
  viajan en el encabezado, así cualquier equipo compatible deriva la clave
  sin estado previo: nada queda atado a un PC.
- Cifrado: AES-256-GCM (AEAD). Detecta contraseña incorrecta y cualquier
  alteración del contenido con la misma excepción.
- La contraseña se pide al operador en cada sesión y NUNCA se guarda, ni
  en el archivo ni en el pendrive ni en el código. Sin secretos embebidos.
- Si se olvida la contraseña NO hay recuperación: no existe llave maestra.

Límites honestos (declarados al usuario):
- Protege los archivos ante pérdida del pendrive. NO protege contra un
  equipo que capture la contraseña al teclearla o los datos ya abiertos
  en memoria/pantalla.
- AEAD detecta alteración de ESTE archivo; no detecta que borren el
  archivo ni que lo reemplacen por una copia cifrada anterior (rollback).

Formato del contenedor (todo big-endian):
    magic 8B "NMTENC1\0" | sal 16B | n u32 | r u32 | p u32 | nonce 12B |
    ciphertext+tag (GCM)
"""
import os
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"NMTENC1\0"
# Parámetros scrypt por defecto: ~0.1-0.3 s por derivación en un PC modesto.
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
_LEN = 32  # clave AES-256

_HEADER = struct.Struct(">8s16sIII12s")

# Presupuesto acotado para parámetros LEÍDOS de un archivo (importar o
# abrir): sin este tope, un archivo hostil podría declarar un n enorme y
# agotar memoria/CPU al derivar la clave. Memoria scrypt ~ 128*n*r*p.
# Nuestro default usa 128*2^15*8*1 = 32 MiB; admitimos hasta el doble
# (64 MiB) para futuras subidas modestas, y rangos cerrados alrededor del
# default: cualquier archivo que escriba esta herramienta queda dentro.
_N_MIN, _N_MAX = 2 ** 10, 2 ** 17
_R_MIN, _R_MAX = 1, 16
_P_MIN, _P_MAX = 1, 4
_MEMORIA_MAX = 64 * 1024 * 1024  # 64 MiB


class ErrorCifrado(Exception):
    """Contraseña incorrecta, contenedor alterado o formato inválido."""


def _validar_parametros(n, r, p):
    """Rechaza parámetros fuera del presupuesto ANTES de derivar la clave."""
    if not (_N_MIN <= n <= _N_MAX) or (n & (n - 1)) != 0:
        raise ErrorCifrado(f"parámetro scrypt n={n} fuera del rango admitido")
    if not (_R_MIN <= r <= _R_MAX):
        raise ErrorCifrado(f"parámetro scrypt r={r} fuera del rango admitido")
    if not (_P_MIN <= p <= _P_MAX):
        raise ErrorCifrado(f"parámetro scrypt p={p} fuera del rango admitido")
    if 128 * n * r * p > _MEMORIA_MAX:
        raise ErrorCifrado("parámetros scrypt exceden el presupuesto de memoria admitido")


def esta_cifrado(data):
    """True si los bytes tienen el formato de contenedor cifrado."""
    return isinstance(data, (bytes, bytearray)) and data[:8] == MAGIC


def _derivar(contrasena, sal, n, r, p):
    if isinstance(contrasena, str):
        contrasena = contrasena.encode("utf-8")
    if not contrasena:
        raise ErrorCifrado("la contraseña no puede estar vacía")
    kdf = Scrypt(salt=sal, length=_LEN, n=n, r=r, p=p)
    return kdf.derive(contrasena)


def cifrar_bytes(texto_claro, contrasena):
    """Cifra bytes con contraseña. Devuelve el contenedor completo."""
    sal = os.urandom(16)
    nonce = os.urandom(12)
    clave = _derivar(contrasena, sal, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    cifrado = AESGCM(clave).encrypt(nonce, texto_claro, MAGIC)
    return _HEADER.pack(MAGIC, sal, SCRYPT_N, SCRYPT_R, SCRYPT_P, nonce) + cifrado


def descifrar_bytes(contenedor, contrasena):
    """Descifra un contenedor. ErrorCifrado ante clave mala o alteración."""
    if not esta_cifrado(contenedor):
        raise ErrorCifrado("no es un archivo cifrado de esta herramienta")
    if len(contenedor) < _HEADER.size + 16:  # header + tag mínimo de GCM
        raise ErrorCifrado("archivo cifrado truncado")
    magic, sal, n, r, p, nonce = _HEADER.unpack(contenedor[: _HEADER.size])
    _validar_parametros(n, r, p)
    try:
        clave = _derivar(contrasena, sal, n, r, p)
        return AESGCM(clave).decrypt(nonce, contenedor[_HEADER.size :], MAGIC)
    except InvalidTag:
        raise ErrorCifrado("contraseña incorrecta o archivo alterado")
    except Exception as exc:
        if isinstance(exc, ErrorCifrado):
            raise
        raise ErrorCifrado(f"no se pudo descifrar: {exc}")
