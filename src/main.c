/*
 * Raspberry Pi Pico 2 WH 用 LED ディスプレイゲームのメインループ
 *
 * FPS = 50 の固定タイムステップで、毎フレーム「入力更新 -> ゲーム更新」を行い、
 * 次フレームの時刻まで sleep する。
 *
 * 効果音はここには出てこない。DMA と割り込みが裏で鳴らし続けるため、
 * CircuitPython 版で必要だった毎フレームの sound.update() が不要になっている。
 */
#include <stdio.h>

#include "device/device_manager.h"
#include "game/games.h"
#include "game/selector.h"
#include "pico/stdlib.h"

#define FPS 50
#define INITIAL_GAME_INDEX 4

/* 実行可能なゲームのレジストリ。ゲームを追加したらここに並べる */
static const game_t *const GAME_LIST[] = {
    &game_bouncing_ball, &game_falling_dot, &game_block_breaker, &game_bomb_defuse, &game_jump_runner,
};
#define GAME_COUNT ((int)(sizeof(GAME_LIST) / sizeof(GAME_LIST[0])))

int main(void) {
    stdio_init_all();

    devices_init();
    selector_init(GAME_LIST, GAME_COUNT, INITIAL_GAME_INDEX);

    const int64_t frame_us = 1000000 / FPS;
    absolute_time_t next_frame = get_absolute_time();

    while (true) {
        next_frame = delayed_by_us(next_frame, frame_us);

        devices_update_inputs();
        selector_update();

        /* フレーム予算の残り時間ぶん待つ (処理が長引いた場合は即座に次へ進む) */
        sleep_until(next_frame);
    }
}
