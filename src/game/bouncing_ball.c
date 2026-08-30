/*
 * ボールが跳ねるゲーム
 *
 * 重力で落下して床で跳ね返るボールを表示し、残像を黄色で描く。
 * ボタン A / B は押すたびに隅のドットをトグルさせるだけの動作確認用。
 */
#include "game/games.h"

#define GRAVITY 0.08f

static struct {
    float x, y;
    float vx, vy;
} ball;

static int prev_x, prev_y;
static bool btn_a_toggle, btn_b_toggle;

static void ball_update(void) {
    ball.vy += GRAVITY;
    ball.y += ball.vy;
    ball.x += ball.vx;

    if (ball.x >= MATRIX_WIDTH - 1) {
        ball.x = MATRIX_WIDTH - 1;
        ball.vx = -ball.vx;
    } else if (ball.x <= 0) {
        ball.x = 0;
        ball.vx = -ball.vx;
    }
    if (ball.y >= MATRIX_HEIGHT - 1) {
        ball.y = MATRIX_HEIGHT - 1;
        ball.vy = -1.0f;
    }
}

static void initialize(void) {
    ball.x = 0.0f;
    ball.y = MATRIX_HEIGHT - 1;
    ball.vx = 0.2f;
    ball.vy = -1.0f;

    prev_x = (int)ball.x;
    prev_y = (int)ball.y;
    btn_a_toggle = true;
    btn_b_toggle = true;
}

static void update(void) {
    matrix_fill(LED_OFF);

    /* 残像 (前回位置) を黄色で残す */
    matrix_set(prev_x, prev_y, LED_YELLOW);

    ball_update();
    matrix_set((int)ball.x, (int)ball.y, LED_RED);

    prev_x = (int)ball.x;
    prev_y = (int)ball.y;

    if (btn_a_fell()) {
        btn_a_toggle = !btn_a_toggle;
    }
    if (btn_b_fell()) {
        btn_b_toggle = !btn_b_toggle;
    }
    matrix_set(7, 0, btn_a_toggle ? LED_GREEN : LED_OFF);
    matrix_set(0, 0, btn_b_toggle ? LED_GREEN : LED_OFF);

    matrix_show();
}

static void finalize(void) {
    matrix_fill(LED_OFF);
    matrix_show();
}

const game_t game_bouncing_ball = {
    .name = "BouncingBall",
    .initialize = initialize,
    .update = update,
    .finalize = finalize,
    .pause = NULL,
    .resume = NULL,
};
