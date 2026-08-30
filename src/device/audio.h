/*
 * 効果音エンジン (PWM オーディオ出力 + DMA ミキサー)
 *
 * GP20 の PWM を 10bit / 約 146kHz のキャリアで回し、DMA タイマーが刻む
 * サンプリングレートでデューティ値を流し込む。DMA 完了割り込みの中で次の
 * バッファをミックスするため、ゲーム側のメインループは一切関与しない
 * (CircuitPython 版で必要だった毎フレームの update() が不要になる)。
 *
 * 複数のボイスを同時に鳴らせるので、ジャンプ音の途中でスコア音が重なっても
 * 前の音が打ち切られない。
 */
#ifndef AUDIO_H
#define AUDIO_H

#include <stdbool.h>
#include <stdint.h>
#include "pico/types.h"

#define AUDIO_SAMPLE_RATE 22050
#define AUDIO_VOICE_COUNT 6 /* 同時に鳴らせる音の数 */

/* マスター音量の既定値 (0..255)。うるさすぎる場合はここか audio_set_volume() で下げる */
#define AUDIO_DEFAULT_VOLUME 255

typedef enum {
    AUDIO_WAVE_SQUARE = 0,   /* 矩形波: レトロなピコピコ音 */
    AUDIO_WAVE_TRIANGLE = 1, /* 三角波: 矩形波より柔らかい */
    AUDIO_WAVE_NOISE = 2,    /* ノイズ: 爆発音・衝突音 */
} audio_wave_t;

/*
 * 効果音の 1 ステップ。CircuitPython 版 SoundManager の譜面と同じ考え方で、
 * 定常音・スイープ・休符を表現する。
 */
typedef struct {
    uint16_t freq_start;  /* Hz (0 なら休符) */
    uint16_t freq_end;    /* Hz (0 なら freq_start と同じ = 定常音) */
    uint16_t duration_ms; /* 長さ (ミリ秒) */
} sfx_step_t;

#define SFX_TONE(freq, ms) {(freq), 0, (ms)}
#define SFX_SWEEP(from, to, ms) {(from), (to), (ms)}
#define SFX_REST(ms) {0, 0, (ms)}

typedef struct {
    const sfx_step_t *steps;
    uint8_t step_count;
    audio_wave_t wave;
    uint8_t amplitude; /* 0..255 */
} sfx_t;

/* 効果音テーブルから sfx_t を組み立てるためのヘルパー */
#define SFX_DEF(steps_array, wave, amp)                                                            \
    {(steps_array), (uint8_t)(sizeof(steps_array) / sizeof((steps_array)[0])), (wave), (amp)}

void audio_init(uint pin);

/* 空いているボイスで鳴らす (全て埋まっていたら最も進んでいる音を置き換える) */
void audio_play(const sfx_t *sfx);

/*
 * フラッシュに焼き込んだ PCM (符号付き 8bit モノラル) を鳴らす。
 * XIP でそのまま読み出すので RAM は消費しない。
 */
void audio_play_sample(const int8_t *pcm, uint32_t length, uint32_t sample_rate, uint8_t amplitude);

void audio_stop_all(void);
void audio_set_volume(uint8_t volume); /* 0..255 */
bool audio_is_playing(void);

#endif /* AUDIO_H */
