/*
 * key_storage.c — хранение ключевой пары bign-128 в Flash STM32F103C8T6.
 *
 * Используется последняя страница Flash (1 КБ) по адресу
 *   FLASH_KEY_ADDR = 0x0801FC00  (для STM32F103C8 = 64 КБ Flash, размер страницы 1 КБ).
 *
 * Чтение — прямое обращение к Flash. Запись — через HAL_FLASH_*:
 *   разблокировка → стирание страницы → программирование по 16 бит → блокировка.
 */

#include "key_storage.h"
#include "stm32f1xx_hal.h"

#include <stddef.h>
#include <string.h>

#define FLASH_KEY_ADDR  0x0801FC00u
#ifndef FLASH_PAGE_SIZE
#define FLASH_PAGE_SIZE 0x400u   /* 1024 байта */
#endif

/* CRC-32 (IEEE 802.3) — программно, чтобы не зависеть от настроек HAL_CRC. */
static uint32_t crc32_calc(const uint8_t *p, size_t n)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; ++i) {
        crc ^= p[i];
        for (uint8_t b = 0; b < 8; ++b) {
            uint32_t mask = -(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

bool ks_load(key_record_t *out)
{
    if (!out) return false;
    memcpy(out, (const void *)FLASH_KEY_ADDR, sizeof(*out));
    if (out->magic != KS_MAGIC) return false;
    uint32_t crc = crc32_calc((const uint8_t *)out,
                              offsetof(key_record_t, crc));
    return crc == out->crc;
}

bool ks_store(const key_record_t *rec_in)
{
    if (!rec_in) return false;

    key_record_t rec = *rec_in;
    rec.magic = KS_MAGIC;
    rec.crc = crc32_calc((const uint8_t *)&rec, offsetof(key_record_t, crc));

    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef er = {
        .TypeErase = FLASH_TYPEERASE_PAGES,
        .PageAddress = FLASH_KEY_ADDR,
        .NbPages = 1u,
    };
    uint32_t page_err = 0;
    if (HAL_FLASHEx_Erase(&er, &page_err) != HAL_OK) {
        HAL_FLASH_Lock();
        return false;
    }

    const uint8_t *src = (const uint8_t *)&rec;
    const size_t   sz  = sizeof(rec);
    for (size_t off = 0; off < sz; off += 2u) {
        uint16_t hw = src[off] | (uint16_t)(off + 1 < sz ? src[off + 1] : 0xFF) << 8;
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_HALFWORD,
                              FLASH_KEY_ADDR + off, hw) != HAL_OK) {
            HAL_FLASH_Lock();
            return false;
        }
    }
    HAL_FLASH_Lock();
    return true;
}
