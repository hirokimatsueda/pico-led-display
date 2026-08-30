/*
 * 落ちてくるドットを避けるゲーム
 *
 * 上からランダムな位置に黄色のドットが落ちてきて、プレイヤー (2x2 の緑) を
 * 左右ボタンで動かして避ける。1 個避けるごとに落下速度が上がる。
 * 衝突したら停止し、両ボタン同時押しで再スタートできる。
 */
#include <stdio.h>

#include "game/games.h"

/*
 * --- 効果音 ---
 *
 * 音程はプロジェクト共通の 4 度堆積 (D - G - C - F) から選ぶ。
 * 移動音は連打されるため、聞き取れるぎりぎりまで短く弱くしてある。
 * 衝突音はノイズの衝撃音と落ちていく三角波を重ねて鳴らす。
 */
static const sfx_step_t SFX_START_STEPS[] = {
    SFX_TONE(587, 40),  /* D5 */
    SFX_TONE(1047, 70), /* C6 */
};
static const sfx_step_t SFX_MOVE_STEPS[] = {SFX_TONE(880, 18)}; /* A5 */
static const sfx_step_t SFX_SCORE_STEPS[] = {
    SFX_TONE(784, 20),  /* G5 */
    SFX_TONE(1047, 45), /* C6 */
};
static const sfx_step_t SFX_CRASH_STEPS[] = {SFX_SWEEP(600, 100, 160)};
static const sfx_step_t SFX_FALL_STEPS[] = {SFX_SWEEP(392, 147, 380)}; /* G4 -> D3 */

static const sfx_t SFX_START = SFX_DEF(SFX_START_STEPS, AUDIO_WAVE_SQUARE, 190);
static const sfx_t SFX_MOVE = SFX_DEF(SFX_MOVE_STEPS, AUDIO_WAVE_TRIANGLE, 130);
static const sfx_t SFX_SCORE = SFX_DEF(SFX_SCORE_STEPS, AUDIO_WAVE_SQUARE, 200);
static const sfx_t SFX_CRASH = SFX_DEF(SFX_CRASH_STEPS, AUDIO_WAVE_NOISE, 255);
static const sfx_t SFX_FALL = SFX_DEF(SFX_FALL_STEPS, AUDIO_WAVE_TRIANGLE, 180);

static bool is_running;
static bool score_shown;

static int player_x, player_y;

static struct {
    int x, y;
    bool is_visible;
} dot;

static float dot_speed;  /* ドットが 1 マス落ちる間隔 (秒) */
static int dot_count;    /* 出現したドットの数 */
static uint32_t last_drop_ms;
static bool both_pressed_prev;
static uint32_t pause_ms;

static void spawn_dot(void) {
    dot.x = (int)rand_below(MATRIX_WIDTH);
    dot.y = 0;
    dot.is_visible = true;

    dot_speed /= 1.1f; /* 新規生成ごとに加速する */
    dot_count++;

    seg_int(dot_count - 1); /* 避けた数 = 得点 */
}

static void initialize(void) {
    is_running = true;
    score_shown = false;

    player_x = MATRIX_WIDTH / 2 - 1;
    player_y = MATRIX_HEIGHT - 2;

    dot_speed = 0.5f;
    dot_count = 0;
    spawn_dot();

    last_drop_ms = now_ms();
    both_pressed_prev = false;

    audio_play(&SFX_START);
}

static void refresh(void) {
    matrix_fill(LED_OFF);

    if (dot.is_visible) {
        matrix_set(dot.x, dot.y, LED_YELLOW);
    }

    /* プレイヤーは 2x2 の緑 */
    for (int dx = 0; dx < 2; dx++) {
        for (int dy = 0; dy < 2; dy++) {
            matrix_set(player_x + dx, player_y + dy, LED_GREEN);
        }
    }

    matrix_show();
}

static bool move_objects(void) {
    bool moved = false;

    if (btn_a_fell()) {
        int next = player_x + 1;
        player_x = (next > MATRIX_WIDTH - 2) ? MATRIX_WIDTH - 2 : next;
        moved = true;
        audio_play(&SFX_MOVE);
    }
    if (btn_b_fell()) {
        int next = player_x - 1;
        player_x = (next < 0) ? 0 : next;
        moved = true;
        audio_play(&SFX_MOVE);
    }

    uint32_t now = now_ms();
    if (now - last_drop_ms >= (uint32_t)(dot_speed * 1000.0f)) {
        last_drop_ms = now;
        if (dot.is_visible) {
            dot.y++;
            if (dot.y >= MATRIX_HEIGHT) {
                dot.is_visible = false;
            }
        }
        if (!dot.is_visible) {
            audio_play(&SFX_SCORE);
            spawn_dot();
        }
        moved = true;
    }

    return moved;
}

static void update(void) {
    if (!is_running) {
        if (!score_shown) {
            score_shown = true;
            printf("Game over. score = %d\n\n", dot_count - 1);
            matrix_border(LED_RED);
            matrix_show();
            /* ノイズの衝撃音と下降する三角波を重ねる */
            audio_play(&SFX_CRASH);
            audio_play(&SFX_FALL);

            /*
             * 衝突した瞬間に両ボタンが押されたままだと「両方押されている状態への
             * 遷移」が即成立して意図せずリセットされるため、一度両方離されるまで
             * リセット判定を無効化する。
             */
            both_pressed_prev = true;
        }

        /*
         * fell 同士 (押した瞬間) の一致で判定すると両ボタンの押下が同一フレームに
         * 揃わない限りリセットされないため、「両方押されている」状態への遷移で見る。
         */
        bool both_pressed = btn_a_pressed() && btn_b_pressed();
        if (both_pressed && !both_pressed_prev) {
            both_pressed_prev = both_pressed;
            initialize();
            return;
        }
        both_pressed_prev = both_pressed;
        return;
    }

    bool moved = move_objects();

    /* 衝突判定 (表示中のドットのみ) */
    if (dot.is_visible) {
        for (int dx = 0; dx < 2; dx++) {
            for (int dy = 0; dy < 2; dy++) {
                if (player_x + dx == dot.x && player_y + dy == dot.y) {
                    is_running = false;
                }
            }
        }
    }

    if (moved) {
        refresh();
    }
}

static void pause_game(void) {
    pause_ms = now_ms();
    audio_stop_all();
}

static void resume_game(void) {
    /* 一時停止していた時間だけ落下タイマーをずらす */
    last_drop_ms += now_ms() - pause_ms;
}

static void finalize(void) {
    audio_stop_all();
    matrix_fill(LED_OFF);
    matrix_show();
}

const game_t game_falling_dot = {
    .name = "FallingDot",
    .initialize = initialize,
    .update = update,
    .finalize = finalize,
    .pause = pause_game,
    .resume = resume_game,
};
