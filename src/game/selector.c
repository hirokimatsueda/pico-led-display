#include <stdio.h>

#include "game/selector.h"

typedef enum {
    MODE_NORMAL = 0,
    MODE_SELECTION = 1,
} selector_mode_t;

static const game_t *const *game_list;
static int game_count;
static selector_mode_t mode;

static const game_t *current_game;
static int current_index;
static int selected_index; /* 選択モードでハイライト中のインデックス */
static int32_t last_encoder_pos;

static bool game_is_valid(const game_t *game) {
    return game != NULL && game->initialize != NULL && game->update != NULL &&
           game->finalize != NULL;
}

static int32_t check_rotation(void) {
    int32_t position = encoder_pos();
    int32_t rotation = position - last_encoder_pos;
    if (rotation != 0) {
        last_encoder_pos = position;
    }
    return rotation;
}

static bool start_game(int index) {
    if (index < 0 || index >= game_count || !game_is_valid(game_list[index])) {
        printf("Invalid game index: %d\n", index);
        return false;
    }

    current_game = game_list[index];
    current_index = index;
    current_game->initialize();
    printf("Successfully initialized game: %s\n", current_game->name);
    return true;
}

static void finalize_current_game(void) {
    if (current_game != NULL) {
        current_game->finalize();
        current_game = NULL;
    }
}

static bool change_game(int index) {
    finalize_current_game();

    if (start_game(index)) {
        printf("Game changed to: %s\n", game_list[index]->name);
        return true;
    }

    /* 失敗した場合は動くゲームにフォールバックする */
    printf("Attempting to fallback to a working game...\n");
    for (int i = 0; i < game_count; i++) {
        if (start_game(i)) {
            printf("Successfully fell back to game: %s\n", game_list[i]->name);
            return false;
        }
    }
    printf("Error: All games failed to initialize\n");
    return false;
}

static void enter_selection_mode(void) {
    if (current_game != NULL && current_game->pause != NULL) {
        current_game->pause();
    }
    mode = MODE_SELECTION;
    selected_index = current_index;
    seg_selection(selected_index + 1);
}

static void exit_selection_mode(void) {
    mode = MODE_NORMAL;
    if (current_game != NULL && current_game->resume != NULL) {
        current_game->resume();
    }
    printf("Exited selection mode, current game index: %d\n", current_index);
}

void selector_init(const game_t *const *games, int count, int initial_index) {
    game_list = games;
    game_count = count;
    mode = MODE_NORMAL;
    current_game = NULL;
    current_index = 0;
    last_encoder_pos = encoder_pos();

    if (!start_game(initial_index)) {
        change_game(0);
    }
    selected_index = current_index;
}

void selector_update(void) {
    if (mode == MODE_NORMAL) {
        if (current_game != NULL) {
            current_game->update();
        }

        /* エンコーダーが回されたら選択モードに移る */
        if (check_rotation() != 0) {
            enter_selection_mode();
        }
        return;
    }

    /* --- 選択モード --- */
    int32_t rotation = check_rotation();
    if (rotation != 0) {
        /* 端まで行ったら反対側へ回り込む */
        selected_index = (selected_index + (rotation > 0 ? 1 : -1) + game_count) % game_count;
        seg_selection(selected_index + 1);
    }

    if (btn_a_fell()) {
        /* 確定 */
        if (!change_game(selected_index)) {
            selected_index = current_index;
            seg_selection(selected_index + 1);
            return;
        }
        exit_selection_mode();
    } else if (btn_b_fell()) {
        /* キャンセル: 一時停止していたゲームをそのまま再開する */
        selected_index = current_index;
        printf("Selection cancelled, returning to game index: %d\n", current_index);
        exit_selection_mode();
    }
}

void selector_finalize(void) { finalize_current_game(); }
