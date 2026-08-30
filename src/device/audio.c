#include <string.h>

#include "device/audio.h"
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "hardware/sync.h"

#define WAVE_TABLE_SIZE 256 /* 2 のべき乗であること (位相のラップに & を使うため) */
#define PWM_WRAP 1023       /* 10bit 出力。キャリアは 150MHz / 1024 = 約 146kHz */
#define PWM_MID 512         /* 無音時のデューティ (中点) */
#define OUTPUT_MAX 511      /* 中点からの最大振れ幅 */
#define AUDIO_BUF_SAMPLES 256

/*
 * 1 ボイスあたりの出力スケール。振幅 255 の 1 音がほぼフルスケールに届くよう
 * 取ってあり、音が重なった分は soft_limit() で受け止める。
 * 音量が足りない / 大きすぎる場合、まずは audio_set_volume() で調整すること。
 */
#define VOICE_SHIFT 14
#define LIMIT_KNEE 340 /* この振幅までは素通し。超えた分は 1/3 に圧縮する */

/* 周波数の再計算をまとめる単位。約 1.45ms ごとなのでスイープは十分滑らかに聞こえる */
#define CTRL_BLOCK 32

/* クリック音を防ぐための立ち上がり / 立ち下がり (サンプル数) */
#define ENV_ATTACK_SAMPLES 44   /* 約 2ms */
#define ENV_RELEASE_SAMPLES 176 /* 約 8ms */

typedef struct {
    bool active;
    bool silent; /* 休符 */

    const sfx_step_t *steps;
    uint8_t step_count;
    uint8_t step_index;
    uint8_t amp;

    const int8_t *data; /* 波形テーブル、または PCM データ */
    uint32_t data_len;
    bool wrap; /* true: 波形テーブルとして繰り返す / false: PCM を 1 回だけ */

    uint32_t phase;     /* Q16.16 でのデータ内位置 */
    uint32_t phase_inc; /* Q16.16 での 1 サンプルあたりの進み */

    uint32_t step_pos; /* このステップで経過したサンプル数 */
    uint32_t step_len; /* このステップの総サンプル数 */
    int32_t freq_start;
    int32_t freq_end;
} voice_t;

static int8_t wave_square[WAVE_TABLE_SIZE];
static int8_t wave_triangle[WAVE_TABLE_SIZE];
static int8_t wave_noise[WAVE_TABLE_SIZE];

static voice_t voices[AUDIO_VOICE_COUNT];
static uint8_t master_volume = AUDIO_DEFAULT_VOLUME;

static uint16_t audio_buf[2][AUDIO_BUF_SAMPLES];
static uint dma_chan[2];

static void build_wave_tables(void) {
    int half = WAVE_TABLE_SIZE / 2;
    for (int i = 0; i < WAVE_TABLE_SIZE; i++) {
        wave_square[i] = (i < half) ? 127 : -127;

        /* -127 から +127 へ上って戻る三角波 */
        int pos = (i < half) ? i : (WAVE_TABLE_SIZE - i);
        wave_triangle[i] = (int8_t)((pos * 254) / half - 127);
    }

    /* ノイズは LFSR で一度だけ作り、以降は波形テーブルとして繰り返す */
    uint32_t lfsr = 0xACE1u;
    for (int i = 0; i < WAVE_TABLE_SIZE; i++) {
        lfsr ^= lfsr << 13;
        lfsr ^= lfsr >> 17;
        lfsr ^= lfsr << 5;
        wave_noise[i] = (int8_t)(lfsr & 0xFF);
    }
}

static const int8_t *wave_table_for(audio_wave_t wave) {
    switch (wave) {
    case AUDIO_WAVE_TRIANGLE:
        return wave_triangle;
    case AUDIO_WAVE_NOISE:
        return wave_noise;
    case AUDIO_WAVE_SQUARE:
    default:
        return wave_square;
    }
}

static inline uint32_t phase_inc_for_freq(int32_t freq) {
    if (freq <= 0) {
        return 0;
    }
    /* 1 サンプルあたりテーブルを何エントリ進むか (Q16.16) */
    return (uint32_t)(((uint64_t)freq * WAVE_TABLE_SIZE * 65536u) / AUDIO_SAMPLE_RATE);
}

static void voice_start_step(voice_t *v) {
    const sfx_step_t *step = &v->steps[v->step_index];

    v->freq_start = step->freq_start;
    v->freq_end = (step->freq_end != 0) ? step->freq_end : step->freq_start;
    v->step_pos = 0;
    v->step_len = ((uint32_t)step->duration_ms * AUDIO_SAMPLE_RATE) / 1000u;
    if (v->step_len == 0) {
        v->step_len = 1;
    }
    v->silent = (step->freq_start == 0);
    v->phase_inc = phase_inc_for_freq(v->freq_start);
    /* 位相はステップごとにリセットして輪郭のはっきりした音にする */
    v->phase = 0;
}

/* 制御ブロックごとに 1 回だけ呼ぶ: ステップ送りと周波数の補間 */
static void voice_control(voice_t *v) {
    if (!v->active) {
        return;
    }

    if (v->step_pos >= v->step_len) {
        if (v->steps == NULL) {
            v->active = false; /* PCM は 1 回鳴らしたら終わり */
            return;
        }
        v->step_index++;
        if (v->step_index >= v->step_count) {
            v->active = false;
            return;
        }
        voice_start_step(v);
    }

    if (!v->silent && v->freq_end != v->freq_start && v->step_len > 0) {
        int32_t span = v->freq_end - v->freq_start;
        int32_t freq =
            v->freq_start + (int32_t)(((int64_t)span * (int32_t)v->step_pos) / (int32_t)v->step_len);
        v->phase_inc = phase_inc_for_freq(freq);
    }
}

/* 0..256 のゲイン。ステップの先頭と末尾を滑らかにしてクリック音を防ぐ */
static inline int32_t envelope_gain(const voice_t *v) {
    uint32_t attack = ENV_ATTACK_SAMPLES;
    uint32_t release = ENV_RELEASE_SAMPLES;

    if (v->step_len < attack + release) {
        /* 極端に短いステップでは立ち上がり / 立ち下がりを比例縮小する */
        attack = v->step_len / 4 + 1;
        release = v->step_len / 4 + 1;
    }

    if (v->step_pos < attack) {
        return (int32_t)((v->step_pos * 256u) / attack);
    }
    uint32_t remaining = (v->step_len > v->step_pos) ? (v->step_len - v->step_pos) : 0;
    if (remaining < release) {
        return (int32_t)((remaining * 256u) / release);
    }
    return 256;
}

static inline int32_t voice_render(voice_t *v) {
    if (v->silent) {
        v->step_pos++;
        return 0;
    }

    uint32_t index = v->phase >> 16;
    if (v->wrap) {
        index &= (WAVE_TABLE_SIZE - 1);
    } else if (index >= v->data_len) {
        v->active = false;
        return 0;
    }

    int32_t sample = v->data[index];
    v->phase += v->phase_inc;

    int32_t gain = envelope_gain(v);
    v->step_pos++;

    /* 127 * 255 * 256 >> 14 で、振幅 255 の 1 音がほぼフルスケール (±506) に届く */
    return (sample * (int32_t)v->amp * gain) >> VOICE_SHIFT;
}

/*
 * 出力を ±OUTPUT_MAX に収める。
 *
 * 1 音でフルスケールまで使い切る設計にしているため、音が重なると単純な足し算では
 * 振り切れてしまう。しきい値 (LIMIT_KNEE) までは素通しし、それを超えた分だけ 1/3 に
 * 圧縮することで、重なった瞬間だけ穏やかに頭打ちさせる (ハードクリップの
 * ガリガリした歪みを避ける)。
 */
static inline int32_t soft_limit(int32_t x) {
    if (x > LIMIT_KNEE) {
        x = LIMIT_KNEE + (x - LIMIT_KNEE) / 3;
        return (x > OUTPUT_MAX) ? OUTPUT_MAX : x;
    }
    if (x < -LIMIT_KNEE) {
        x = -LIMIT_KNEE + (x + LIMIT_KNEE) / 3;
        return (x < -OUTPUT_MAX) ? -OUTPUT_MAX : x;
    }
    return x;
}

static void audio_fill(uint16_t *dst) {
    for (uint32_t base = 0; base < AUDIO_BUF_SAMPLES; base += CTRL_BLOCK) {
        for (int i = 0; i < AUDIO_VOICE_COUNT; i++) {
            voice_control(&voices[i]);
        }

        for (uint32_t n = 0; n < CTRL_BLOCK; n++) {
            int32_t acc = 0;
            for (int i = 0; i < AUDIO_VOICE_COUNT; i++) {
                if (voices[i].active) {
                    acc += voice_render(&voices[i]);
                }
            }

            acc = (acc * (int32_t)master_volume) >> 8;
            dst[base + n] = (uint16_t)(PWM_MID + soft_limit(acc));
        }
    }
}

static void __isr audio_dma_handler(void) {
    for (int i = 0; i < 2; i++) {
        if (dma_hw->ints0 & (1u << dma_chan[i])) {
            dma_hw->ints0 = 1u << dma_chan[i]; /* 割り込みをクリア */
            /* 再生し終わったバッファを詰め直し、次に回ってきた時に備える */
            audio_fill(audio_buf[i]);
            dma_channel_set_read_addr(dma_chan[i], audio_buf[i], false);
        }
    }
}

static voice_t *allocate_voice(void) {
    voice_t *oldest = &voices[0];
    for (int i = 0; i < AUDIO_VOICE_COUNT; i++) {
        if (!voices[i].active) {
            return &voices[i];
        }
        /* 全て使用中なら、一番再生が進んでいるものを置き換える */
        if (voices[i].step_pos > oldest->step_pos) {
            oldest = &voices[i];
        }
    }
    return oldest;
}

void audio_init(uint pin) {
    build_wave_tables();
    memset(voices, 0, sizeof(voices));
    memset(audio_buf, 0, sizeof(audio_buf));

    /* --- PWM: 10bit のキャリアを出す --- */
    gpio_set_function(pin, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(pin);
    uint chan = pwm_gpio_to_channel(pin);

    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_wrap(&cfg, PWM_WRAP);
    pwm_init(slice, &cfg, true);
    pwm_set_chan_level(slice, chan, PWM_MID); /* 無音時は中点 */

    /* デューティ比レジスタ (CC) のうち、使用するチャンネル側の 16bit を狙う */
    volatile void *pwm_cc = (volatile void *)&pwm_hw->slice[slice].cc;
    if (chan == PWM_CHAN_B) {
        pwm_cc = (volatile uint8_t *)pwm_cc + 2;
    }

    /* --- DMA タイマー: サンプリングレートを刻む --- */
    uint timer = (uint)dma_claim_unused_timer(true);
    uint32_t den = clock_get_hz(clk_sys) / AUDIO_SAMPLE_RATE; /* 150MHz なら 6802 */
    dma_timer_set_fraction(timer, 1, (uint16_t)den);

    /* --- DMA: 2 つのバッファを交互に流し続ける (ピンポン転送) --- */
    dma_chan[0] = (uint)dma_claim_unused_channel(true);
    dma_chan[1] = (uint)dma_claim_unused_channel(true);

    for (int i = 0; i < 2; i++) {
        dma_channel_config c = dma_channel_get_default_config(dma_chan[i]);
        channel_config_set_transfer_data_size(&c, DMA_SIZE_16);
        channel_config_set_read_increment(&c, true);
        channel_config_set_write_increment(&c, false);
        channel_config_set_dreq(&c, dma_get_timer_dreq(timer));
        channel_config_set_chain_to(&c, dma_chan[1 - i]); /* 終わったら相方を起動 */
        dma_channel_configure(dma_chan[i], &c, pwm_cc, audio_buf[i], AUDIO_BUF_SAMPLES, false);
        dma_channel_set_irq0_enabled(dma_chan[i], true);
    }

    irq_set_exclusive_handler(DMA_IRQ_0, audio_dma_handler);
    irq_set_enabled(DMA_IRQ_0, true);

    dma_channel_start(dma_chan[0]);
}

void audio_play(const sfx_t *sfx) {
    if (sfx == NULL || sfx->steps == NULL || sfx->step_count == 0) {
        return;
    }

    uint32_t save = save_and_disable_interrupts();

    voice_t *v = allocate_voice();
    v->active = false; /* 設定が終わるまで再生対象から外す */
    v->steps = sfx->steps;
    v->step_count = sfx->step_count;
    v->step_index = 0;
    v->amp = sfx->amplitude;
    v->data = wave_table_for(sfx->wave);
    v->data_len = WAVE_TABLE_SIZE;
    v->wrap = true;
    voice_start_step(v);
    v->active = true;

    restore_interrupts(save);
}

void audio_play_sample(const int8_t *pcm, uint32_t length, uint32_t sample_rate,
                       uint8_t amplitude) {
    if (pcm == NULL || length == 0 || sample_rate == 0) {
        return;
    }

    uint32_t save = save_and_disable_interrupts();

    voice_t *v = allocate_voice();
    v->active = false;
    v->steps = NULL;
    v->step_count = 0;
    v->step_index = 0;
    v->amp = amplitude;
    v->data = pcm;
    v->data_len = length;
    v->wrap = false;
    v->silent = false;
    v->phase = 0;
    v->phase_inc = (uint32_t)(((uint64_t)sample_rate * 65536u) / AUDIO_SAMPLE_RATE);
    v->step_pos = 0;
    /* 出力側のサンプル数に直しておくとエンベロープが PCM にもそのまま効く */
    v->step_len = (uint32_t)(((uint64_t)length * AUDIO_SAMPLE_RATE) / sample_rate);
    v->freq_start = 0;
    v->freq_end = 0;
    v->active = true;

    restore_interrupts(save);
}

void audio_stop_all(void) {
    uint32_t save = save_and_disable_interrupts();
    for (int i = 0; i < AUDIO_VOICE_COUNT; i++) {
        voices[i].active = false;
    }
    restore_interrupts(save);
}

void audio_set_volume(uint8_t volume) { master_volume = volume; }

bool audio_is_playing(void) {
    for (int i = 0; i < AUDIO_VOICE_COUNT; i++) {
        if (voices[i].active) {
            return true;
        }
    }
    return false;
}
