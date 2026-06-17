/*
 * key_storage.h
 *
 * Хранилище долговременных ключей в области Flash микроконтроллера
 * STM32F103C8T6. Используется последняя страница Flash объёмом 1 КБ.
 *
 * Формат записи:
 *   uint32_t  magic         = 0x53544231   // "STB1"
 *   uint8_t   privkey[32]                   // закрытый ключ bign-128
 *   uint8_t   pubkey[64]                    // публичный ключ bign-128
 *   uint32_t  crc32                         // CRC поверх всех полей выше
 *
 * Размер блока = 4 + 32 + 64 + 4 = 104 байта < 1024.
 */

#ifndef KEY_STORAGE_H_
#define KEY_STORAGE_H_

#include <stdint.h>
#include <stdbool.h>

#define KS_MAGIC 0x53544231u   /* 'S','T','B','1' */

typedef struct {
    uint32_t magic;
    uint8_t  privkey[32];
    uint8_t  pubkey[64];
    uint32_t crc;
} key_record_t;

bool ks_load(key_record_t *out);
bool ks_store(const key_record_t *rec);

#endif /* KEY_STORAGE_H_ */
