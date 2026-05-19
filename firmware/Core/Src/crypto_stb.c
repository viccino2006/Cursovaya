/*
 * crypto_stb.c — реализация прикладного слоя криптографии на bee2.
 *
 * Используем функции bee2 для алгоритмов СТБ 34.101.31 (belt) и
 * СТБ 34.101.45 (bign).
 */

#include "crypto_stb.h"

#include "bee2/core/err.h"
#include "bee2/core/mem.h"
#include "bee2/core/rng.h"
#include "bee2/crypto/belt.h"
#include "bee2/crypto/bign.h"

#include <string.h>

/* Идентификатор алгоритма bign-curve256v1 (bign-128). */
#define CURVE_OID "1.2.112.0.2.0.34.101.45.3.1"

static bign_params s_params;
static bool s_params_loaded = false;

int crypto_init(void)
{
    if (bignParamsStd(&s_params, CURVE_OID) != ERR_OK) {
        return -1;
    }
    if (bignParamsVal(&s_params) != ERR_OK) {
        return -2;
    }
    s_params_loaded = true;
    return 0;
}

int crypto_hash(const uint8_t *data, size_t len, uint8_t out_hash[CRYPTO_HASH_LEN])
{
    return (beltHash(out_hash, data, len) == ERR_OK) ? 0 : -1;
}

int crypto_cbc_encrypt(const uint8_t key[CRYPTO_KEY_LEN], const uint8_t iv[CRYPTO_BLOCK_LEN],
                       const uint8_t *in_data, size_t len, uint8_t *out_data)
{
    if (len == 0u || (len % CRYPTO_BLOCK_LEN) != 0u) {
        return -1;
    }
    memmove(out_data, in_data, len);
    return (beltCBCEncr(out_data, len, key, CRYPTO_KEY_LEN, iv) == ERR_OK) ? 0 : -2;
}

int crypto_cbc_decrypt(const uint8_t key[CRYPTO_KEY_LEN], const uint8_t iv[CRYPTO_BLOCK_LEN],
                       const uint8_t *in_data, size_t len, uint8_t *out_data)
{
    if (len == 0u || (len % CRYPTO_BLOCK_LEN) != 0u) {
        return -1;
    }
    memmove(out_data, in_data, len);
    return (beltCBCDecr(out_data, len, key, CRYPTO_KEY_LEN, iv) == ERR_OK) ? 0 : -2;
}

/* Идентификатор алгоритма belt-hash (OID bign-with-hash-belt) для подписи.
 * Согласно СТБ 34.101.45 п. 6.2 используется идентификатор алгоритма хэш-функции.
 * Для belt-hash OID = 1.2.112.0.2.0.34.101.31.81. Передаётся в bignSign в виде
 * der-кодированного OID. Утилита oidToDER из bee2 даёт нужное представление. */
static const uint8_t s_oid_belt_hash[] = {
    /* OID 1.2.112.0.2.0.34.101.31.81 (id-belt-hash) */
    0x06, 0x0A, 0x2A, 0x70, 0x00, 0x02, 0x00, 0x22, 0x65, 0x1F, 0x51, 0x00
};

int crypto_sign_hash(const uint8_t hash[CRYPTO_HASH_LEN],
                     const uint8_t privkey[CRYPTO_PRIVKEY_LEN],
                     uint8_t out_sig[CRYPTO_SIG_LEN])
{
    if (!s_params_loaded) {
        return -1;
    }
    /* bignSign формирует ЭЦП с использованием детерминированного либо случайного
     * параметра k. Используем bignSign2 (детерминированный, безопаснее при отсутствии
     * качественного RNG): k формируется из приватного ключа и хэша через belt-pbkdf. */
    if (bignSign2(out_sig, &s_params, s_oid_belt_hash, sizeof(s_oid_belt_hash),
                  hash, privkey, NULL, 0) != ERR_OK) {
        return -2;
    }
    return 0;
}

int crypto_verify_sig(const uint8_t hash[CRYPTO_HASH_LEN],
                      const uint8_t sig[CRYPTO_SIG_LEN],
                      const uint8_t pubkey[CRYPTO_PUBKEY_LEN])
{
    if (!s_params_loaded) {
        return -1;
    }
    return (bignVerify(&s_params, s_oid_belt_hash, sizeof(s_oid_belt_hash),
                       hash, sig, pubkey) == ERR_OK) ? 0 : 1;
}

int crypto_keygen(uint8_t out_priv[CRYPTO_PRIVKEY_LEN],
                  uint8_t out_pub[CRYPTO_PUBKEY_LEN])
{
    if (!s_params_loaded) {
        return -1;
    }
    /* В bee2 ключевая пара генерируется через bignKeypairGen.
     * RNG передаётся как callback; на STM32 RNG-обёртка использует
     * адаптер прошивки rng_step (см. rng_stm32.c). */
    if (bignKeypairGen(out_priv, out_pub, &s_params, rngStepR2, NULL) != ERR_OK) {
        return -2;
    }
    return 0;
}

int crypto_pubkey_from_priv(const uint8_t priv[CRYPTO_PRIVKEY_LEN],
                            uint8_t out_pub[CRYPTO_PUBKEY_LEN])
{
    if (!s_params_loaded) {
        return -1;
    }
    return (bignCalcPubkey(out_pub, &s_params, priv) == ERR_OK) ? 0 : -2;
}
