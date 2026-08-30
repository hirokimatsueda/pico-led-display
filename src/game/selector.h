/*
 * ゲームセレクター
 *
 * CircuitPython 版の GameSelector / GameManager / SelectionState をまとめたもの。
 * 2 モードの状態機械として動作する。
 *   通常モード  : 実行中のゲームの update() に委譲しつつエンコーダーを監視する
 *   選択モード  : エンコーダーでゲームを選び、A で確定 / B でキャンセルする
 * 選択モードに入っても現在のゲームは finalize されず一時停止するだけなので、
 * キャンセルすればそのまま続きから再開できる。
 */
#ifndef SELECTOR_H
#define SELECTOR_H

#include "game/game.h"

void selector_init(const game_t *const *games, int game_count, int initial_index);
void selector_update(void);
void selector_finalize(void);

#endif /* SELECTOR_H */
