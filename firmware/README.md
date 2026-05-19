# Прошивка криптомодуля для STM32F103C8T6 (плата STM32 Smart V2.0)

Эта прошивка реализует криптографические преобразования по
стандартам Республики Беларусь (СТБ 34.101.31 и СТБ 34.101.45) и
обмен с ПК по интерфейсу USB CDC (Virtual COM Port).

## Структура каталога

```
firmware/
├── Core/
│   ├── Inc/                     — заголовочные файлы прикладного слоя
│   │   ├── main.h
│   │   ├── crypto_stb.h         — API криптографических функций
│   │   ├── key_storage.h        — API хранения ключей во Flash
│   │   └── usb_protocol.h       — описание протокола USB CDC
│   └── Src/
│       ├── main.c               — точка входа, основной цикл
│       ├── crypto_stb.c         — обёртка над bee2 (belt, bign)
│       ├── key_storage.c        — запись/чтение ключей в последнюю страницу Flash
│       ├── usb_protocol.c       — обработчик команд протокола
│       └── rng_stm32.c          — программный RNG на основе UID+SysTick+ADC+belt-hash
├── bee2/                        — git-submodule с библиотекой bee2
└── README.md                    — эта инструкция
```

CubeMX-генерируемые модули (`stm32f1xx_hal_msp.c`, `usbd_cdc_if.c`,
`stm32f1xx_it.c`, `system_stm32f1xx.c`) подключаются автоматически при
импорте проекта в STM32CubeIDE и здесь не приводятся, чтобы не
дублировать сгенерированный шаблон. Прикладной код привязан к
`MX_USB_DEVICE_Init`, `CDC_Transmit_FS` и глобальному кольцевому буферу
`g_rx_buf`, который заполняется из `CDC_Receive_FS`.

## Подключение библиотеки bee2

`firmware/bee2` — git-submodule (см. `git submodule update --init`). В
STM32CubeIDE добавьте в свойства проекта:

* **C/C++ Build → Settings → Include paths:**
  `${workspace_loc:/${ProjName}/bee2/include}`
* **C/C++ General → Paths and Symbols → Source Locations:** добавить
  каталог `bee2/src/core`, `bee2/src/math`, `bee2/src/crypto/belt`,
  `bee2/src/crypto/bign`, `bee2/src/crypto/brng`.

Файлы bee2 собираются как часть проекта (включаются в общий
`arm-none-eabi-gcc`-вызов). Используется конфигурация без проверки
безопасной памяти (`BEE2_NO_SAFE_DELETE`) и без поддержки RDRAND.

## Конфигурация микроконтроллера (STM32CubeMX `.ioc`)

* Тактирование: HSE 8 МГц → PLL ×9 → SYSCLK 72 МГц;
  USB-клок 48 МГц получается из PLL/1.5; APB1 = 36 МГц, APB2 = 72 МГц.
* Активные периферии: `USB Device → Communication Device Class (Virtual Port Com)`,
  `ADC1 IN16 (Temperature Sensor)`, `RCC HSE Bypass`.
* Heap/stack: `Stack Size = 0x800`, `Heap Size = 0x200`.
* Опции компилятора: `-Os -ffunction-sections -fdata-sections` (по умолчанию CubeIDE).

## Сборка

В STM32CubeIDE: импорт проекта → правая кнопка → `Build Project`.
Альтернативно, при подключённом arm-none-eabi-gcc можно собрать
прошивку и из командной строки (примерный Makefile приведён в
`firmware/Makefile.example`).

После прошивки в `.bin`/`.hex` файлах исполняемый код размещается с
адреса `0x08000000`; область `0x0801FC00 — 0x0801FFFF` (последняя
страница) зарезервирована под хранилище ключевой пары bign-128.

## Протокол USB CDC

Описан в `Core/Inc/usb_protocol.h`. Бинарный формат
`[CMD : 1][LEN : 2 LE][DATA : LEN]` для запросов и
`[STATUS : 1][LEN : 2 LE][DATA : LEN]` для ответов.
Поддерживаются команды:

| Код  | Команда         | Тело запроса                          | Тело ответа       |
|------|-----------------|----------------------------------------|-------------------|
| 0x00 | `CMD_PING`      | —                                      | `"BIGN1"` (5 байт) |
| 0x01 | `CMD_SIGN`      | 32 байта (хэш)                         | 48 байт (подпись) |
| 0x02 | `CMD_VERIFY`    | 32 + 48 + 64 байт                      | пусто (OK) или код ошибки |
| 0x03 | `CMD_GET_PUBKEY`| —                                      | 64 байта          |
| 0x04 | `CMD_GEN_KEYPAIR`| —                                     | 64 байта (новый pubkey) |
| 0x05 | `CMD_ENCRYPT`   | 16 (IV) + 32 (key) + N (plain)         | N байт            |
| 0x06 | `CMD_DECRYPT`   | 16 (IV) + 32 (key) + N (cipher)        | N байт            |
| 0x07 | `CMD_HASH`      | N байт                                 | 32 байта          |

Все команды ECRYPT/DECRYPT принимают ключ от ПК — это сделано
сознательно: устройство играет роль криптоускорителя, не сессионного
менеджера. ЭЦП же делается строго на устройстве: приватный ключ
никогда не покидает Flash микроконтроллера.
