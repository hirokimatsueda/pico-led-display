/*
 * 爆弾解除ゲーム
 *
 * 1 本の導火線が燃え続けるなかで、ワイヤーを切り続ける。ラウンドの開始時に
 * 一瞬だけ正解側のワイヤーが緑に光るので、それを憶えてボタン A (左) か
 * ボタン B (右) を押す。正解なら導火線が少し伸び、間違えると残り時間が 4 割
 * 吹き飛ぶ。**死ぬのは導火線が燃え尽きたときだけ**で、誤答は即死ではない。
 * したがって残り時間だけが緊張の源であり、秒読み・点滅・爆発といった演出は
 * 常に意味を持つ。スコアは切れたワイヤーの本数。
 *
 * 画面 (8x8):
 *   外周 28 ドット = 導火線。残量に応じて緑→黄→赤に変わり、先端が炎として光る。
 *   内側 6x6       = 操作盤。左右のワイヤー束 (x=1,2 と x=5,6) と中央の起爆装置。
 * さらに残り時間が減るほど速くなる鼓動に合わせて、表示全体の輝度を明滅させる。
 *
 * 複雑な部類のゲームなので、導火線タイマーや表示パターンといった専用ヘルパーは
 * 共有ユーティリティにせずこのファイル内に閉じて持つ。
 */
#include <stdio.h>

#include "game/games.h"

#define COUNT_OF(a) ((int)(sizeof(a) / sizeof((a)[0])))

typedef enum {
    STATE_REVEAL, /* ワイヤーの色を見せている */
    STATE_ARMED,  /* 入力待ち */
    STATE_CUT,    /* 正解: ワイヤーが切れる */
    STATE_SHORT,  /* 誤答: ショートして導火線が一気に燃える */
    STATE_BLAST,  /* 爆発アニメーション */
    STATE_OVER,   /* 残り火。両ボタン同時押しで再スタート */
} bomb_state_t;

/* --- 導火線 (一時停止に対応した、増減できるカウントダウン) --- */
typedef struct {
    uint32_t remaining_ms;
    uint32_t last_ms;
    bool paused;
} fuse_t;

#define FUSE_MAX_MS 10000u

static void fuse_reset(fuse_t *f, uint32_t ms) {
    f->remaining_ms = (ms > FUSE_MAX_MS) ? FUSE_MAX_MS : ms;
    f->last_ms = now_ms();
    f->paused = false;
}

static uint32_t fuse_tick(fuse_t *f) {
    if (f->paused) {
        return f->remaining_ms;
    }
    uint32_t now = now_ms();
    uint32_t elapsed = now - f->last_ms;
    f->last_ms = now;
    f->remaining_ms = (elapsed >= f->remaining_ms) ? 0 : (f->remaining_ms - elapsed);
    return f->remaining_ms;
}

/* 正解のボーナス (正) と誤答のペナルティ (負) を加える */
static void fuse_add(fuse_t *f, int32_t delta_ms) {
    int32_t value = (int32_t)f->remaining_ms + delta_ms;
    if (value < 0) {
        value = 0;
    } else if (value > (int32_t)FUSE_MAX_MS) {
        value = (int32_t)FUSE_MAX_MS;
    }
    f->remaining_ms = (uint32_t)value;
}

static void fuse_pause(fuse_t *f) {
    if (!f->paused) {
        fuse_tick(f);
        f->paused = true;
    }
}

static void fuse_resume(fuse_t *f) {
    if (f->paused) {
        f->last_ms = now_ms(); /* 止まっていた分は経過させない */
        f->paused = false;
    }
}

/* --- 表示 --- */
typedef struct {
    int8_t x, y;
} point_t;

/* 外周を左上から時計回りに 1 周。導火線はこの順に並び、末尾から燃えて短くなる */
static const point_t FUSE_RING[] = {
    {0, 0}, {1, 0}, {2, 0}, {3, 0}, {4, 0}, {5, 0}, {6, 0}, {7, 0},
    {7, 1}, {7, 2}, {7, 3}, {7, 4}, {7, 5}, {7, 6}, {7, 7},
    {6, 7}, {5, 7}, {4, 7}, {3, 7}, {2, 7}, {1, 7}, {0, 7},
    {0, 6}, {0, 5}, {0, 4}, {0, 3}, {0, 2}, {0, 1},
};
#define RING_COUNT COUNT_OF(FUSE_RING)

/* 爆発後の残り火 */
static const point_t EMBER_PATTERN[] = {
    {1, 6}, {3, 5}, {6, 6}, {2, 3}, {5, 2}, {4, 6}, {6, 3}, {1, 2},
};

#define WIRE_LEFT_X 1
#define WIRE_RIGHT_X 5

/* 中心からの距離 (0 = 中央 2x2, 3 = 外周)。爆発の波紋に使う */
static int shell_of(int x, int y) {
    int dx = (x < 4) ? (3 - x) : (x - 4);
    int dy = (y < 4) ? (3 - y) : (y - 4);
    return (dx > dy) ? dx : dy;
}

/* 導火線の残量を外周に描く。残りが少ないほど色が険しくなる */
static void draw_ring(float fraction, bool flame_on) {
    int lit = (int)(fraction * (float)RING_COUNT + 0.5f);
    if (lit > RING_COUNT) {
        lit = RING_COUNT;
    }
    if (lit <= 0) {
        lit = (fraction > 0.0f) ? 1 : 0; /* 生きている間は 1 ドットだけ残す */
    }

    led_color_t body = (fraction > 0.5f) ? LED_GREEN : ((fraction > 0.2f) ? LED_YELLOW : LED_RED);
    for (int i = 0; i < lit; i++) {
        bool is_flame = (i == lit - 1);
        led_color_t color = is_flame ? (flame_on ? LED_YELLOW : LED_RED) : body;
        matrix_set(FUSE_RING[i].x, FUSE_RING[i].y, color);
    }
}

/*
 * ワイヤー束を 1 つ描く。gap は中央から数えた切れ幅で、0 = 無傷、
 * 3 = 完全に切断。切断は中央から上下へ弾けるように広がる。
 */
static void draw_bundle(int x0, led_color_t color, int gap) {
    if (color == LED_OFF) {
        return;
    }
    for (int x = x0; x < x0 + 2; x++) {
        for (int y = 1; y <= 6; y++) {
            int distance = (y <= 3) ? (4 - y) : (y - 3); /* 中央から 1..3 */
            if (distance > gap) {
                matrix_set(x, y, color);
            }
        }
    }
}

/* 中央の起爆装置 (2x2) */
static void draw_core(led_color_t color) {
    if (color == LED_OFF) {
        return;
    }
    for (int x = 3; x <= 4; x++) {
        for (int y = 3; y <= 4; y++) {
            matrix_set(x, y, color);
        }
    }
}

/*
 * --- 効果音 ---
 *
 * 音程はプロジェクト共通の 4 度堆積 (D - G - C - F) から選ぶ。秒読みは鼓動と
 * 同じ間隔で鳴らすため終盤は連打になるので振幅を抑え、切断音・ショート音・
 * 爆発だけを前に出す。
 */
static const sfx_step_t SFX_ARM_STEPS[] = {SFX_TONE(294, 40)};        /* D4 */
static const sfx_step_t SFX_TICK_STEPS[] = {SFX_TONE(392, 26)};       /* G4 */
static const sfx_step_t SFX_TICK_WARN_STEPS[] = {SFX_TONE(1175, 30)}; /* D6 */
static const sfx_step_t SFX_CUT_STEPS[] = {
    SFX_TONE(784, 35),  /* G5 */
    SFX_TONE(1175, 55), /* D6 */
};
static const sfx_step_t SFX_SHORT_STEPS[] = {SFX_SWEEP(500, 120, 160)};
static const sfx_step_t SFX_SHORT_LOW_STEPS[] = {SFX_SWEEP(294, 110, 260)}; /* D4 から下降 */
static const sfx_step_t SFX_BLAST_STEPS[] = {SFX_SWEEP(900, 60, 400)};
static const sfx_step_t SFX_RUMBLE_STEPS[] = {SFX_SWEEP(392, 147, 600)}; /* G4 -> D3 */

static const sfx_t SFX_ARM = SFX_DEF(SFX_ARM_STEPS, AUDIO_WAVE_SQUARE, 150);
static const sfx_t SFX_TICK = SFX_DEF(SFX_TICK_STEPS, AUDIO_WAVE_SQUARE, 170);
static const sfx_t SFX_TICK_WARN = SFX_DEF(SFX_TICK_WARN_STEPS, AUDIO_WAVE_SQUARE, 205);
static const sfx_t SFX_CUT = SFX_DEF(SFX_CUT_STEPS, AUDIO_WAVE_SQUARE, 200);
static const sfx_t SFX_SHORT = SFX_DEF(SFX_SHORT_STEPS, AUDIO_WAVE_NOISE, 240);
static const sfx_t SFX_SHORT_LOW = SFX_DEF(SFX_SHORT_LOW_STEPS, AUDIO_WAVE_TRIANGLE, 190);
static const sfx_t SFX_BLAST = SFX_DEF(SFX_BLAST_STEPS, AUDIO_WAVE_NOISE, 255);
static const sfx_t SFX_RUMBLE = SFX_DEF(SFX_RUMBLE_STEPS, AUDIO_WAVE_TRIANGLE, 200);

/* --- 時間の設計 --- */
#define BONUS_BASE_MS 2400u /* 1 本切るごとに伸びる長さ。切るほど渋くなる */
#define BONUS_STEP_MS 60u
#define BONUS_MIN_MS 900u

#define PENALTY_NUM 2u /* 誤答で残り時間の 2/5 を失う */
#define PENALTY_DEN 5u
#define PENALTY_MIN_MS 600u

/* 正解の色を見せる時間。切るほど短くなる */
#define REVEAL_BASE_MS 600u
#define REVEAL_STEP_MS 18u
#define REVEAL_MIN_MS 140u

/* フェイク (先に嘘の色を見せる) の発生率 */
#define FAKE_CHANCE_MAX 0.6f
#define FAKE_CHANCE_PER_CUT 0.05f

/* 鼓動の間隔。導火線が短くなるほど速くなる */
#define BEAT_SLOW_MS 1000u
#define BEAT_FAST_MS 190u
#define BEAT_FLASH_MS 80u
#define BRIGHT_PEAK 15u
#define BRIGHT_BASE 7u

#define CUT_EFFECT_MS 420u
#define SHORT_EFFECT_MS 520u
#define BLAST_EFFECT_MS 1800u

/* --- 状態 --- */
static bomb_state_t state;
static fuse_t fuse;
static int cuts; /* 切れたワイヤーの本数 = スコア */
static bool correct_is_a;

static uint32_t reveal_start_ms;
static uint32_t reveal_fake_ms; /* 嘘の色を見せている長さ (0 ならフェイクなし) */
static uint32_t reveal_true_ms;
static uint32_t effect_start_ms;
static bool cut_was_a; /* 直前に選んだ側 */

static float ring_shown; /* 表示用にならした導火線の残量 */
static uint32_t beat_ms; /* 直近の鼓動の時刻 */
static uint32_t flash_until_ms;
static bool beat_flash;

static bool last_pressed_a;
static bool last_pressed_b;
static int last_score_shown;

static void show_score(void) {
    if (cuts != last_score_shown) {
        seg_int02(cuts);
        last_score_shown = cuts;
    }
}

/* 導火線の残量に合わせて鼓動を刻み、輝度と秒読みを駆動する */
static void beat_update(void) {
    float fraction = (float)fuse.remaining_ms / (float)FUSE_MAX_MS;
    uint32_t interval = BEAT_FAST_MS + (uint32_t)((float)(BEAT_SLOW_MS - BEAT_FAST_MS) * fraction);

    uint32_t now = now_ms();
    if (now - beat_ms >= interval) {
        beat_ms = now;
        flash_until_ms = now + BEAT_FLASH_MS;
        audio_play((fraction <= 0.25f) ? &SFX_TICK_WARN : &SFX_TICK);
    }
    beat_flash = (now < flash_until_ms);
    matrix_brightness(beat_flash ? (uint8_t)BRIGHT_PEAK : (uint8_t)BRIGHT_BASE);
}

/* 表示用の残量を実際の残量へなめらかに寄せる (ボーナス / ペナルティが動いて見える) */
static void ring_shown_update(void) {
    float target = (float)fuse.remaining_ms / (float)FUSE_MAX_MS;
    ring_shown += (target - ring_shown) * 0.28f;
    if (ring_shown < 0.0f) {
        ring_shown = 0.0f;
    } else if (ring_shown > 1.0f) {
        ring_shown = 1.0f;
    }
}

/* 外周を描いた状態でフレームを始める。glitch はフェイク中の「信号の乱れ」 */
static void begin_frame(bool glitch) {
    matrix_fill(LED_OFF);
    if (glitch) {
        matrix_border(LED_YELLOW);
    } else {
        draw_ring(ring_shown, beat_flash);
    }
}

static void start_blast(const char *reason) {
    state = STATE_BLAST;
    effect_start_ms = now_ms();
    /* 爆発の瞬間に押していたボタンでそのまま再スタートしてしまわないようにする */
    last_pressed_a = btn_a_pressed();
    last_pressed_b = btn_b_pressed();
    audio_play(&SFX_BLAST);
    audio_play(&SFX_RUMBLE);
    printf("BOOM (%s) - wires cut: %d\n", reason, cuts);
}

static void start_round(void) {
    correct_is_a = (rand_below(2) == 0);

    uint32_t reduction = (uint32_t)cuts * REVEAL_STEP_MS;
    reveal_true_ms =
        (reduction >= REVEAL_BASE_MS - REVEAL_MIN_MS) ? REVEAL_MIN_MS : (REVEAL_BASE_MS - reduction);

    /*
     * フェイクは「正しい色を見せる時間」を削らず、その前に嘘の色を足す形にする。
     * 見分ける手掛かりとして、嘘を見せている間は外周が黄色くちらつく。
     */
    float fake_chance = (float)cuts * FAKE_CHANCE_PER_CUT;
    if (fake_chance > FAKE_CHANCE_MAX) {
        fake_chance = FAKE_CHANCE_MAX;
    }
    reveal_fake_ms = (rand_float() < fake_chance) ? (reveal_true_ms * 3u / 4u) : 0u;

    reveal_start_ms = now_ms();
    state = STATE_REVEAL;
    audio_play(&SFX_ARM);
}

static void initialize(void) {
    cuts = 0;
    last_score_shown = -1;
    last_pressed_a = false;
    last_pressed_b = false;
    effect_start_ms = 0;
    cut_was_a = false;

    fuse_reset(&fuse, FUSE_MAX_MS);
    ring_shown = 1.0f;
    beat_ms = now_ms();
    flash_until_ms = 0;
    beat_flash = false;

    matrix_brightness((uint8_t)BRIGHT_BASE);
    show_score();
    start_round();

    printf("Bomb Defuse started - fuse %.1fs\n", (double)FUSE_MAX_MS / 1000.0);
}

static void cut_wire(bool pressed_a) {
    cut_was_a = pressed_a;

    if (pressed_a == correct_is_a) {
        uint32_t reduction = (uint32_t)cuts * BONUS_STEP_MS;
        uint32_t bonus =
            (reduction >= BONUS_BASE_MS - BONUS_MIN_MS) ? BONUS_MIN_MS : (BONUS_BASE_MS - reduction);
        fuse_add(&fuse, (int32_t)bonus);
        cuts++;
        state = STATE_CUT;
        effect_start_ms = now_ms();
        audio_play(&SFX_CUT);
        printf("Cut %d - fuse +%ums (%ums left)\n", cuts, (unsigned)bonus,
               (unsigned)fuse.remaining_ms);
        return;
    }

    /* 誤答: 残り時間の 4 割 (最低 600ms) が吹き飛ぶ。即死はしない */
    uint32_t penalty = fuse.remaining_ms * PENALTY_NUM / PENALTY_DEN;
    if (penalty < PENALTY_MIN_MS) {
        penalty = PENALTY_MIN_MS;
    }
    fuse_add(&fuse, -(int32_t)penalty);
    state = STATE_SHORT;
    effect_start_ms = now_ms();
    audio_play(&SFX_SHORT);
    audio_play(&SFX_SHORT_LOW);
    printf("Short circuit - fuse -%ums (%ums left)\n", (unsigned)penalty,
           (unsigned)fuse.remaining_ms);
}

/* 導火線が尽きていたら爆発へ移る */
static bool check_burnout(void) {
    if (fuse.remaining_ms > 0) {
        return false;
    }
    start_blast("fuse burned out");
    return true;
}

static void update_reveal(void) {
    uint32_t elapsed = now_ms() - reveal_start_ms;
    if (elapsed >= reveal_fake_ms + reveal_true_ms) {
        state = STATE_ARMED;
        return;
    }

    bool faking = (elapsed < reveal_fake_ms);
    bool show_a_green = faking ? !correct_is_a : correct_is_a;

    /* フェイク中は外周を黄色くちらつかせて「信号が乱れている」ことを見せる */
    begin_frame(faking && ((now_ms() / 60u) % 2u == 0u));
    draw_bundle(WIRE_LEFT_X, show_a_green ? LED_GREEN : LED_RED, 0);
    draw_bundle(WIRE_RIGHT_X, show_a_green ? LED_RED : LED_GREEN, 0);
    draw_core(faking ? LED_YELLOW : LED_RED);
    matrix_show();
}

static void update_armed(void) {
    if (btn_a_fell()) {
        cut_wire(true);
        return;
    }
    if (btn_b_fell()) {
        cut_wire(false);
        return;
    }

    begin_frame(false);
    draw_bundle(WIRE_LEFT_X, LED_RED, 0);
    draw_bundle(WIRE_RIGHT_X, LED_RED, 0);
    draw_core(beat_flash ? LED_YELLOW : LED_RED);
    matrix_show();
}

/* 選んだ束が中央から弾けて切れる */
static void update_cut(void) {
    uint32_t elapsed = now_ms() - effect_start_ms;
    if (elapsed >= CUT_EFFECT_MS) {
        start_round();
        return;
    }

    int gap = (int)(elapsed * 4u / CUT_EFFECT_MS); /* 0..3 */
    begin_frame(false);
    draw_bundle(cut_was_a ? WIRE_LEFT_X : WIRE_RIGHT_X, LED_GREEN, gap);
    draw_bundle(cut_was_a ? WIRE_RIGHT_X : WIRE_LEFT_X, LED_RED, 0);
    draw_core((gap < 2) ? LED_GREEN : LED_RED);
    matrix_show();
}

/* 選んだ束がショートして激しく明滅し、正解だった側を緑で教える */
static void update_short(void) {
    uint32_t elapsed = now_ms() - effect_start_ms;
    if (elapsed >= SHORT_EFFECT_MS) {
        start_round();
        return;
    }

    bool spark = ((elapsed / 60u) % 2u == 0u);
    int wrong_x = cut_was_a ? WIRE_LEFT_X : WIRE_RIGHT_X;
    int right_x = cut_was_a ? WIRE_RIGHT_X : WIRE_LEFT_X;

    begin_frame(false);
    draw_bundle(wrong_x, spark ? LED_YELLOW : LED_RED, 0);
    draw_bundle(right_x, LED_GREEN, 0);
    draw_core(spark ? LED_YELLOW : LED_OFF);
    matrix_show();
}

/*
 * 爆発。白飛び → 外へ広がる波紋 → 崩れて残り火、の 3 段で輝度も落としていく。
 * 静止画を数秒出すのではなく、時間の流れを見せることを狙っている。
 */
static void update_blast(void) {
    uint32_t elapsed = now_ms() - effect_start_ms;
    if (elapsed >= BLAST_EFFECT_MS) {
        state = STATE_OVER;
        return;
    }

    matrix_fill(LED_OFF);

    if (elapsed < 120u) {
        matrix_brightness((uint8_t)BRIGHT_PEAK);
        matrix_fill(LED_YELLOW);
    } else if (elapsed < 900u) {
        matrix_brightness((uint8_t)BRIGHT_PEAK);
        int front = (int)((elapsed - 120u) * 4u / 780u); /* 0..3 の波面 */
        for (int x = 0; x < MATRIX_WIDTH; x++) {
            for (int y = 0; y < MATRIX_HEIGHT; y++) {
                int shell = shell_of(x, y);
                if (shell == front) {
                    matrix_set(x, y, LED_YELLOW);
                } else if (shell < front) {
                    matrix_set(x, y, LED_RED);
                }
            }
        }
    } else {
        /* 残り火: 明滅しながら暗くなる */
        uint32_t fade = (elapsed - 900u) * 10u / (BLAST_EFFECT_MS - 900u); /* 0..9 */
        matrix_brightness((uint8_t)((fade >= 9u) ? 3u : (12u - fade)));
        bool phase = ((elapsed / 90u) % 2u == 0u);
        for (int i = 0; i < COUNT_OF(EMBER_PATTERN); i++) {
            if ((i % 2 == 0) == phase) {
                matrix_set(EMBER_PATTERN[i].x, EMBER_PATTERN[i].y, LED_RED);
            }
        }
    }

    matrix_show();
}

static void update_over(void) {
    bool pressed_a = btn_a_pressed();
    bool pressed_b = btn_b_pressed();

    /* 両ボタン同時押しで再スタート */
    if (pressed_a && pressed_b && !(last_pressed_a && last_pressed_b)) {
        initialize();
        return;
    }
    last_pressed_a = pressed_a;
    last_pressed_b = pressed_b;

    matrix_brightness(3);
    matrix_fill(LED_OFF);
    bool phase = ((now_ms() / 500u) % 2u == 0u);
    for (int i = 0; i < COUNT_OF(EMBER_PATTERN); i++) {
        if ((i % 2 == 0) == phase) {
            matrix_set(EMBER_PATTERN[i].x, EMBER_PATTERN[i].y, LED_RED);
        }
    }
    matrix_show();
}

static void update(void) {
    if (state == STATE_BLAST) {
        update_blast();
        return;
    }
    if (state == STATE_OVER) {
        update_over();
        return;
    }

    /* ここから先は導火線が燃えている状態。演出中も時間は進む */
    fuse_tick(&fuse);
    beat_update();
    ring_shown_update();
    show_score();

    if (check_burnout()) {
        return;
    }

    switch (state) {
    case STATE_REVEAL:
        update_reveal();
        break;
    case STATE_ARMED:
        update_armed();
        break;
    case STATE_CUT:
        update_cut();
        break;
    case STATE_SHORT:
        update_short();
        break;
    case STATE_BLAST:
    case STATE_OVER:
        break; /* 冒頭で処理済み */
    }
}

static void pause_game(void) {
    fuse_pause(&fuse);
    audio_stop_all();
    matrix_brightness(15); /* 選択モードや次のゲームに暗いまま渡さない */
    printf("Bomb Defuse paused\n");
}

static void resume_game(void) {
    fuse_resume(&fuse);
    beat_ms = now_ms();
    flash_until_ms = 0;
    printf("Bomb Defuse resumed\n");
}

static void finalize(void) {
    audio_stop_all();
    matrix_brightness(15);
    matrix_fill(LED_OFF);
    matrix_show();
    seg_text(NULL);

    state = STATE_REVEAL;
    cuts = 0;
    last_score_shown = -1;
    last_pressed_a = false;
    last_pressed_b = false;
    fuse_reset(&fuse, FUSE_MAX_MS);

    printf("Bomb Defuse finalized\n");
}

const game_t game_bomb_defuse = {
    .name = "BombDefuse",
    .initialize = initialize,
    .update = update,
    .finalize = finalize,
    .pause = pause_game,
    .resume = resume_game,
};
