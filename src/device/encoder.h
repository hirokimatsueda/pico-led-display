/*
 * ロータリーエンコーダー (インクリメンタル型)
 *
 * CircuitPython 版の rotaryio.IncrementalEncoder 相当。GPIO 割り込みで
 * 4 逓倍のクォーターステップを数え、1 クリック = 1 カウントになるよう 4 で割る。
 */
#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>
#include "pico/types.h"

void encoder_init(uint pin_a, uint pin_b);

/* 現在位置 (1 クリック単位) */
int32_t encoder_position(void);

#endif /* ENCODER_H */
