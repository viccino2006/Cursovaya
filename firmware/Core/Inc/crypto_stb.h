/*
 * crypto_stb.h
 *
 * Прикладной слой работы с криптографическими алгоритмами Республики Беларусь:
 *   - belt-hash    (СТБ 34.101.31)
 *   - belt-cbc     (СТБ 34.101.31)
 *   - bign-sign /  bign-verify (СТБ 34.101.45) для уровня b = 128 (bign-curve256v1)
 *
 * Реализация поверх библиотеки bee2 (https://github.com/agievich/bee2).
 *
 * Размеры ключей и подписей для bign 128:
 *   - параметры params128             (bign-curve256v1, идентификатор OID 1.2.112.0.2.0.34.101.45.3.1)
 *   - закрытый ключ                   32 байта
 *   - публичный ключ                  64 байта (x || y)
 *   - хэш-значение (belt-hash)        32 байта
 *   - подпись                         48 байт (s_0 || s_1)
 */

#ifndef CRYPTO_STB_H_
#define CRYPTO_STB_H_

#include <stdint.h>
#include <stddef.h>

#define CRYPTO_HASH_LEN        32u
#define CRYPTO_PRIVKEY_LEN     32u
#define CRYPTO_PUBKEY_LEN      64u
#define CRYPTO_SIG_LEN         48u
#define CRYPTO_BLOCK_LEN       16u
#define CRYPTO_KEY_LEN         32u

/* Инициализация криптомодуля: подгружает параметры bign-128 и проверяет их. */
int crypto_init(void);

/* belt-hash (СТБ 34.101.31). Хэш всегда CRYPTO_HASH_LEN байт. */
int crypto_hash(const uint8_t *data, size_t len, uint8_t out_hash[CRYPTO_HASH_LEN]);

/* belt-cbc (СТБ 34.101.31 п. 6.2.4) — зашифрование/расшифрование.
 * Длина данных должна быть кратна CRYPTO_BLOCK_LEN. */
int crypto_cbc_encrypt(const uint8_t key[CRYPTO_KEY_LEN], const uint8_t iv[CRYPTO_BLOCK_LEN],
                       const uint8_t *in_data, size_t len, uint8_t *out_data);
int crypto_cbc_decrypt(const uint8_t key[CRYPTO_KEY_LEN], const uint8_t iv[CRYPTO_BLOCK_LEN],
                       const uint8_t *in_data, size_t len, uint8_t *out_data);

/* Подпись и проверка bign-128 (СТБ 34.101.45). */
int crypto_sign_hash(const uint8_t hash[CRYPTO_HASH_LEN],
                     const uint8_t privkey[CRYPTO_PRIVKEY_LEN],
                     uint8_t out_sig[CRYPTO_SIG_LEN]);
int crypto_verify_sig(const uint8_t hash[CRYPTO_HASH_LEN],
                      const uint8_t sig[CRYPTO_SIG_LEN],
                      const uint8_t pubkey[CRYPTO_PUBKEY_LEN]);

/* Генерация пары ключей bign-128. Возвращает приватный ключ
 * (32 байта) и публичный ключ (64 байта). Внутри использует
 * аппаратный источник энтропии (RNG-обёртку). */
int crypto_keygen(uint8_t out_priv[CRYPTO_PRIVKEY_LEN],
                  uint8_t out_pub[CRYPTO_PUBKEY_LEN]);

/* Получить публичный ключ по уже сохранённому приватному ключу. */
int crypto_pubkey_from_priv(const uint8_t priv[CRYPTO_PRIVKEY_LEN],
                            uint8_t out_pub[CRYPTO_PUBKEY_LEN]);

#endif /* CRYPTO_STB_H_ */
