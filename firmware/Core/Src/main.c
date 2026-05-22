/*
 * main.c — точка входа прошивки криптомодуля на STM32F103C8T6
 *          (плата STM32 Smart V2.0).
 *
 * Алгоритм работы:
 *   1. Инициализация HAL, тактирования HSE 8 МГц → PLL → 72 МГц.
 *   2. Инициализация USB CDC (PA11 — D-, PA12 — D+; перед запуском USB линия
 *      D+ кратковременно тянется к 0 для перезапуска перечисления).
 *   3. Инициализация криптомодуля (загрузка параметров bign-128).
 *   4. Бесконечный цикл: чтение из USB CDC RX-буфера; как только в буфере
 *      есть полный пакет (CMD + LEN + DATA) — выполнить usb_protocol_handle
 *      и отправить ответ через CDC_Transmit_FS.
 *
 * USB RX-кольцо реализовано в usbd_cdc_if.c: при приёме данных
 * CDC_Receive_FS копирует их в g_rx_buf, обновляя g_rx_head.
 */

#include "main.h"
#include "stm32f1xx_hal.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"
#include "adc.h"          /* CubeMX-генерируемый заголовок MX_ADC1_Init */
#include "crypto_stb.h"
#include "usb_protocol.h"

#include <string.h>

#define RX_RING_SIZE 4096u
#define TX_BUF_SIZE  2300u

extern volatile uint8_t  g_rx_buf[RX_RING_SIZE];
extern volatile uint32_t g_rx_head;   /* куда писать (изменяется в ISR) */
static   uint32_t        g_rx_tail = 0; /* откуда читать */

static uint8_t s_frame[USB_PROTO_HEADER_LEN + USB_PROTO_MAX_PAYLOAD];
static uint8_t s_tx_buf[TX_BUF_SIZE];

static void SystemClock_Config(void);

static uint32_t rx_avail(void)
{
    return (g_rx_head - g_rx_tail) & (RX_RING_SIZE - 1u);
}

static uint8_t rx_pop(void)
{
    uint8_t b = g_rx_buf[g_rx_tail & (RX_RING_SIZE - 1u)];
    g_rx_tail++;
    return b;
}

static bool try_read_frame(size_t *out_len)
{
    if (rx_avail() < USB_PROTO_HEADER_LEN) return false;
    uint8_t cmd = g_rx_buf[g_rx_tail & (RX_RING_SIZE - 1u)];
    uint8_t l0  = g_rx_buf[(g_rx_tail + 1u) & (RX_RING_SIZE - 1u)];
    uint8_t l1  = g_rx_buf[(g_rx_tail + 2u) & (RX_RING_SIZE - 1u)];
    uint16_t plen = (uint16_t)l0 | ((uint16_t)l1 << 8);
    if (plen > USB_PROTO_MAX_PAYLOAD) {
        /* мусор — сдвигаем читающую позицию на 1 и пробуем заново */
        rx_pop();
        return false;
    }
    if (rx_avail() < (uint32_t)USB_PROTO_HEADER_LEN + plen) return false;
    /* копируем полный кадр в линейный буфер */
    s_frame[0] = cmd; s_frame[1] = l0; s_frame[2] = l1;
    rx_pop(); rx_pop(); rx_pop();
    for (uint16_t i = 0; i < plen; ++i) {
        s_frame[USB_PROTO_HEADER_LEN + i] = rx_pop();
    }
    *out_len = USB_PROTO_HEADER_LEN + plen;
    return true;
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_USB_DEVICE_Init();

    /* Калибровка ADC и включение DWT-счётчика (нужен для rng_stm32). */
    extern ADC_HandleTypeDef hadc1;
    HAL_ADCEx_Calibration_Start(&hadc1);
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL  |= DWT_CTRL_CYCCNTENA_Msk;

    crypto_init();

    for (;;) {
        size_t in_len = 0;
        if (!try_read_frame(&in_len)) {
            HAL_Delay(1);
            continue;
        }
        size_t out_len = 0;
        usb_protocol_handle(s_frame, in_len, s_tx_buf, sizeof(s_tx_buf), &out_len);
        if (out_len > 0u) {
            /* Активный опрос состояния передачи; при USB FS обычно достаточно ~5 мс. */
            uint32_t deadline = HAL_GetTick() + 200u;
            while (CDC_Transmit_FS(s_tx_buf, (uint16_t)out_len) == USBD_BUSY) {
                if (HAL_GetTick() >= deadline) break;
            }
        }
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef o = {0};
    RCC_ClkInitTypeDef c = {0};
    RCC_PeriphCLKInitTypeDef p = {0};

    o.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    o.HSEState = RCC_HSE_ON;
    o.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLMUL = RCC_PLL_MUL9;   /* 8 MHz × 9 = 72 MHz */
    HAL_RCC_OscConfig(&o);

    c.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.AHBCLKDivider = RCC_SYSCLK_DIV1;
    c.APB1CLKDivider = RCC_HCLK_DIV2;   /* 36 МГц */
    c.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&c, FLASH_LATENCY_2);

    p.PeriphClockSelection = RCC_PERIPHCLK_USB;
    p.UsbClockSelection = RCC_USBCLKSOURCE_PLL_DIV1_5;   /* 72/1.5 = 48 МГц */
    HAL_RCCEx_PeriphCLKConfig(&p);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1) {}
}
