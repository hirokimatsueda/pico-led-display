/*
 * ゲームインターフェース
 *
 * CircuitPython 版の Game 基底クラス相当。継承の代わりに関数ポインタの表を
 * 持たせる。同時に動くゲームは 1 つだけなので、各ゲームは状態を自分の
 * 翻訳単位の static 変数として持ち、動的確保は一切行わない。
 */
#ifndef GAME_H
#define GAME_H

#include <stdbool.h>
#include <stdint.h>

#include "device/device_manager.h"
#include "pico/rand.h"
#include "pico/time.h"

typedef struct {
    const char *name;
    void (*initialize)(void);
    void (*update)(void);
    void (*finalize)(void);
    void (*pause)(void);  /* 不要なら NULL */
    void (*resume)(void); /* 不要なら NULL */
} game_t;

/* --- ゲーム共通の小道具 (ハードウェア寄りのユーティリティのみ) --- */

/* CircuitPython 版の time.monotonic() 相当。ミリ秒で扱う */
static inline uint32_t now_ms(void) { return to_ms_since_boot(get_absolute_time()); }

/* 0 以上 bound 未満の整数 */
static inline uint32_t rand_below(uint32_t bound) { return get_rand_32() % bound; }

/* 0.0 以上 1.0 未満の浮動小数点数 */
static inline float rand_float(void) { return (float)(get_rand_32() >> 8) / (float)(1u << 24); }

#endif /* GAME_H */
