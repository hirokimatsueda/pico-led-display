import time

import board
import rotaryio

from games.device_manager import DeviceManager
from games.selector import GameSelector

from games.bouncing_ball import BouncingBallGame
from games.falling_dot import FallingDotGame
from games.breakout import BreakoutGame

FPS = 50  # フレームレート

# ゲーム切り替え用変数
GAME_LIST = [BouncingBallGame, FallingDotGame, BreakoutGame]
GAME_INDEX = 2


def main():
    """
    Raspberry Pi Pico用のLEDディスプレイゲームのメインループ
    このスクリプトは、ゲームの初期化、更新、描画を行い、フレームレートを制御します。
    """

    # デバイス（LED, 7セグ, ボタン等）を初期化
    devices = DeviceManager()

    # ゲーム選択のためのロータリーエンコーダー初期化
    encoder = rotaryio.IncrementalEncoder(board.GP10, board.GP11)

    # GameSelectorを初期化
    game_selector = GameSelector(devices, encoder, GAME_LIST)
    game_selector.initialize()

    # 初期ゲームを設定（必要に応じて）
    if GAME_INDEX != 0:
        game_selector.game_manager.change_game(GAME_INDEX)

    try:
        while True:
            # ループ開始時刻を記録（フレームレート制御用）
            start_time = time.monotonic()

            # GameSelectorの更新処理（通常モードと選択モードの両方を処理）
            game_selector.update()

            # フレームレート維持のための待機時間計算
            elapsed = time.monotonic() - start_time
            sleep_time = max(0, (1.0 / FPS) - elapsed)
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        # シリアルモニターからCtrl+C等で終了した場合の処理
        pass
    finally:
        # ゲーム終了時の後処理（画面クリア等）
        if game_selector.game_manager.current_game:
            game_selector.game_manager.current_game.finalize()


if __name__ == "__main__":
    main()
