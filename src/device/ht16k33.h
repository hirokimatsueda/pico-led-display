/*
 * HT16K33 ドライバ (8x8 二色 LED マトリクス / 4桁7セグ表示器)
 *
 * CircuitPython 版の adafruit_ht16k33 と同じ表示 RAM レイアウトを再現している。
 * 表示 RAM はホスト側に持ち、show() のタイミングでまとめて I2C 転送する。
 */
#ifndef HT16K33_H
#define HT16K33_H

#include <stdbool.h>
#include <stdint.h>
#include "hardware/i2c.h"

#define HT16K33_ADDR 0x70

/* LED マトリクスの色 (CircuitPython 版の Matrix8x8x2 と同じ値) */
typedef enum {
    LED_OFF = 0,
    LED_RED = 1,
    LED_GREEN = 2,
    LED_YELLOW = 3,
} led_color_t;

typedef struct {
    i2c_inst_t *i2c;
    uint8_t addr;
    uint8_t ram[16]; /* HT16K33 の表示 RAM (COM0..COM15) */
} ht16k33_t;

/* 共通: 発振器 ON・表示 ON・輝度設定を行い、表示をクリアする */
void ht16k33_init(ht16k33_t *dev, i2c_inst_t *i2c, uint8_t addr);
void ht16k33_set_brightness(ht16k33_t *dev, uint8_t brightness); /* 0..15 */
void ht16k33_show(ht16k33_t *dev);

/* --- 8x8 二色マトリクス --- */
/*
 * 表示 RAM のレイアウト (adafruit_ht16k33 の Matrix8x8x2 と同一):
 *   ram[2 * x]     = 列 x の緑ビット (bit y)
 *   ram[2 * x + 1] = 列 x の赤ビット (bit y)
 */
void ht16k33_matrix_fill(ht16k33_t *dev, led_color_t color);
void ht16k33_matrix_set_pixel(ht16k33_t *dev, int x, int y, led_color_t color);
led_color_t ht16k33_matrix_get_pixel(const ht16k33_t *dev, int x, int y);

/* --- 4桁7セグ表示器 --- */
/*
 * 桁 0..3 は表示 RAM の 0, 2, 6, 8 番地に対応する (4 番地はコロン)。
 */
void ht16k33_seg_clear(ht16k33_t *dev);
void ht16k33_seg_put_char(ht16k33_t *dev, int index, char c);
/* 右詰めで文字列を表示する (CircuitPython 版の fill(0) + print() 相当) */
void ht16k33_seg_print(ht16k33_t *dev, const char *text);

#endif /* HT16K33_H */
