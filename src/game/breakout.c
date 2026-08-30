/*
 * ブロック崩し
 *
 * 2 つのボタンで 3 ドットのパドルを操作し、ボールで上部 3 行のブロックを崩す。
 * 全て壊せばクリア (緑で全点灯)、下端にボールが落ちればゲームオーバー (赤で全点灯)。
 */
#include <stdio.h>

#include "game/games.h"

#define BLOCK_ROWS 3
#define BLOCK_COUNT (BLOCK_ROWS * MATRIX_WIDTH)
#define BALL_SPEED 0.125f

/*
 * --- 効果音 ---
 *
 * 音程はプロジェクト共通の 4 度堆積 (D - G - C - F) から選ぶ。
 * ブロックは列 (上ほど高い) ごとに音程を変えて、崩した位置が耳でも分かるようにした。
 * 反射音はラリー中ずっと鳴るので短く弱め、破壊音とゲーム終了音だけを目立たせる。
 */
static const sfx_step_t SFX_PADDLE_MOVE_STEPS[] = {SFX_TONE(587, 18)}; /* D5 */
static const sfx_step_t SFX_WALL_STEPS[] = {SFX_TONE(880, 22)};        /* A5 */
static const sfx_step_t SFX_PADDLE_HIT_STEPS[] = {SFX_TONE(440, 30)};  /* A4 */
static const sfx_step_t SFX_BLOCK_TOP_STEPS[] = {SFX_TONE(1397, 45)};  /* F6 (最上段) */
static const sfx_step_t SFX_BLOCK_MID_STEPS[] = {SFX_TONE(1047, 45)};  /* C6 */
static const sfx_step_t SFX_BLOCK_LOW_STEPS[] = {SFX_TONE(784, 45)};   /* G5 (最下段) */
static const sfx_step_t SFX_CLEAR_STEPS[] = {
    SFX_TONE(587, 45),  /* D5 */
    SFX_TONE(784, 45),  /* G5 */
    SFX_TONE(1047, 45), /* C6 */
    SFX_TONE(1397, 45), /* F6 */
    SFX_REST(30),
    SFX_TONE(1760, 160), /* A6 */
};
static const sfx_step_t SFX_CRASH_STEPS[] = {SFX_SWEEP(500, 90, 180)};
static const sfx_step_t SFX_FALL_STEPS[] = {SFX_SWEEP(392, 147, 420)}; /* G4 -> D3 */

static const sfx_t SFX_PADDLE_MOVE = SFX_DEF(SFX_PADDLE_MOVE_STEPS, AUDIO_WAVE_TRIANGLE, 120);
static const sfx_t SFX_WALL = SFX_DEF(SFX_WALL_STEPS, AUDIO_WAVE_TRIANGLE, 150);
static const sfx_t SFX_PADDLE_HIT = SFX_DEF(SFX_PADDLE_HIT_STEPS, AUDIO_WAVE_SQUARE, 200);
static const sfx_t SFX_BLOCK_ROW[BLOCK_ROWS] = {
    SFX_DEF(SFX_BLOCK_TOP_STEPS, AUDIO_WAVE_SQUARE, 210),
    SFX_DEF(SFX_BLOCK_MID_STEPS, AUDIO_WAVE_SQUARE, 210),
    SFX_DEF(SFX_BLOCK_LOW_STEPS, AUDIO_WAVE_SQUARE, 210),
};
static const sfx_t SFX_CLEAR = SFX_DEF(SFX_CLEAR_STEPS, AUDIO_WAVE_SQUARE, 220);
static const sfx_t SFX_CRASH = SFX_DEF(SFX_CRASH_STEPS, AUDIO_WAVE_NOISE, 255);
static const sfx_t SFX_FALL = SFX_DEF(SFX_FALL_STEPS, AUDIO_WAVE_TRIANGLE, 190);

typedef enum {
    STATE_PLAYING,
    STATE_GAME_OVER,
    STATE_GAME_CLEAR,
} breakout_state_t;

static struct {
    int x; /* パドル中央の X 座標 */
    int y;
} paddle;

static struct {
    float x, y;
    float vx, vy;
} ball;

static bool block_active[BLOCK_COUNT];

static bool is_running;
static bool score_shown;
static int score;
static breakout_state_t state;
static bool both_pressed_prev;

static inline int block_x(int i) { return i % MATRIX_WIDTH; }
static inline int block_y(int i) { return i / MATRIX_WIDTH; }

static void update_score_display(void) { seg_int(score); }

static void refresh(void) {
    matrix_fill(LED_OFF);

    for (int i = 0; i < BLOCK_COUNT; i++) {
        if (block_active[i]) {
            matrix_set(block_x(i), block_y(i), LED_RED);
        }
    }

    /* パドルは 3 ドットの緑 */
    for (int dx = -1; dx <= 1; dx++) {
        matrix_set(paddle.x + dx, paddle.y, LED_GREEN);
    }

    int bx = (int)ball.x;
    int by = (int)ball.y;
    if (bx >= 0 && bx < MATRIX_WIDTH && by >= 0 && by < MATRIX_HEIGHT) {
        matrix_set(bx, by, LED_YELLOW);
    }

    matrix_show();
}

static void initialize(void) {
    is_running = true;
    score_shown = false;
    score = 0;
    state = STATE_PLAYING;

    paddle.x = 3;
    paddle.y = 7;

    for (int i = 0; i < BLOCK_COUNT; i++) {
        block_active[i] = true;
    }

    /* ボールはパドルの上から右斜め上に発射する */
    ball.x = (float)paddle.x;
    ball.y = 6.0f;
    ball.vx = BALL_SPEED;
    ball.vy = -BALL_SPEED;

    both_pressed_prev = false;

    update_score_display();
    refresh();
}

static bool handle_paddle_input(void) {
    int prev_x = paddle.x;

    /* ボタン A で左へ、ボタン B で右へ (画面端まで) */
    if (btn_a_fell() && paddle.x < 6) {
        paddle.x++;
    }
    if (btn_b_fell() && paddle.x > 1) {
        paddle.x--;
    }

    bool moved = paddle.x != prev_x;
    if (moved) {
        audio_play(&SFX_PADDLE_MOVE);
    }
    return moved;
}

static bool move_objects(void) {
    int prev_pixel_x = (int)ball.x;
    int prev_pixel_y = (int)ball.y;

    ball.x += ball.vx;
    ball.y += ball.vy;

    /* 画面上のドット位置が変わった時だけ描き直せばよい */
    return (int)ball.x != prev_pixel_x || (int)ball.y != prev_pixel_y;
}

static bool check_wall_collisions(void) {
    bool collided = false;

    if (ball.x <= 0.0f || ball.x >= 7.0f) {
        ball.vx = -ball.vx;
        ball.x = (ball.x <= 0.0f) ? 0.0f : 7.0f;
        collided = true;
        audio_play(&SFX_WALL);
    }

    if (ball.y <= 0.0f) {
        ball.vy = -ball.vy;
        ball.y = 0.0f;
        collided = true;
        audio_play(&SFX_WALL);
    }

    if (ball.y >= 8.0f) {
        state = STATE_GAME_OVER;
        is_running = false;
        collided = true;
    }

    return collided;
}

static bool check_paddle_collision(void) {
    /*
     * 描画時は (int) で切り捨てた列を使うため、判定も同じ列基準で行う
     * (paddle.x + 1 の右端で ball.x が非整数のまま素通りするのを防ぐ)。
     */
    int ball_col = (int)ball.x;
    if (ball.y >= 7.0f && ball.vy > 0.0f && ball_col >= paddle.x - 1 && ball_col <= paddle.x + 1) {
        /* パドルのどこに当たったかで反射角を変える */
        float angle_factor = (ball.x - (float)paddle.x) * 0.5f;
        ball.vx = BALL_SPEED * angle_factor;
        ball.vy = -((ball.vy < 0.0f) ? -ball.vy : ball.vy);
        ball.y = 6.0f;

        audio_play(&SFX_PADDLE_HIT);
        return true;
    }
    return false;
}

static bool check_block_collisions(void) {
    int bx = (int)ball.x;
    int by = (int)ball.y;

    if (bx < 0 || bx >= MATRIX_WIDTH || by < 0 || by >= BLOCK_ROWS) {
        return false;
    }

    int index = by * MATRIX_WIDTH + bx;
    if (!block_active[index]) {
        return false;
    }

    /* 1 フレームで複数のブロックを壊さないよう、最初の 1 個で処理を終える */
    block_active[index] = false;
    ball.vy = -ball.vy;
    score++;
    audio_play(&SFX_BLOCK_ROW[by]);
    return true;
}

static void check_game_end_conditions(void) {
    for (int i = 0; i < BLOCK_COUNT; i++) {
        if (block_active[i]) {
            return;
        }
    }
    state = STATE_GAME_CLEAR;
    is_running = false;
}

static void show_game_end_display(void) {
    matrix_fill(LED_OFF);

    if (state == STATE_GAME_CLEAR) {
        printf("Game Clear! Score: %d\n", score);
        matrix_fill(LED_GREEN);
        audio_play(&SFX_CLEAR);
    } else if (state == STATE_GAME_OVER) {
        printf("Game Over! Score: %d\n", score);
        matrix_fill(LED_RED);
        /* ノイズの衝撃音と下降する三角波を重ねる */
        audio_play(&SFX_CRASH);
        audio_play(&SFX_FALL);
    }

    update_score_display();
    matrix_show();
}

static void handle_restart_input(void) {
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
}

static void update(void) {
    if (!is_running) {
        if (!score_shown) {
            score_shown = true;
            show_game_end_display();
        }
        handle_restart_input();
        return;
    }

    bool input_processed = handle_paddle_input();
    bool objects_moved = move_objects();

    bool wall = check_wall_collisions();
    bool paddle_hit = check_paddle_collision();
    bool block_hit = check_block_collisions();
    bool collided = wall || paddle_hit || block_hit;

    check_game_end_conditions();

    if (block_hit) {
        update_score_display();
    }

    if (objects_moved || collided || input_processed) {
        refresh();
    }
}

static void finalize(void) {
    audio_stop_all();
    matrix_fill(LED_OFF);
    matrix_show();
    seg_text(NULL);
}

const game_t game_breakout = {
    .name = "Breakout",
    .initialize = initialize,
    .update = update,
    .finalize = finalize,
    .pause = NULL,
    .resume = NULL,
};
