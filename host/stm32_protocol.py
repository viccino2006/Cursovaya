"""
stm32_protocol — клиент USB CDC для криптомодуля STM32F103C8T6.

Реализует двоичный протокол, описанный в firmware/Core/Inc/usb_protocol.h:

    запрос: [CMD : 1][LEN : 2 LE][DATA : LEN]
    ответ:  [STATUS : 1][LEN : 2 LE][DATA : LEN]

Поддерживаемые операции:
    ping            -> b'BIGN1'
    sign(hash)      -> sig (48 байт)
    verify(h,s,pk)  -> True/False
    get_pubkey()    -> 64 байта
    gen_keypair()   -> 64 байта (новый публичный ключ)
    encrypt(iv, key, plain)  -> cipher
    decrypt(iv, key, cipher) -> plain
    hash(data)      -> 32 байта (belt-hash на устройстве)
"""
from __future__ import annotations

import struct
from typing import Optional

import serial
import serial.tools.list_ports

# ---- константы протокола ------------------------------------------------------
CMD_PING        = 0x00
CMD_SIGN        = 0x01
CMD_VERIFY      = 0x02
CMD_GET_PUBKEY  = 0x03
CMD_GEN_KEYPAIR = 0x04
CMD_ENCRYPT     = 0x05
CMD_DECRYPT     = 0x06
CMD_HASH        = 0x07

STATUS_OK  = 0xAA
STATUS_ERR = 0xFF

HASH_LEN    = 32
SIG_LEN     = 48
PUBKEY_LEN  = 64
PRIVKEY_LEN = 32
BLOCK_LEN   = 16
KEY_LEN     = 32

ERR_NAMES = {
    0x01: "BAD_LEN",
    0x02: "BAD_CMD",
    0x03: "INTERNAL",
    0x04: "NO_KEY",
    0x05: "BAD_SIG",
    0x06: "BAD_KEY",
    0x07: "RNG",
    0x08: "FLASH",
}


class DeviceError(RuntimeError):
    """Устройство вернуло STATUS_ERR (содержит расшифровку кода ошибки)."""


class STM32Crypto:
    """Высокоуровневый клиент криптомодуля."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 10.0) -> None:
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser: Optional[serial.Serial] = None

    # ------------------------------------------------------------------------
    # Управление соединением
    # ------------------------------------------------------------------------
    def connect(self) -> None:
        self._ser = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout,
            write_timeout=5.0,
        )

    def disconnect(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    @property
    def connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ------------------------------------------------------------------------
    # Низкоуровневая отправка кадра
    # ------------------------------------------------------------------------
    def _send(self, cmd: int, data: bytes = b"") -> bytes:
        if not self.connected:
            raise ConnectionError("Устройство не подключено")
        if len(data) > 0xFFFF:
            raise ValueError("data exceeds 65535 bytes")
        pkt = struct.pack("<BH", cmd, len(data)) + data
        self._ser.reset_input_buffer()
        self._ser.write(pkt)

        header = self._ser.read(3)
        if len(header) < 3:
            raise TimeoutError("Таймаут ожидания заголовка ответа")
        status, length = struct.unpack("<BH", header)
        body = self._ser.read(length) if length > 0 else b""
        if len(body) != length:
            raise TimeoutError(f"Получено {len(body)} байт из {length}")
        if status != STATUS_OK:
            err = body[0] if body else 0
            raise DeviceError(f"STATUS_ERR (code 0x{err:02X} = {ERR_NAMES.get(err, '?')})")
        return body

    # ------------------------------------------------------------------------
    # Высокоуровневые операции
    # ------------------------------------------------------------------------
    def ping(self) -> bytes:
        return self._send(CMD_PING)

    def get_pubkey(self) -> bytes:
        pk = self._send(CMD_GET_PUBKEY)
        if len(pk) != PUBKEY_LEN:
            raise RuntimeError(f"pubkey: expected {PUBKEY_LEN} bytes, got {len(pk)}")
        return pk

    def gen_keypair(self) -> bytes:
        """Сгенерировать новую пару ключей. Возвращает публичный ключ (64 байта)."""
        pk = self._send(CMD_GEN_KEYPAIR)
        if len(pk) != PUBKEY_LEN:
            raise RuntimeError(f"new pubkey: expected {PUBKEY_LEN} bytes, got {len(pk)}")
        return pk

    def sign(self, hash_bytes: bytes) -> bytes:
        if len(hash_bytes) != HASH_LEN:
            raise ValueError(f"hash must be {HASH_LEN} bytes")
        sig = self._send(CMD_SIGN, hash_bytes)
        if len(sig) != SIG_LEN:
            raise RuntimeError(f"sig: expected {SIG_LEN} bytes, got {len(sig)}")
        return sig

    def verify(self, hash_bytes: bytes, sig: bytes, pubkey: bytes) -> bool:
        if len(hash_bytes) != HASH_LEN:
            raise ValueError(f"hash must be {HASH_LEN} bytes")
        if len(sig) != SIG_LEN:
            raise ValueError(f"sig must be {SIG_LEN} bytes")
        if len(pubkey) != PUBKEY_LEN:
            raise ValueError(f"pubkey must be {PUBKEY_LEN} bytes")
        try:
            self._send(CMD_VERIFY, hash_bytes + sig + pubkey)
            return True
        except DeviceError as e:
            if "BAD_SIG" in str(e):
                return False
            raise

    def encrypt(self, iv: bytes, key: bytes, plain: bytes) -> bytes:
        if len(iv) != BLOCK_LEN: raise ValueError("iv must be 16 bytes")
        if len(key) != KEY_LEN: raise ValueError("key must be 32 bytes")
        if len(plain) == 0 or len(plain) % BLOCK_LEN != 0:
            raise ValueError("plain must be non-empty and multiple of 16 bytes")
        return self._send(CMD_ENCRYPT, iv + key + plain)

    def decrypt(self, iv: bytes, key: bytes, cipher: bytes) -> bytes:
        if len(iv) != BLOCK_LEN: raise ValueError("iv must be 16 bytes")
        if len(key) != KEY_LEN: raise ValueError("key must be 32 bytes")
        if len(cipher) == 0 or len(cipher) % BLOCK_LEN != 0:
            raise ValueError("cipher must be non-empty and multiple of 16 bytes")
        return self._send(CMD_DECRYPT, iv + key + cipher)

    def hash(self, data: bytes) -> bytes:
        h = self._send(CMD_HASH, data)
        if len(h) != HASH_LEN:
            raise RuntimeError(f"hash: expected {HASH_LEN} bytes, got {len(h)}")
        return h


# -----------------------------------------------------------------------------
# Вспомогательные функции
# -----------------------------------------------------------------------------
def find_stm32_ports() -> list:
    """Возвращает список COM-портов, в описании которых упоминается STM32."""
    ports = []
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "") + " " + (p.manufacturer or "")
        if "STM32" in desc or "STMicroelectronics" in desc or "Virtual" in desc:
            ports.append(p.device)
    return ports
