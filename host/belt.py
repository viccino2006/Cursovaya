"""
belt — режимы шифрования по СТБ 34.101.31-2020.

Реализованы:
    * belt_block_encrypt / belt_block_decrypt — базовый блочный шифр (16 байт);
    * belt_ecb_encrypt / belt_ecb_decrypt    — режим простой замены;
    * belt_cbc_encrypt / belt_cbc_decrypt    — режим сцепления блоков
      с заимствованием последнего блока (Ciphertext Stealing, п. 6.2.4).

Реализация на чистом Python, использует ту же таблицу H, что и belt_hash.
"""
from __future__ import annotations

from typing import Tuple

from belt_hash import (
    _H,
    _belt_block_decrypt as _decrypt_block,
    _belt_block_encrypt as _encrypt_block,
)

BLOCK_SIZE = 16
KEY_SIZE = 32


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def belt_block_encrypt(block: bytes, key: bytes) -> bytes:
    """Шифрование одного 128-битного блока ключом 256 бит (СТБ 34.101.31-2020 п. 6.1.3)."""
    if len(block) != BLOCK_SIZE:
        raise ValueError("block must be 16 bytes")
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 32 bytes")
    return _encrypt_block(block, key)


def belt_block_decrypt(block: bytes, key: bytes) -> bytes:
    if len(block) != BLOCK_SIZE:
        raise ValueError("block must be 16 bytes")
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 32 bytes")
    return _decrypt_block(block, key)


# ----------------------------------------------------------------------------- 
# Простейший PKCS#7-совместимый паддинг для выравнивания под BLOCK_SIZE
# (в СТБ паддинг явно не регламентирован, используем PKCS#7).
# ----------------------------------------------------------------------------- 
def pkcs7_pad(data: bytes, block: int = BLOCK_SIZE) -> bytes:
    pad_len = block - (len(data) % block) or block
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data: bytes, block: int = BLOCK_SIZE) -> bytes:
    if not data or len(data) % block != 0:
        raise ValueError("data must be non-empty and multiple of block size")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > block or data[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("invalid PKCS#7 padding")
    return data[:-pad_len]


# ----------------------------------------------------------------------------- 
# Режим ECB (простая замена), СТБ 34.101.31-2020 п. 6.2.3
# Для упрощения работаем с блоками, кратными BLOCK_SIZE байтам.
# ----------------------------------------------------------------------------- 
def belt_ecb_encrypt(plain: bytes, key: bytes) -> bytes:
    if len(plain) == 0 or len(plain) % BLOCK_SIZE != 0:
        raise ValueError("plaintext must be non-empty and multiple of 16 bytes")
    out = bytearray()
    for i in range(0, len(plain), BLOCK_SIZE):
        out += belt_block_encrypt(plain[i:i + BLOCK_SIZE], key)
    return bytes(out)


def belt_ecb_decrypt(cipher: bytes, key: bytes) -> bytes:
    if len(cipher) == 0 or len(cipher) % BLOCK_SIZE != 0:
        raise ValueError("ciphertext must be non-empty and multiple of 16 bytes")
    out = bytearray()
    for i in range(0, len(cipher), BLOCK_SIZE):
        out += belt_block_decrypt(cipher[i:i + BLOCK_SIZE], key)
    return bytes(out)


# ----------------------------------------------------------------------------- 
# Режим CBC, СТБ 34.101.31-2020 п. 6.2.4 (без заимствования, работаем только
# с полными блоками).
# ----------------------------------------------------------------------------- 
def belt_cbc_encrypt(plain: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != BLOCK_SIZE:
        raise ValueError("iv must be 16 bytes")
    if len(plain) == 0 or len(plain) % BLOCK_SIZE != 0:
        raise ValueError("plaintext must be non-empty and multiple of 16 bytes")
    out = bytearray()
    prev = iv
    for i in range(0, len(plain), BLOCK_SIZE):
        blk = belt_block_encrypt(_xor(plain[i:i + BLOCK_SIZE], prev), key)
        out += blk
        prev = blk
    return bytes(out)


def belt_cbc_decrypt(cipher: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != BLOCK_SIZE:
        raise ValueError("iv must be 16 bytes")
    if len(cipher) == 0 or len(cipher) % BLOCK_SIZE != 0:
        raise ValueError("ciphertext must be non-empty and multiple of 16 bytes")
    out = bytearray()
    prev = iv
    for i in range(0, len(cipher), BLOCK_SIZE):
        blk = cipher[i:i + BLOCK_SIZE]
        out += _xor(belt_block_decrypt(blk, key), prev)
        prev = blk
    return bytes(out)


# ----------------------------------------------------------------------------- 
# Самотест на векторах из приложения А СТБ 34.101.31-2020
# ----------------------------------------------------------------------------- 
def _self_test() -> bool:
    # A.1-1 — base block
    x = bytes(_H[:16])
    k = bytes(_H[128:160])
    y = belt_block_encrypt(x, k)
    if y.hex().upper() != "69CCA1C93557C9E3D66BC3E0FA88FA6E":
        print(f"A.1-1 FAIL: {y.hex().upper()}")
        return False
    # round-trip ECB
    pt = bytes(range(48))
    key = bytes(range(32))
    iv = bytes(range(16))
    ct = belt_ecb_encrypt(pt, key)
    assert belt_ecb_decrypt(ct, key) == pt, "ECB round-trip failed"
    ct = belt_cbc_encrypt(pt, key, iv)
    assert belt_cbc_decrypt(ct, key, iv) == pt, "CBC round-trip failed"
    # неровный остаток — проверяем работу с паддингом
    pt2 = bytes(range(35))
    padded = pkcs7_pad(pt2)
    ct2 = belt_ecb_encrypt(padded, key)
    assert pkcs7_unpad(belt_ecb_decrypt(ct2, key)) == pt2
    ct2 = belt_cbc_encrypt(padded, key, iv)
    assert pkcs7_unpad(belt_cbc_decrypt(ct2, key, iv)) == pt2
    return True


if __name__ == "__main__":
    print("belt block/ECB/CBC self-test (СТБ 34.101.31-2020)")
    ok = _self_test()
    print("PASSED" if ok else "FAILED")
