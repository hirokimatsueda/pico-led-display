/*
 * 横スクロールのジャンプアクションゲーム
 *
 * プレイヤーは画面左寄りに固定され、右から流れてくる障害物を
 * 緑ボタン (ジャンプ)・赤ボタン (しゃがみ) で避け続ける。
 *
 * 障害物は 3 種類:
 *   GROUND (地面, 赤)     : 通常ジャンプで回避
 *   AIR    (頭の高さ, 黄) : しゃがみで回避
 *   TALL   (全高, 赤+黄)  : しゃがみ中にジャンプする「大ジャンプ」でのみ回避可能
 *
 * 加えて画面上部には、地上/空中の障害物とは独立したタイミングで洞窟の天井のような
 * ギザギザした壁がスクロールしてくる。列ごとに深さがランダムなので、大ジャンプ中に
 * どこかの列の高さへ到達すると頭をぶつける。TALL が画面内にいる間は TALL のいる列
 * だけ壁に穴が開き逃げ場になる。これにより「大ジャンプで無駄に高く跳ばない」という
 * 制約が常に効くようになる。
 */
#include <stdio.h>

#include "game/games.h"

#define PLAYER_X 1

/* 通常ジャンプ (A のみ): 地上障害物のみクリアできる高さ */
#define NORMAL_JUMP_MAX_OFFSET 3
/* 大ジャンプ (しゃがみ中に A): プレイヤー全高の障害物もクリアできる高さ */
#define BIG_JUMP_MAX_OFFSET 6
#define JUMP_DURATION_MS 450u

/*
 * 障害物 1 マス移動あたりの間隔。初期値は「安全にジャンプで避けられる時間」より
 * 短く設定し、加速してもジャンプの避けやすさが極端に損なわれないようにする。
 */
#define INITIAL_OBSTACLE_INTERVAL 0.25f
#define MIN_OBSTACLE_INTERVAL 0.12f
#define SPEEDUP_FACTOR 1.08f

/* 障害物出現時に TALL が選ばれる確率。他は地上/空中で等分 */
#define TALL_OBSTACLE_PROBABILITY 0.15f

/* 画面上部の壁が、待機中の 1 移動ステップごとに新規出現する確率 */
#define WALL_SPAWN_CHANCE 0.2f

/* 壁パターンの横幅 (列数)。列ごとに深さを変えてギザギザにする */
#define WALL_PATTERN_WIDTH 4

/*
 * TALL の逃げ場として壁に穴を開ける範囲 (TALL の列を中心に前後何列まで)。
 * 大ジャンプは開始から着地まで数ティックかかるため、TALL がちょうどプレイヤーの列に
 * いる瞬間だけ穴を開けても直前・直後のティックで別の壁区画に引っかかってしまう。
 */
#define TALL_GAP_MARGIN 2

#define GROUND_Y (MATRIX_HEIGHT - 1)     /* 7 */
#define HEAD_Y (MATRIX_HEIGHT - 2)       /* 6 */
#define CEILING_ROWS (HEAD_Y - NORMAL_JUMP_MAX_OFFSET) /* 天井の段数 = 3 */

typedef enum {
    OBSTACLE_GROUND,
    OBSTACLE_AIR,
    OBSTACLE_TALL,
} obstacle_kind_t;

/* --- 効果音 (このゲーム専用の譜面データ) --- */
static const sfx_step_t SFX_START_STEPS[] = {
    SFX_TONE(523, 50),
    SFX_TONE(784, 50),
    SFX_TONE(1047, 100),
};
static const sfx_step_t SFX_JUMP_STEPS[] = {SFX_SWEEP(392, 880, 100)};
static const sfx_step_t SFX_BIG_JUMP_STEPS[] = {SFX_SWEEP(392, 1568, 200)};
static const sfx_step_t SFX_CROUCH_STEPS[] = {SFX_SWEEP(330, 165, 70)};
static const sfx_step_t SFX_SCORE_STEPS[] = {SFX_TONE(1047, 30), SFX_TONE(1568, 50)};
static const sfx_step_t SFX_GAME_OVER_STEPS[] = {SFX_SWEEP(440, 80, 500)};

static const sfx_t SFX_START = SFX_DEF(SFX_START_STEPS, AUDIO_WAVE_SQUARE, 200);
static const sfx_t SFX_JUMP = SFX_DEF(SFX_JUMP_STEPS, AUDIO_WAVE_SQUARE, 255);
static const sfx_t SFX_BIG_JUMP = SFX_DEF(SFX_BIG_JUMP_STEPS, AUDIO_WAVE_SQUARE, 255);
static const sfx_t SFX_CROUCH = SFX_DEF(SFX_CROUCH_STEPS, AUDIO_WAVE_TRIANGLE, 200);
static const sfx_t SFX_SCORE = SFX_DEF(SFX_SCORE_STEPS, AUDIO_WAVE_SQUARE, 220);
static const sfx_t SFX_GAME_OVER = SFX_DEF(SFX_GAME_OVER_STEPS, AUDIO_WAVE_NOISE, 255);

/* --- ゲーム状態 --- */
static bool is_running;
static bool score_shown;
static bool both_pressed_prev;

static bool is_jumping;
static bool jump_is_big;
static uint32_t jump_start_ms;
static int jump_offset;

static struct {
    obstacle_kind_t kind;
    int x;
    uint8_t row_mask; /* 占有する Y 座標のビットマスク */
    bool is_visible;
} obstacle;

static float obstacle_interval;
static uint32_t last_move_ms;
static int score;

/* 画面上部の壁 (wall_x < 0 なら非表示)。wall_pattern[j] は列 wall_x - j にいる */
static int wall_x;
static int wall_pattern[WALL_PATTERN_WIDTH];

static uint32_t pause_ms;

static void update_score_display(void) { seg_int(score); }

static void spawn_obstacle(bool initial) {
    float r = rand_float();

    if (r < TALL_OBSTACLE_PROBABILITY) {
        /*
         * 壁自体は消さない。TALL がいる列だけ動的に穴を開ける (is_tall_gap_at 参照)
         * ことで、壁がいきなり消える不自然さを避ける。
         */
        obstacle.kind = OBSTACLE_TALL;
        obstacle.row_mask = 0;
        for (int y = HEAD_Y - NORMAL_JUMP_MAX_OFFSET + 1; y < MATRIX_HEIGHT; y++) {
            obstacle.row_mask |= (uint8_t)(1u << y);
        }
    } else if (r < TALL_OBSTACLE_PROBABILITY + (1.0f - TALL_OBSTACLE_PROBABILITY) / 2.0f) {
        obstacle.kind = OBSTACLE_GROUND;
        obstacle.row_mask = (uint8_t)(1u << GROUND_Y);
    } else {
        obstacle.kind = OBSTACLE_AIR;
        obstacle.row_mask = (uint8_t)(1u << HEAD_Y);
    }

    obstacle.x = MATRIX_WIDTH - 1;
    obstacle.is_visible = true;

    /* 初期生成時は加速しない */
    if (!initial) {
        obstacle_interval /= SPEEDUP_FACTOR;
        if (obstacle_interval < MIN_OBSTACLE_INTERVAL) {
            obstacle_interval = MIN_OBSTACLE_INTERVAL;
        }
    }
}

static void initialize(void) {
    is_running = true;
    score_shown = false;
    both_pressed_prev = false;

    is_jumping = false;
    jump_is_big = false;
    jump_start_ms = 0;
    jump_offset = 0;

    wall_x = -1;

    obstacle_interval = INITIAL_OBSTACLE_INTERVAL;
    score = 0;
    last_move_ms = now_ms();
    spawn_obstacle(true);

    update_score_display();
    audio_play(&SFX_START);
}

static bool is_crouching(void) {
    /* 赤ボタン (B) を押している間だけしゃがむ (ジャンプ中は不可) */
    return !is_jumping && btn_b_pressed();
}

/* 現在プレイヤーが占有するピクセルを返す。戻り値は個数 */
static int get_player_pixels(int ys[2]) {
    if (is_crouching()) {
        ys[0] = GROUND_Y; /* しゃがみ中は地面の 1 ピクセルのみ */
        return 1;
    }
    ys[0] = HEAD_Y - jump_offset;
    ys[1] = GROUND_Y - jump_offset;
    return 2;
}

static void check_collision(int x, uint8_t row_mask) {
    if (x != PLAYER_X) {
        return;
    }
    int ys[2];
    int count = get_player_pixels(ys);
    for (int i = 0; i < count; i++) {
        if (ys[i] >= 0 && (row_mask & (1u << ys[i]))) {
            is_running = false;
            return;
        }
    }
}

static void handle_input(void) {
    /* 緑ボタン (A) でジャンプ開始。このとき赤ボタン (B) を押していれば大ジャンプ */
    if (btn_a_fell() && !is_jumping) {
        jump_is_big = btn_b_pressed();
        is_jumping = true;
        jump_start_ms = now_ms();
        audio_play(jump_is_big ? &SFX_BIG_JUMP : &SFX_JUMP);
    } else if (btn_b_fell() && !is_jumping) {
        /* しゃがみ始めた瞬間だけ鳴らす (押しっぱなしの間は鳴らさない) */
        audio_play(&SFX_CROUCH);
    }
}

static void update_jump(void) {
    if (!is_jumping) {
        jump_offset = 0;
        return;
    }

    float frac = (float)(now_ms() - jump_start_ms) / (float)JUMP_DURATION_MS;
    if (frac >= 1.0f) {
        is_jumping = false;
        jump_offset = 0;
        return;
    }

    int max_offset = jump_is_big ? BIG_JUMP_MAX_OFFSET : NORMAL_JUMP_MAX_OFFSET;

    /* 三角波でジャンプの上昇・下降を表現する */
    float height = (frac < 0.5f) ? (frac / 0.5f) : ((1.0f - frac) / 0.5f);
    jump_offset = (int)((float)max_offset * height + 0.5f);
}

/*
 * 列 x に大ジャンプの逃げ場となる穴を開けるべきか。
 * TALL がいる列を中心に前後 TALL_GAP_MARGIN 列ぶん、壁があっても無視する。
 */
static bool is_tall_gap_at(int x) {
    if (!obstacle.is_visible || obstacle.kind != OBSTACLE_TALL) {
        return false;
    }
    int diff = obstacle.x - x;
    if (diff < 0) {
        diff = -diff;
    }
    return diff <= TALL_GAP_MARGIN;
}

static void move_wall(void) {
    if (wall_x >= 0) {
        wall_x--;
        if (wall_x < 0) {
            return;
        }
        /*
         * wall_pattern[j] は列 (wall_x - j) にいる。プレイヤーの列と重なっている
         * 区画があれば、その深さぶんだけ判定する (TALL の逃げ場は除く)。
         */
        for (int j = 0; j < WALL_PATTERN_WIDTH; j++) {
            int col = wall_x - j;
            if (col == PLAYER_X) {
                if (!is_tall_gap_at(col)) {
                    uint8_t mask = 0;
                    for (int y = 0; y < wall_pattern[j]; y++) {
                        mask |= (uint8_t)(1u << y);
                    }
                    check_collision(PLAYER_X, mask);
                }
                break;
            }
        }
        return;
    }

    if (rand_float() < WALL_SPAWN_CHANCE) {
        /*
         * 画面右端のさらに外側からスタートすることで、他の障害物と同様に
         * 1 列ずつ画面に入ってくるように見せる。
         */
        wall_x = MATRIX_WIDTH - 1 + (WALL_PATTERN_WIDTH - 1);
        for (int j = 0; j < WALL_PATTERN_WIDTH; j++) {
            wall_pattern[j] = 1 + (int)rand_below(CEILING_ROWS);
        }
    }
}

static void move_world(void) {
    uint32_t now = now_ms();
    if (now - last_move_ms < (uint32_t)(obstacle_interval * 1000.0f)) {
        return;
    }
    last_move_ms = now;

    /*
     * 判定はプレイヤーの列に進んできた瞬間の 1 回だけ行う。障害物・壁は次に動くまで
     * 同じ列に留まるため、毎フレーム判定するとジャンプ / しゃがみを滞在時間ぶん
     * ずっと維持しないと避けられなくなり、タイミングがシビアすぎる。
     */
    if (obstacle.is_visible) {
        obstacle.x--;
        if (obstacle.x < 0) {
            obstacle.is_visible = false;
        } else if (obstacle.x == PLAYER_X) {
            check_collision(obstacle.x, obstacle.row_mask);
        }
    }

    if (!obstacle.is_visible) {
        score++;
        update_score_display();
        audio_play(&SFX_SCORE);
        spawn_obstacle(false);
    }

    move_wall();
}

static void refresh(void) {
    matrix_fill(LED_OFF);

    if (obstacle.is_visible) {
        /*
         * 頭の高さは黄色、それ以外 (地面) は赤。TALL は両方点灯し、
         * 「ジャンプ + しゃがみの両方が要る」ことを示す。
         */
        for (int y = 0; y < MATRIX_HEIGHT; y++) {
            if (obstacle.row_mask & (1u << y)) {
                matrix_set(obstacle.x, y, (y == HEAD_Y) ? LED_YELLOW : LED_RED);
            }
        }
    }

    if (wall_x >= 0) {
        /* 洞窟の天井のように、列ごとに深さの違う鍾乳石を描く */
        for (int j = 0; j < WALL_PATTERN_WIDTH; j++) {
            int x = wall_x - j;
            if (x >= 0 && x < MATRIX_WIDTH && !is_tall_gap_at(x)) {
                for (int y = 0; y < wall_pattern[j]; y++) {
                    matrix_set(x, y, LED_RED);
                }
            }
        }
    }

    int ys[2];
    int count = get_player_pixels(ys);
    for (int i = 0; i < count; i++) {
        matrix_set(PLAYER_X, ys[i], LED_GREEN);
    }

    matrix_show();
}

static void show_game_over(void) {
    matrix_border(LED_RED);
    matrix_show();
    /* 衝突音はノイズ波形の下降スイープで「ドカン」と鳴らす */
    audio_play(&SFX_GAME_OVER);
}

static void update(void) {
    if (!is_running) {
        if (!score_shown) {
            score_shown = true;
            printf("Game over. score = %d\n\n", score);
            show_game_over();

            /*
             * 大ジャンプ (B を押しながら A) の失敗で衝突した場合、衝突した瞬間は
             * 両ボタンが押されたままになっている。このままだと「両方押されている
             * 状態への遷移」が即成立して意図せずリセットされてしまうため、
             * 一度両方離されるまでリセット判定を無効化する。
             */
            both_pressed_prev = true;
        }

        bool both_pressed = btn_a_pressed() && btn_b_pressed();
        if (both_pressed && !both_pressed_prev) {
            both_pressed_prev = both_pressed;
            initialize();
            return;
        }
        both_pressed_prev = both_pressed;
        return;
    }

    handle_input();
    update_jump();
    move_world();
    refresh();
}

static void pause_game(void) {
    pause_ms = now_ms();
    audio_stop_all();
}

static void resume_game(void) {
    /* 一時停止していた時間だけ障害物とジャンプのタイマーをずらす */
    uint32_t paused_for = now_ms() - pause_ms;
    last_move_ms += paused_for;
    if (is_jumping) {
        jump_start_ms += paused_for;
    }
}

static void finalize(void) {
    audio_stop_all();
    matrix_fill(LED_OFF);
    matrix_show();
    seg_text(NULL);
}

const game_t game_jump_runner = {
    .name = "JumpRunner",
    .initialize = initialize,
    .update = update,
    .finalize = finalize,
    .pause = pause_game,
    .resume = resume_game,
};
