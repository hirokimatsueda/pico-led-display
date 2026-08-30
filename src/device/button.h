/*
 * 押しボタンのデバウンス処理
 *
 * CircuitPython 版の adafruit_debouncer 相当。プルアップ + Low アクティブで、
 * 「押された瞬間」を fell として 1 フレームだけ立てる。
 */
#ifndef BUTTON_H
#define BUTTON_H

#include <stdbool.h>
#include <stdint.h>

#include "pico/types.h"

typedef struct {
    uint pin;
    bool raw;         /* 直前に読んだ生の値 */
    bool state;       /* デバウンス後の値 (true = 離されている) */
    bool fell;        /* このフレームで押された (High -> Low) */
    bool rose;        /* このフレームで離された (Low -> High) */
    uint32_t last_change_us;
} button_t;

void button_init(button_t *btn, uint pin);

/* 毎フレーム 1 回だけ呼ぶ。fell / rose はこの呼び出しの間だけ true になる */
void button_update(button_t *btn);

static inline bool button_pressed(const button_t *btn) { return !btn->state; }

#endif /* BUTTON_H */
