/*
 * rng_stm32.c — источник энтропии для STM32F103.
 *
 * STM32F103 не имеет аппаратного RNG. В качестве источника энтропии
 * используется комбинация:
 *   1) уникальный 96-битный идентификатор кристалла (0x1FFFF7E8);
 *   2) счётчик SysTick на момент вызова (нестабилен между перезапусками);
 *   3) ADC-замер внутреннего датчика температуры (наименее значимые биты).
 *
 * Энтропия пропускается через belt-hash, что даёт криптостойкий генератор
 * (расширение секрета). Реализация совместима с bee2 rng_t (callback).
 */

#include <stdint.h>
#include <string.h>
#include <stdbool.h>

#include "stm32f1xx_hal.h"
#include "bee2/crypto/belt.h"

extern ADC_HandleTypeDef hadc1;

static uint8_t s_state[32];
static bool    s_state_inited = false;

static void seed_state(void)
{
    uint8_t pool[64] = {0};
    /* UID 96 бит из ROM */
    memcpy(pool, (const void *)UID_BASE, 12);
    /* SysTick value */
    uint32_t t = SysTick->VAL;
    memcpy(pool + 12, &t, 4);
    /* DWT->CYCCNT, если включён */
    uint32_t cyc = DWT->CYCCNT;
    memcpy(pool + 16, &cyc, 4);
    /* пара выборок ADC (датчик температуры) */
    HAL_ADC_Start(&hadc1);
    for (int i = 0; i < 8; ++i) {
        HAL_ADC_PollForConversion(&hadc1, 10);
        uint16_t v = (uint16_t)HAL_ADC_GetValue(&hadc1);
        pool[20 + i * 2] = (uint8_t)v;
        pool[21 + i * 2] = (uint8_t)(v >> 8);
    }
    HAL_ADC_Stop(&hadc1);
    beltHash(s_state, pool, sizeof(pool));
    s_state_inited = true;
}

/* Извлекает n байт из «расширителя секрета»: state = belt-hash(state || cnt). */
void stm32_rng_step(void *buf, size_t n, void *state)
{
    (void)state;
    if (!s_state_inited) seed_state();
    uint8_t *out = (uint8_t *)buf;
    size_t produced = 0;
    uint64_t cnt = 0;
    while (produced < n) {
        uint8_t input[40];
        memcpy(input, s_state, 32);
        memcpy(input + 32, &cnt, 8);
        beltHash(s_state, input, sizeof(input));
        size_t take = (n - produced) < 32 ? (n - produced) : 32;
        memcpy(out + produced, s_state, take);
        produced += take;
        cnt++;
    }
}
