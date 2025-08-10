import time
from games.device_manager import DeviceManager

from games.bouncing_ball import BouncingBallGame
from games.falling_dot import FallingDotGame

FPS = 50  # フレームレート

# ゲーム切り替え用変数
GAME_LIST = [BouncingBallGame, FallingDotGame]
GAME_INDEX = 1  # ここを変更してゲームを切り替え


def main():
    """
    Raspberry Pi Pico用のLEDディスプレイゲームのメインループ
    このスクリプトは、ゲームの初期化、更新、描画を行い、フレームレートを制御します。
    """

    # デバイス（LED, 7セグ, ボタン等）を初期化
    devices = DeviceManager()

    # 選択されたゲームのインスタンスを生成
    game = GAME_LIST[GAME_INDEX](devices)

    # ゲームの初期化処理（画面や内部状態のリセット等）
    game.initialize()
    try:
        while True:
            # ループ開始時刻を記録（フレームレート制御用）
            start_time = time.monotonic()

            # ゲームの状態更新・描画
            game.update()

            # フレームレート維持のための待機時間計算
            elapsed = time.monotonic() - start_time
            sleep_time = max(0, (1.0 / FPS) - elapsed)
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        # シリアルモニターからCtrl+C等で終了した場合の処理
        pass
    finally:
        # ゲーム終了時の後処理（画面クリア等）
        game.finalize()


if __name__ == "__main__":
    main()
