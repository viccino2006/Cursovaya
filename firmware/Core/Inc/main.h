/*
 * main.h — общие объявления для прошивки.
 *
 * MX_GPIO_Init() и Error_Handler() предоставляются CubeMX-генерируемым кодом.
 */

#ifndef MAIN_H_
#define MAIN_H_

#include "stm32f1xx_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

void Error_Handler(void);
void MX_GPIO_Init(void);

#ifdef __cplusplus
}
#endif

#endif /* MAIN_H_ */
