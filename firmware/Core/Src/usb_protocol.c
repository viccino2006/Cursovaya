/*
 * usb_protocol.c — обработчик команд протокола USB CDC.
 *
 * Читает пакет [CMD : 1][LEN : 2][DATA : LEN], выполняет команду через
 * crypto_stb и key_storage, формирует ответ [STATUS : 1][LEN : 2][DATA : LEN].
 */

#include "usb_protocol.h"
#include "crypto_stb.h"
#include "key_storage.h"

#include <string.h>

static size_t pack_response(uint8_t *out, status_t st, uint16_t len)
{
    out[0] = (uint8_t)st;
    out[1] = (uint8_t)(len & 0xFFu);
    out[2] = (uint8_t)((len >> 8) & 0xFFu);
    return USB_PROTO_HEADER_LEN + (size_t)len;
}

static int respond_err(uint8_t *out, size_t cap, size_t *out_len, err_t err)
{
    if (cap < USB_PROTO_HEADER_LEN + 1u) {
        return -1;
    }
    out[USB_PROTO_HEADER_LEN] = (uint8_t)err;
    *out_len = pack_response(out, STATUS_ERR, 1u);
    return 0;
}

static int respond_ok(uint8_t *out, size_t cap, size_t *out_len,
                      const uint8_t *payload, uint16_t pl_len)
{
    if (cap < USB_PROTO_HEADER_LEN + pl_len) {
        return -1;
    }
    if (pl_len > 0 && payload != (out + USB_PROTO_HEADER_LEN)) {
        memcpy(out + USB_PROTO_HEADER_LEN, payload, pl_len);
    }
    *out_len = pack_response(out, STATUS_OK, pl_len);
    return 0;
}

int usb_protocol_handle(const uint8_t *in, size_t in_len,
                        uint8_t *out, size_t out_cap, size_t *out_len)
{
    if (in_len < USB_PROTO_HEADER_LEN) {
        return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
    }
    uint8_t cmd = in[0];
    uint16_t plen = (uint16_t)in[1] | ((uint16_t)in[2] << 8);
    if (in_len < USB_PROTO_HEADER_LEN + plen) {
        return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
    }
    const uint8_t *body = in + USB_PROTO_HEADER_LEN;

    key_record_t kr;
    uint8_t buf[CRYPTO_PUBKEY_LEN];

    switch ((cmd_t)cmd) {
    case CMD_PING: {
        const char tag[] = "BIGN1";
        return respond_ok(out, out_cap, out_len, (const uint8_t *)tag, 5);
    }

    case CMD_GET_PUBKEY: {
        if (!ks_load(&kr)) {
            return respond_err(out, out_cap, out_len, ERR_NO_KEY);
        }
        return respond_ok(out, out_cap, out_len, kr.pubkey, CRYPTO_PUBKEY_LEN);
    }

    case CMD_GEN_KEYPAIR: {
        if (crypto_keygen(kr.privkey, kr.pubkey) != 0) {
            return respond_err(out, out_cap, out_len, ERR_RNG);
        }
        if (!ks_store(&kr)) {
            return respond_err(out, out_cap, out_len, ERR_FLASH);
        }
        return respond_ok(out, out_cap, out_len, kr.pubkey, CRYPTO_PUBKEY_LEN);
    }

    case CMD_SIGN: {
        if (plen != CRYPTO_HASH_LEN) {
            return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
        }
        if (!ks_load(&kr)) {
            return respond_err(out, out_cap, out_len, ERR_NO_KEY);
        }
        if (crypto_sign_hash(body, kr.privkey, buf) != 0) {
            return respond_err(out, out_cap, out_len, ERR_INTERNAL);
        }
        return respond_ok(out, out_cap, out_len, buf, CRYPTO_SIG_LEN);
    }

    case CMD_VERIFY: {
        if (plen != CRYPTO_HASH_LEN + CRYPTO_SIG_LEN + CRYPTO_PUBKEY_LEN) {
            return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
        }
        const uint8_t *hash = body;
        const uint8_t *sig  = hash + CRYPTO_HASH_LEN;
        const uint8_t *pk   = sig  + CRYPTO_SIG_LEN;
        int rc = crypto_verify_sig(hash, sig, pk);
        if (rc == 0) {
            return respond_ok(out, out_cap, out_len, NULL, 0);
        } else if (rc == 1) {
            return respond_err(out, out_cap, out_len, ERR_BAD_SIG);
        } else {
            return respond_err(out, out_cap, out_len, ERR_INTERNAL);
        }
    }

    case CMD_HASH: {
        uint8_t hash[CRYPTO_HASH_LEN];
        if (crypto_hash(body, plen, hash) != 0) {
            return respond_err(out, out_cap, out_len, ERR_INTERNAL);
        }
        return respond_ok(out, out_cap, out_len, hash, CRYPTO_HASH_LEN);
    }

    case CMD_ENCRYPT:
    case CMD_DECRYPT: {
        /* [IV 16][KEY 32][DATA N] */
        if (plen < CRYPTO_BLOCK_LEN + CRYPTO_KEY_LEN + CRYPTO_BLOCK_LEN) {
            return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
        }
        const uint8_t *iv  = body;
        const uint8_t *key = body + CRYPTO_BLOCK_LEN;
        const uint8_t *src = body + CRYPTO_BLOCK_LEN + CRYPTO_KEY_LEN;
        size_t data_len = (size_t)plen - CRYPTO_BLOCK_LEN - CRYPTO_KEY_LEN;
        if ((data_len % CRYPTO_BLOCK_LEN) != 0u) {
            return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
        }
        if (out_cap < USB_PROTO_HEADER_LEN + data_len) {
            return respond_err(out, out_cap, out_len, ERR_BAD_LEN);
        }
        uint8_t *dst = out + USB_PROTO_HEADER_LEN;
        int rc = (cmd == CMD_ENCRYPT)
                 ? crypto_cbc_encrypt(key, iv, src, data_len, dst)
                 : crypto_cbc_decrypt(key, iv, src, data_len, dst);
        if (rc != 0) {
            return respond_err(out, out_cap, out_len, ERR_INTERNAL);
        }
        *out_len = pack_response(out, STATUS_OK, (uint16_t)data_len);
        return 0;
    }

    default:
        return respond_err(out, out_cap, out_len, ERR_BAD_CMD);
    }
}
