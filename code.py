"""
Adafruit 902 (HT16K33 8x8 LEDマトリクス) を使い、
点が重力で跳ねる動きを表示するサンプル。
"""

import board
import busio
import time
from adafruit_ht16k33.matrix import Matrix8x8x2
from games.bouncing_ball import BouncingBallGame

FPS = 60  # フレームレート

# LEDマトリクス初期化
i2c = busio.I2C(board.GP17, board.GP16)
matrix = Matrix8x8x2(i2c)

# ここで他のゲームクラスも定義できる
# class AnotherGame(Game):
#     ...

# ゲーム切り替え用変数
GAME_LIST = [BouncingBallGame]
GAME_INDEX = 0  # ここを変更してゲームを切り替え


def main():
    game = GAME_LIST[GAME_INDEX](matrix)
    game.initialize()
    try:
        while True:
            start_time = time.monotonic()

            # ゲームの更新
            game.update()

            # フレームレート制御
            elapsed = time.monotonic() - start_time
            sleep_time = max(0, (1.0 / FPS) - elapsed)
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        pass
    finally:
        game.finalize()


if __name__ == "__main__":
    main()
