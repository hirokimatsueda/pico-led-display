/*
 * 爆弾解除ゲーム
 *
 * ステージごとに正解のボタン (A または B) がランダムに決まる。開始直後に
 * 一瞬だけワイヤーの色 (正解側が緑・不正解側が赤) がフラッシュ表示されるので、
 * それを記憶して制限時間内に正しい方を押す。ステージが進むほど制限時間と
 * ヒント表示時間が短くなり、前半だけ色が逆になる「フェイク」も混ざり始める。
 *
 * 複雑な部類のゲームなので、タイマーと表示効果はこのファイル内に閉じた
 * 専用ヘルパーとして持つ (ゲーム間で共有する抽象は作らない)。
 */
#include <stdio.h>

#include "game/games.h"

typedef enum {
    STATE_PLAYING,
    STATE_SUCCESS,
    STATE_GAME_OVER,
} bomb_state_t;

/* --- 一時停止に対応したカウントダウンタイマー --- */
typedef struct {
    uint32_t initial_ms;
    uint32_t remaining_ms;
    uint32_t start_ms;
    bool is_running;
    bool is_paused;
} bomb_timer_t;

static void timer_reset(bomb_timer_t *t, uint32_t duration_ms) {
    t->initial_ms = duration_ms;
    t->remaining_ms = duration_ms;
    t->start_ms = 0;
    t->is_running = false;
    t->is_paused = false;
}

static void timer_start(bomb_timer_t *t) {
    t->start_ms = now_ms();
    t->is_running = true;
    t->is_paused = false;
}

static uint32_t timer_update(bomb_timer_t *t) {
    if (!t->is_running || t->is_paused) {
        return t->remaining_ms;
    }
    uint32_t elapsed = now_ms() - t->start_ms;
    t->remaining_ms = (elapsed >= t->initial_ms) ? 0 : (t->initial_ms - elapsed);
    return t->remaining_ms;
}

static void timer_pause(bomb_timer_t *t) {
    if (t->is_running && !t->is_paused) {
        timer_update(t);
        t->is_paused = true;
    }
}

static void timer_resume(bomb_timer_t *t) {
    if (t->is_running && t->is_paused) {
        /* 残り時間から再開するよう開始時刻を作り直す */
        t->start_ms = now_ms() - (t->initial_ms - t->remaining_ms);
        t->is_paused = false;
    }
}

/* --- 表示効果 --- */
typedef struct {
    int8_t x, y;
} point_t;

/* 爆弾本体 (導火線の燃え代は含まない) */
static const point_t BOMB_BODY_PATTERN[] = {
    {3, 2}, {4, 2},                 /* 導火線の付け根 */
    {2, 3}, {3, 3}, {4, 3}, {5, 3}, /* 本体上部 */
    {2, 4}, {3, 4}, {4, 4}, {5, 4}, /* 本体中央 */
    {2, 5}, {3, 5}, {4, 5}, {5, 5}, /* 本体下部 */
    {3, 6}, {4, 6},                 /* 本体底部 */
};

/* 導火線の未燃焼部分。手前 (爆弾に近い側) から先端の順 */
static const point_t FUSE_TRAIL[] = {{4, 1}, {4, 0}};

static const point_t EXPLOSION_PATTERN[] = {
    {3, 3}, {4, 3}, {3, 4}, {4, 4},                                 /* 中央 */
    {2, 2}, {5, 2}, {2, 5}, {5, 5}, {1, 3}, {6, 3}, {3, 1}, {4, 1}, /* 内側 */
    {3, 6}, {4, 6},
    {0, 0}, {7, 0}, {0, 7}, {7, 7}, {1, 1}, {6, 1}, {1, 6}, {6, 6}, /* 外側 */
    {0, 3}, {7, 3}, {0, 4}, {7, 4}, {3, 0}, {4, 0}, {3, 7}, {4, 7},
};

static const point_t SUCCESS_PATTERN[] = {
    {2, 4}, {3, 5}, {4, 4}, {5, 3}, {6, 2},                         /* チェックマーク */
    {1, 1}, {6, 1}, {1, 6}, {6, 6}, {0, 3}, {7, 3}, {3, 0}, {4, 0}, /* 装飾 */
    {3, 7}, {4, 7},
};

#define COUNT_OF(a) ((int)(sizeof(a) / sizeof((a)[0])))

static bool blink_state;
static uint32_t last_blink_ms;

static void draw_pattern(const point_t *pattern, int count, led_color_t color) {
    matrix_fill(LED_OFF);
    for (int i = 0; i < count; i++) {
        matrix_set(pattern[i].x, pattern[i].y, color);
    }
    matrix_show();
}

/*
 * 爆弾の表示。残り時間の割合に応じて導火線が先端から燃え尽きて短くなり、
 * 燃え尽きた後は本体ごと高速点滅させて爆発直前の緊迫感を出す。
 */
static void show_bomb(float remaining_fraction) {
    int visible_trail;
    uint32_t blink_interval_ms;

    if (remaining_fraction <= 0.2f) {
        visible_trail = 0;
        blink_interval_ms = 100;
    } else if (remaining_fraction <= 0.5f) {
        visible_trail = 1;
        blink_interval_ms = 250;
    } else {
        visible_trail = COUNT_OF(FUSE_TRAIL);
        blink_interval_ms = 600;
    }

    uint32_t now = now_ms();
    if (now - last_blink_ms >= blink_interval_ms) {
        blink_state = !blink_state;
        last_blink_ms = now;
    }

    matrix_fill(LED_OFF);

    if (visible_trail == 0) {
        /* 導火線が燃え尽きた後は本体ごと点滅させる */
        if (blink_state) {
            for (int i = 0; i < COUNT_OF(BOMB_BODY_PATTERN); i++) {
                matrix_set(BOMB_BODY_PATTERN[i].x, BOMB_BODY_PATTERN[i].y, LED_RED);
            }
        }
        matrix_show();
        return;
    }

    for (int i = 0; i < COUNT_OF(BOMB_BODY_PATTERN); i++) {
        matrix_set(BOMB_BODY_PATTERN[i].x, BOMB_BODY_PATTERN[i].y, LED_RED);
    }

    /* 燃え残りを描く。火がついている先端だけ点滅させる */
    for (int i = 0; i < visible_trail; i++) {
        bool is_tip = (i == visible_trail - 1);
        if (!is_tip || blink_state) {
            matrix_set(FUSE_TRAIL[i].x, FUSE_TRAIL[i].y, LED_YELLOW);
        }
    }

    matrix_show();
}

/* --- ゲーム本体 --- */
#define BASE_TIME_MS 10000u
#define MIN_TIME_MS 3000u
#define TIME_REDUCTION_MS 200u

#define REVEAL_BASE_MS 500u
#define REVEAL_MIN_MS 150u
#define REVEAL_REDUCTION_MS 15u

#define FAKE_CHANCE_MAX 0.6f
#define FAKE_CHANCE_PER_STAGE 0.05f

#define SUCCESS_EFFECT_MS 1000u
#define EXPLOSION_EFFECT_MS 2000u

static bomb_state_t state;
static int current_stage;
static int max_stage_reached;
static bool correct_is_a;

static bomb_timer_t timer;
static uint32_t current_stage_time_ms;

static uint32_t effect_start_ms;
static bool button_pressed;
static bool last_pressed_a;
static bool last_pressed_b;

static uint32_t input_delay_duration_ms;
static uint32_t input_delay_start_ms;
static bool input_delay_started;
static bool hint_has_fake;

static int last_display_time;

static bool is_input_delay_active(void) {
    if (!input_delay_started) {
        return false;
    }
    return (now_ms() - input_delay_start_ms) < input_delay_duration_ms;
}

static void start_new_stage(void) {
    correct_is_a = (rand_below(2) == 0);

    /* ステージが進むほど制限時間を短くする (最小 3 秒) */
    uint32_t reduction = (uint32_t)(current_stage - 1) * TIME_REDUCTION_MS;
    uint32_t stage_time =
        (reduction >= BASE_TIME_MS - MIN_TIME_MS) ? MIN_TIME_MS : BASE_TIME_MS - reduction;
    current_stage_time_ms = stage_time;

    timer_reset(&timer, stage_time);
    timer_start(&timer);

    button_pressed = false;

    /* ヒント表示時間もステージが進むほど短くする */
    uint32_t reveal_reduction = (uint32_t)(current_stage - 1) * REVEAL_REDUCTION_MS;
    input_delay_duration_ms = (reveal_reduction >= REVEAL_BASE_MS - REVEAL_MIN_MS)
                                  ? REVEAL_MIN_MS
                                  : REVEAL_BASE_MS - reveal_reduction;

    /* フェイク点滅の発生確率はステージが進むほど上がる */
    float fake_chance = (float)(current_stage - 1) * FAKE_CHANCE_PER_STAGE;
    if (fake_chance > FAKE_CHANCE_MAX) {
        fake_chance = FAKE_CHANCE_MAX;
    }
    hint_has_fake = rand_float() < fake_chance;

    input_delay_start_ms = now_ms();
    input_delay_started = true;

    state = STATE_PLAYING;

    printf("Stage %d started - Correct button: %c, Time: %.1fs\n", current_stage,
           correct_is_a ? 'A' : 'B', (double)stage_time / 1000.0);
}

static void initialize(void) {
    state = STATE_PLAYING;
    current_stage = 1;
    max_stage_reached = 1;
    correct_is_a = true;

    button_pressed = false;
    last_pressed_a = false;
    last_pressed_b = false;
    effect_start_ms = 0;
    last_display_time = -1;

    blink_state = false;
    last_blink_ms = now_ms();

    timer_reset(&timer, BASE_TIME_MS);

    seg_text(NULL);
    show_bomb(1.0f);

    start_new_stage();

    printf("Bomb Defuse Game initialized - Stage %d\n", current_stage);
}

static void handle_correct_answer(void) {
    state = STATE_SUCCESS;
    timer_pause(&timer);
    draw_pattern(SUCCESS_PATTERN, COUNT_OF(SUCCESS_PATTERN), LED_GREEN);
    effect_start_ms = now_ms();

    current_stage++;
    if (current_stage > max_stage_reached) {
        max_stage_reached = current_stage;
    }
    printf("Correct! Advancing to stage %d\n", current_stage);
}

static void handle_incorrect_answer(void) {
    state = STATE_GAME_OVER;
    timer_pause(&timer);
    draw_pattern(EXPLOSION_PATTERN, COUNT_OF(EXPLOSION_PATTERN), LED_RED);
    effect_start_ms = now_ms();
    printf("Wrong button! Game Over at stage %d\n", current_stage);
    printf("Final Score: Stage %d\n", max_stage_reached);
}

static void handle_button_press(bool pressed_a) {
    if (button_pressed || state != STATE_PLAYING) {
        return; /* 重複入力を防止する */
    }
    button_pressed = true;

    printf("Button %c pressed - Correct: %c\n", pressed_a ? 'A' : 'B', correct_is_a ? 'A' : 'B');

    if (pressed_a == correct_is_a) {
        handle_correct_answer();
    } else {
        handle_incorrect_answer();
    }
}

static void check_button_input(void) {
    bool pressed_a = btn_a_pressed();
    bool pressed_b = btn_b_pressed();

    /* ヒント表示中は入力を無視する (待機終了後の誤検出を防ぐため状態だけ更新) */
    if (is_input_delay_active()) {
        last_pressed_a = pressed_a;
        last_pressed_b = pressed_b;
        return;
    }

    /* CircuitPython 版と同じく、ボタンを「離した」タイミングで判定する */
    if (last_pressed_a && !pressed_a) {
        handle_button_press(true);
    }
    if (last_pressed_b && !pressed_b) {
        handle_button_press(false);
    }

    last_pressed_a = pressed_a;
    last_pressed_b = pressed_b;
}

static void check_timer(void) {
    if (timer_update(&timer) > 0) {
        return;
    }

    state = STATE_GAME_OVER;
    timer_pause(&timer);
    draw_pattern(EXPLOSION_PATTERN, COUNT_OF(EXPLOSION_PATTERN), LED_RED);
    effect_start_ms = now_ms();
    printf("Time's up! Game Over at stage %d\n", current_stage);
    printf("Final Score: Stage %d\n", max_stage_reached);
}

/*
 * ヒント表示 (ワイヤーカラー)
 *
 * 画面を左右に分け、正解ボタン側を緑・不正解側を赤で塗る。表示は一瞬なので
 * 記憶を頼りに判断することになる。フェイク発生時は前半だけ色が逆になり、
 * 後半で必ず正しい色に切り替わる。
 */
static void show_input_delay_display(void) {
    led_color_t real_left = correct_is_a ? LED_GREEN : LED_RED;
    led_color_t real_right = correct_is_a ? LED_RED : LED_GREEN;

    bool show_fake = false;
    if (hint_has_fake) {
        show_fake = (now_ms() - input_delay_start_ms) < (input_delay_duration_ms / 2);
    }

    led_color_t left = show_fake ? real_right : real_left;
    led_color_t right = show_fake ? real_left : real_right;

    matrix_fill(LED_OFF);
    for (int x = 0; x < 4; x++) {
        for (int y = 0; y < MATRIX_HEIGHT; y++) {
            matrix_set(x, y, left);
        }
    }
    for (int x = 4; x < MATRIX_WIDTH; x++) {
        for (int y = 0; y < MATRIX_HEIGHT; y++) {
            matrix_set(x, y, right);
        }
    }
    matrix_show();

    seg_text("--");
}

static void update_display(void) {
    if (is_input_delay_active()) {
        show_input_delay_display();
        return;
    }

    uint32_t remaining_ms = timer_update(&timer);

    /* ステージごとに制限時間が違うので、導火線の長さは割合で決める */
    float fraction =
        (current_stage_time_ms > 0) ? (float)remaining_ms / (float)current_stage_time_ms : 0.0f;
    show_bomb(fraction);

    /* 残り時間は切り上げた整数秒を 2 桁で表示する */
    int display_time = (int)((remaining_ms + 999u) / 1000u);
    seg_int02(display_time);

    if (display_time != last_display_time) {
        printf("Stage %d - Time: %02ds%s\n", current_stage, display_time,
               (fraction <= 0.2f) ? " [WARNING]" : "");
        last_display_time = display_time;
    }
}

static void show_success_effect(void) {
    if (now_ms() - effect_start_ms < SUCCESS_EFFECT_MS) {
        draw_pattern(SUCCESS_PATTERN, COUNT_OF(SUCCESS_PATTERN), LED_GREEN);
        seg_int02(current_stage - 1); /* 完了したステージ数 */
        return;
    }
    start_new_stage();
}

static void check_game_over_input(void) {
    bool pressed_a = btn_a_pressed();
    bool pressed_b = btn_b_pressed();

    /* 左右同時押しでリセット */
    if (pressed_a && pressed_b && !(last_pressed_a && last_pressed_b)) {
        initialize();
        return;
    }

    last_pressed_a = pressed_a;
    last_pressed_b = pressed_b;
}

static void show_game_over_effect(void) {
    check_game_over_input();

    if (now_ms() - effect_start_ms < EXPLOSION_EFFECT_MS) {
        draw_pattern(EXPLOSION_PATTERN, COUNT_OF(EXPLOSION_PATTERN), LED_RED);
        seg_int02(max_stage_reached);
    }
    /* エフェクト終了後はゲーム選択で切り替えられるまでそのまま待機する */
}

static void update(void) {
    switch (state) {
    case STATE_PLAYING:
        check_button_input();
        check_timer();
        update_display();
        break;
    case STATE_SUCCESS:
        show_success_effect();
        break;
    case STATE_GAME_OVER:
        show_game_over_effect();
        break;
    }
}

static void pause_game(void) {
    if (state == STATE_PLAYING) {
        timer_pause(&timer);
    }
    printf("Bomb Defuse Game paused\n");
}

static void resume_game(void) {
    if (state == STATE_PLAYING) {
        timer_resume(&timer);
    }
    printf("Bomb Defuse Game resumed\n");
}

static void finalize(void) {
    matrix_fill(LED_OFF);
    matrix_show();
    seg_text(NULL);

    state = STATE_PLAYING;
    current_stage = 1;
    max_stage_reached = 1;
    correct_is_a = true;
    button_pressed = false;
    last_pressed_a = false;
    last_pressed_b = false;
    effect_start_ms = 0;
    timer_reset(&timer, BASE_TIME_MS);

    printf("Bomb Defuse Game finalized\n");
}

const game_t game_bomb_defuse = {
    .name = "BombDefuse",
    .initialize = initialize,
    .update = update,
    .finalize = finalize,
    .pause = pause_game,
    .resume = resume_game,
};
