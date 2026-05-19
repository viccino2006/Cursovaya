/*
 * usb_protocol.h
 *
 * Описание двоичного протокола обмена между ПК и устройством STM32 по USB CDC.
 * Все поля в пакетах передаются в формате little-endian.
 *
 * Запрос (от ПК):  [CMD : 1][LEN : 2][DATA : LEN]
 * Ответ (от STM32): [STATUS : 1][LEN : 2][DATA : LEN]
 *
 * STATUS_OK   = 0xAA — операция выполнена успешно;
 * STATUS_ERR  = 0xFF — ошибка (LEN может содержать код ошибки).
 *
 * Команды:
 *   CMD_PING        0x00 — проверка связи (ответ: STATUS_OK, "BIGN1")
 *   CMD_SIGN        0x01 — подписать хэш (32 байта) → подпись (48 байт)
 *   CMD_VERIFY      0x02 — проверить подпись (хэш 32 + подпись 48 + ключ 64)
 *   CMD_GET_PUBKEY  0x03 — получить публичный ключ устройства (64 байта)
 *   CMD_GEN_KEYPAIR 0x04 — сгенерировать новую пару ключей, сохранить во Flash
 *   CMD_ENCRYPT     0x05 — зашифровать данные (BelT-CBC).
 *                          Тело запроса: [IV 16][KEY 32][PLAIN N]; ответ: [CIPHER N]
 *   CMD_DECRYPT     0x06 — расшифровать данные (BelT-CBC).
 *                          Тело запроса: [IV 16][KEY 32][CIPHER N]; ответ: [PLAIN N]
 *   CMD_HASH        0x07 — вычислить belt-hash (СТБ 34.101.31). Ответ: 32 байта.
 */

#ifndef USB_PROTOCOL_H_
#define USB_PROTOCOL_H_

#include <stdint.h>
#include <stddef.h>

#define USB_PROTO_MAX_PAYLOAD     2048u
#define USB_PROTO_HEADER_LEN      3u    /* CMD/STATUS + LEN16 */

typedef enum {
    CMD_PING        = 0x00,
    CMD_SIGN        = 0x01,
    CMD_VERIFY      = 0x02,
    CMD_GET_PUBKEY  = 0x03,
    CMD_GEN_KEYPAIR = 0x04,
    CMD_ENCRYPT     = 0x05,
    CMD_DECRYPT     = 0x06,
    CMD_HASH        = 0x07,
} cmd_t;

typedef enum {
    STATUS_OK  = 0xAA,
    STATUS_ERR = 0xFF,
} status_t;

typedef enum {
    ERR_NONE          = 0x00,
    ERR_BAD_LEN       = 0x01,
    ERR_BAD_CMD       = 0x02,
    ERR_INTERNAL      = 0x03,
    ERR_NO_KEY        = 0x04,
    ERR_BAD_SIG       = 0x05,
    ERR_BAD_KEY       = 0x06,
    ERR_RNG           = 0x07,
    ERR_FLASH         = 0x08,
} err_t;

/* Прокачивает один кадр (запрос-ответ).
 * Возвращает 0 при успехе.
 * При непустом ответе функция формирует пакет и кладёт его в out_buf;
 * out_len содержит реальный размер ответа. */
int usb_protocol_handle(const uint8_t *in_buf, size_t in_len,
                        uint8_t *out_buf, size_t out_buf_cap,
                        size_t *out_len);

#endif /* USB_PROTOCOL_H_ */
