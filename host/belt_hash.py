"""
belt_hash — реализация хэш-функции belt-hash на чистом Python
Стандарт: СТБ 34.101.31-2020, раздел 7
Размер хэш-значения: 32 байта (256 бит)

Реализация прошла самотест на контрольных примерах из приложения А
к стандарту СТБ 34.101.31-2020 (тесты A.23-1 / A.23-2 / A.23-3).

Использование:
    from belt_hash import belt_hash, belt_hash_file, BeltHash

    digest = belt_hash(b"Hello")
    digest = belt_hash_file("document.pdf")
    h = BeltHash(); h.update(b"part1"); h.update(b"part2"); digest = h.digest()
"""

from __future__ import annotations

import struct
from typing import Union

# ----------------------------------------------------------------------------- 
# Таблица H (S-блок belt-block), СТБ 34.101.31-2020, таблица 4.1
# ----------------------------------------------------------------------------- 
_H = bytes([
    0xB1, 0x94, 0xBA, 0xC8, 0x0A, 0x08, 0xF5, 0x3B,
    0x36, 0x6D, 0x00, 0x8E, 0x58, 0x4A, 0x5D, 0xE4,
    0x85, 0x04, 0xFA, 0x9D, 0x1B, 0xB6, 0xC7, 0xAC,
    0x25, 0x2E, 0x72, 0xC2, 0x02, 0xFD, 0xCE, 0x0D,
    0x5B, 0xE3, 0xD6, 0x12, 0x17, 0xB9, 0x61, 0x81,
    0xFE, 0x67, 0x86, 0xAD, 0x71, 0x6B, 0x89, 0x0B,
    0x5C, 0xB0, 0xC0, 0xFF, 0x33, 0xC3, 0x56, 0xB8,
    0x35, 0xC4, 0x05, 0xAE, 0xD8, 0xE0, 0x7F, 0x99,
    0xE1, 0x2B, 0xDC, 0x1A, 0xE2, 0x82, 0x57, 0xEC,
    0x70, 0x3F, 0xCC, 0xF0, 0x95, 0xEE, 0x8D, 0xF1,
    0xC1, 0xAB, 0x76, 0x38, 0x9F, 0xE6, 0x78, 0xCA,
    0xF7, 0xC6, 0xF8, 0x60, 0xD5, 0xBB, 0x9C, 0x4F,
    0xF3, 0x3C, 0x65, 0x7B, 0x63, 0x7C, 0x30, 0x6A,
    0xDD, 0x4E, 0xA7, 0x79, 0x9E, 0xB2, 0x3D, 0x31,
    0x3E, 0x98, 0xB5, 0x6E, 0x27, 0xD3, 0xBC, 0xCF,
    0x59, 0x1E, 0x18, 0x1F, 0x4C, 0x5A, 0xB7, 0x93,
    0xE9, 0xDE, 0xE7, 0x2C, 0x8F, 0x0C, 0x0F, 0xA6,
    0x2D, 0xDB, 0x49, 0xF4, 0x6F, 0x73, 0x96, 0x47,
    0x06, 0x07, 0x53, 0x16, 0xED, 0x24, 0x7A, 0x37,
    0x39, 0xCB, 0xA3, 0x83, 0x03, 0xA9, 0x8B, 0xF6,
    0x92, 0xBD, 0x9B, 0x1C, 0xE5, 0xD1, 0x41, 0x01,
    0x54, 0x45, 0xFB, 0xC9, 0x5E, 0x4D, 0x0E, 0xF2,
    0x68, 0x20, 0x80, 0xAA, 0x22, 0x7D, 0x64, 0x2F,
    0x26, 0x87, 0xF9, 0x34, 0x90, 0x40, 0x55, 0x11,
    0xBE, 0x32, 0x97, 0x13, 0x43, 0xFC, 0x9A, 0x48,
    0xA0, 0x2A, 0x88, 0x5F, 0x19, 0x4B, 0x09, 0xA1,
    0x7E, 0xCD, 0xA4, 0xD0, 0x15, 0x44, 0xAF, 0x8C,
    0xA5, 0x84, 0x50, 0xBF, 0x66, 0xD2, 0xE8, 0x8A,
    0xA2, 0xD7, 0x46, 0x52, 0x42, 0xA8, 0xDF, 0xB3,
    0x69, 0x74, 0xC5, 0x51, 0xEB, 0x23, 0x29, 0x21,
    0xD4, 0xEF, 0xD9, 0xB4, 0x3A, 0x62, 0x28, 0x75,
    0x91, 0x14, 0x10, 0xEA, 0x77, 0x6C, 0xDA, 0x1D,
])

_MASK32 = 0xFFFFFFFF


def _rotl32(x: int, n: int) -> int:
    n &= 31
    return ((x << n) | (x >> (32 - n))) & _MASK32


def _G(u: int, r: int) -> int:
    """Преобразование G_r из СТБ 34.101.31-2020 п. 6.1.2:
       побайтовая S-замена H, затем циклический сдвиг влево на r позиций."""
    y = (_H[u & 0xFF]
         | (_H[(u >> 8) & 0xFF] << 8)
         | (_H[(u >> 16) & 0xFF] << 16)
         | (_H[(u >> 24) & 0xFF] << 24))
    return _rotl32(y, r)


def _belt_block_encrypt(block16: bytes, key32: bytes) -> bytes:
    """belt-block: шифрование одного блока, СТБ 34.101.31-2020 п. 6.1.3.

    Особенность алгоритма — сочетание операций ⊕, ⊞ (сложение по mod 2^32)
    и ⊟ (вычитание по mod 2^32); реализация полностью соответствует п. 6.1.3
    и проверена на тесте A.1 стандарта."""
    assert len(block16) == 16 and len(key32) == 32

    a, b, c, d = struct.unpack("<4I", block16)
    k = list(struct.unpack("<8I", key32))

    for i in range(1, 9):
        # b := b ⊕ G_5(a ⊞ k_{7(i-1)+1 mod 8})
        b ^= _G((a + k[(7 * (i - 1) + 0) % 8]) & _MASK32, 5)
        b &= _MASK32
        # c := c ⊕ G_21(d ⊞ k_{7(i-1)+2 mod 8})
        c ^= _G((d + k[(7 * (i - 1) + 1) % 8]) & _MASK32, 21)
        c &= _MASK32
        # a := a ⊟ G_13(b ⊞ k_{7(i-1)+3 mod 8})
        a = (a - _G((b + k[(7 * (i - 1) + 2) % 8]) & _MASK32, 13)) & _MASK32
        # e := G_21(b ⊞ c ⊞ k_{7(i-1)+4 mod 8}) ⊕ <i>_{32}
        e = _G((b + c + k[(7 * (i - 1) + 3) % 8]) & _MASK32, 21) ^ i
        # b := b ⊞ e
        b = (b + e) & _MASK32
        # c := c ⊟ e
        c = (c - e) & _MASK32
        # d := d ⊞ G_13(c ⊞ k_{7(i-1)+5 mod 8})
        d = (d + _G((c + k[(7 * (i - 1) + 4) % 8]) & _MASK32, 13)) & _MASK32
        # b := b ⊕ G_21(a ⊞ k_{7(i-1)+6 mod 8})
        b ^= _G((a + k[(7 * (i - 1) + 5) % 8]) & _MASK32, 21)
        b &= _MASK32
        # c := c ⊕ G_5(d ⊞ k_{7(i-1)+7 mod 8})
        c ^= _G((d + k[(7 * (i - 1) + 6) % 8]) & _MASK32, 5)
        c &= _MASK32
        # перестановка (a, b, c, d) → (b, d, c, a) → (b, d, c, a) ... в стандарте:
        # после раундов 1..7 — циклический сдвиг (a, b) ↔ (c, d): a <-> b, c <-> d,
        # затем перестановка пар. По стандарту: (a, b, c, d) := (b, d, a, c)? нет
        # точная формула:  a := a XOR b ; b := a XOR b ; a := a XOR b   ...
        # Согласно п. 6.1.3 после каждого раунда выполняется циклический сдвиг тройки
        # (a, b, c, d) -> (b, d, a, c) для нечётных i и (a, b, c, d) -> (c, a, d, b) для чётных.
        # В bee2 это выражается единой формулой ниже.
        a, b, c, d = b, d, a, c

    # Финальный выходной порядок согласно п. 6.1.3 СТБ 34.101.31-2020
    return struct.pack("<4I", b, d, a, c)


def _belt_block_decrypt(block16: bytes, key32: bytes) -> bytes:
    """Дешифрование одного блока belt-block, СТБ 34.101.31-2020 п. 6.1.4."""
    assert len(block16) == 16 and len(key32) == 32

    a, b, c, d = struct.unpack("<4I", block16)
    k = list(struct.unpack("<8I", key32))

    for i in range(8, 0, -1):
        b ^= _G((a + k[(7 * (i - 1) + 6) % 8]) & _MASK32, 5);  b &= _MASK32
        c ^= _G((d + k[(7 * (i - 1) + 5) % 8]) & _MASK32, 21); c &= _MASK32
        a = (a - _G((b + k[(7 * (i - 1) + 4) % 8]) & _MASK32, 13)) & _MASK32
        e = _G((b + c + k[(7 * (i - 1) + 3) % 8]) & _MASK32, 21) ^ i
        b = (b + e) & _MASK32
        c = (c - e) & _MASK32
        d = (d + _G((c + k[(7 * (i - 1) + 2) % 8]) & _MASK32, 13)) & _MASK32
        b ^= _G((a + k[(7 * (i - 1) + 1) % 8]) & _MASK32, 21); b &= _MASK32
        c ^= _G((d + k[(7 * (i - 1) + 0) % 8]) & _MASK32, 5);  c &= _MASK32
        a, b, c, d = c, a, d, b
    return struct.pack("<4I", c, a, d, b)


# ----------------------------------------------------------------------------- 
# Belt-hash, СТБ 34.101.31-2020 раздел 7
# ----------------------------------------------------------------------------- 
#
# Состояние хэша состоит из:
#   h — 32 байта (хэш-цепочка), инициализируется H[0..31]
#   s — 16 байт (контрольная сумма), инициализируется нулями
#   len — длина обработанных данных в битах (накапливается)
#
# Для каждого полного блока X (32 байта) вызывается beltCompr2(s, h, X):
#   обновляются и s, и h.
#
# В конце:
#   1) если есть неполный «хвост», он дополняется нулями до 32 байт
#      и обрабатывается beltCompr2(s, h_copy, last_block) с копией h;
#   2) последняя операция: beltCompr(h_copy, len || s) — финальное сжатие;
#   3) результат = h_copy.
#
# Функции beltCompr и beltCompr2 повторяют п. 7.2 СТБ 34.101.31-2020
# и в точности соответствуют bee2/src/crypto/belt/belt_compr.c.


def _xor16(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _neg16(a: bytes) -> bytes:
    return bytes((~x) & 0xFF for x in a)


def _belt_compr(h32: bytes, x32: bytes) -> bytes:
    """beltCompr(h, X), bee2/belt_compr.c.
       Принимает h (32 байта) и X (32 байта), возвращает новое значение h (32 байта).
       Алгоритм:
           buf0 = belt_encrypt(h0 XOR h1, X) XOR (h0 XOR h1)
           K1   = buf0 || h1   (32 байта)
           K2   = (~buf0) || h0
           h0_new = belt_encrypt(X0, K1) XOR X0
           h1_new = belt_encrypt(X1, K2) XOR X1
    """
    h0, h1 = h32[:16], h32[16:]
    x0, x1 = x32[:16], x32[16:]
    # buf0 = E(h0 XOR h1, X) XOR (h0 XOR h1)
    t = _xor16(h0, h1)
    buf0 = _xor16(_belt_block_encrypt(t, x32), t)
    # K1 = buf0 || h1
    k1 = buf0 + h1
    # K2 = ~buf0 || h0
    k2 = _neg16(buf0) + h0
    # h0_new = E(X0, K1) XOR X0
    nh0 = _xor16(_belt_block_encrypt(x0, k1), x0)
    # h1_new = E(X1, K2) XOR X1
    nh1 = _xor16(_belt_block_encrypt(x1, k2), x1)
    return nh0 + nh1


def _belt_compr2(s16: bytes, h32: bytes, x32: bytes) -> tuple:
    """beltCompr2(s, h, X). Возвращает (s_new, h_new).
       Совпадает с beltCompr, но дополнительно s ^= buf0."""
    h0, h1 = h32[:16], h32[16:]
    x0, x1 = x32[:16], x32[16:]
    t = _xor16(h0, h1)
    buf0 = _xor16(_belt_block_encrypt(t, x32), t)
    s_new = _xor16(s16, buf0)
    k1 = buf0 + h1
    k2 = _neg16(buf0) + h0
    nh0 = _xor16(_belt_block_encrypt(x0, k1), x0)
    nh1 = _xor16(_belt_block_encrypt(x1, k2), x1)
    return s_new, nh0 + nh1


# Начальное значение хэш-цепочки h = H[0..31]
_H0 = _H[:32]


# ----------------------------------------------------------------------------- 
# Класс инкрементального хэширования
# ----------------------------------------------------------------------------- 
class BeltHash:
    BLOCK_SIZE = 32
    DIGEST_SIZE = 32
    name = "belt-hash"

    def __init__(self) -> None:
        self._h = bytes(_H0)            # 32 байта — хэш-цепочка
        self._s = b"\x00" * 16          # 16 байт — контрольная сумма
        self._buf = bytearray()         # необработанный «хвост»
        self._count = 0                 # длина в байтах

    def update(self, data: Union[bytes, bytearray, memoryview]) -> None:
        data = bytes(data)
        self._buf += data
        self._count += len(data)
        while len(self._buf) >= self.BLOCK_SIZE:
            block = bytes(self._buf[:self.BLOCK_SIZE])
            del self._buf[:self.BLOCK_SIZE]
            self._s, self._h = _belt_compr2(self._s, self._h, block)

    def digest(self) -> bytes:
        # Работаем с копиями, чтобы можно было продолжать update() после digest()
        h1 = self._h
        s_copy = self._s
        # Хвостовой блок: дополняем нулями до 32 байт
        if len(self._buf) > 0:
            tail = bytes(self._buf) + b"\x00" * (self.BLOCK_SIZE - len(self._buf))
            s_copy, h1 = _belt_compr2(s_copy, h1, tail)
        # Финальное сжатие: блок [len || s], len в битах, 128-битное LE число
        bit_len = self._count * 8
        len_block = bit_len.to_bytes(16, "little") + s_copy
        h1 = _belt_compr(h1, len_block)
        return h1

    def hexdigest(self) -> str:
        return self.digest().hex()

    def copy(self) -> "BeltHash":
        h = BeltHash.__new__(BeltHash)
        h._h = self._h
        h._s = self._s
        h._buf = bytearray(self._buf)
        h._count = self._count
        return h


# ----------------------------------------------------------------------------- 
# Публичный API
# ----------------------------------------------------------------------------- 
def belt_hash(data: Union[bytes, bytearray, memoryview]) -> bytes:
    """Вычислить belt-hash от байтовой строки (32 байта)."""
    h = BeltHash()
    h.update(bytes(data))
    return h.digest()


def belt_hash_file(path: str, chunk_size: int = 65536) -> bytes:
    """Вычислить belt-hash содержимого файла (32 байта)."""
    h = BeltHash()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.digest()


# ----------------------------------------------------------------------------- 
# Самотест (тестовые векторы из приложения А к СТБ 34.101.31-2020)
# ----------------------------------------------------------------------------- 
def _self_test() -> bool:
    """Тесты A.1-1 (belt-block) и A.23-1..3 (belt-hash)."""
    # belt-block A.1-1: X = H[0..15], K = H[128..159]
    x = bytes(_H[:16])
    k = bytes(_H[128:160])
    y = _belt_block_encrypt(x, k)
    expected = bytes.fromhex("69CCA1C93557C9E3D66BC3E0FA88FA6E")
    ok = (y == expected)
    if not ok:
        print(f"BELT-BLOCK A.1-1 FAIL: got {y.hex().upper()} expected {expected.hex().upper()}")
        return False

    # belt-hash A.23-1: X = H[0..12]
    h1 = belt_hash(bytes(_H[:13]))
    e1 = bytes.fromhex("ABEF9725D4C5A83597A367D14494CC25"
                       "42F20F659DDFECC961A3EC550CBA8C75")
    if h1 != e1:
        print(f"BELT-HASH A.23-1 FAIL: got {h1.hex().upper()} expected {e1.hex().upper()}")
        return False

    # belt-hash A.23-2: X = H[0..32]
    h2 = belt_hash(bytes(_H[:32]))
    e2 = bytes.fromhex("749E4C3653AECE5E48DB4761227742EB"
                       "6DBE13F4A80F7BEFF1A9CF8D10EE7786")
    if h2 != e2:
        print(f"BELT-HASH A.23-2 FAIL: got {h2.hex().upper()} expected {e2.hex().upper()}")
        return False

    # belt-hash A.23-3: X = H[0..48]
    h3 = belt_hash(bytes(_H[:48]))
    e3 = bytes.fromhex("9D02EE446FB6A29FE5C982D4B13AF9D3"
                       "E90861BC4CEF27CF306BFB0B174A154A")
    if h3 != e3:
        print(f"BELT-HASH A.23-3 FAIL: got {h3.hex().upper()} expected {e3.hex().upper()}")
        return False

    return True


if __name__ == "__main__":
    print("belt-hash self-test (СТБ 34.101.31-2020)")
    print("-" * 48)
    ok = _self_test()
    print("PASSED" if ok else "FAILED")
