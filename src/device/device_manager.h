/*
 * デバイス層
 *
 * LED マトリクス・7セグ表示器・ボタン・ロータリーエンコーダー・効果音の
 * ハンドルをすべてここが持つ。CircuitPython 版の DeviceManager と同じ役割だが、
 * ハードウェアは 1 セットしか存在しないためインスタンスを持ち回らず、
 * モジュール内のシングルトンとして扱う。
 *
 * 配線 (CircuitPython 版と同一):
 *   LED マトリクス (Adafruit 902) : I2C0 GP17(SCL) / GP16(SDA)
 *   7セグ表示器 (Adafruit 5599)   : I2C1 GP15(SCL) / GP14(SDA)
 *   ボタン A / B                  : GP18 / GP19 (プルアップ, Low アクティブ)
 *   ロータリーエンコーダー        : GP10(A) / GP11(B)
 *   効果音                        : GP20 (PWM) -> RC -> PAM8302A
 */
#ifndef DEVICE_MANAGER_H
#define DEVICE_MANAGER_H

#include <stdbool.h>
#include <stdint.h>

#include "device/audio.h"
#include "device/ht16k33.h"

#define MATRIX_WIDTH 8
#define MATRIX_HEIGHT 8

void devices_init(void);

/* 毎フレーム 1 回だけ呼ぶ (ボタンのデバウンス更新) */
void devices_update_inputs(void);

/* --- LED マトリクス --- */
void matrix_fill(led_color_t color);
void matrix_set(int x, int y, led_color_t color);
void matrix_show(void);
/* 外周 1 ドットを指定色で描く (show は呼び出し側に委ねる) */
void matrix_border(led_color_t color);
/*
 * 表示全体の輝度 (0..15)。HT16K33 の輝度レジスタを直接叩くので描画とは独立に効く。
 * 下げたゲームは finalize / pause で 15 に戻すこと。
 */
void matrix_brightness(uint8_t level);

/* --- 7セグ表示器 --- */
void seg_text(const char *text); /* NULL または "" でクリア */
void seg_int(int value);
void seg_int02(int value);            /* 2 桁ゼロ詰め */
void seg_selection(int game_number);  /* ゲーム選択モードの --NN-- 表示 */

/* --- ボタン (Low アクティブ) --- */
bool btn_a_pressed(void);
bool btn_b_pressed(void);
bool btn_a_fell(void); /* このフレームで押された瞬間 */
bool btn_b_fell(void);

/* --- ロータリーエンコーダー --- */
int32_t encoder_pos(void);

#endif /* DEVICE_MANAGER_H */
