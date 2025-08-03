"""
Adafruit 902 (HT16K33 8x8 LEDマトリクス) を使い、
点が重力で跳ねる動きを表示するサンプル。
"""

import board
import busio
import time
from adafruit_ht16k33.matrix import Matrix8x8x2

# LEDマトリクス初期化
i2c = busio.I2C(board.GP17, board.GP16)
matrix = Matrix8x8x2(i2c)


class Ball:
    """
    跳ねる点（ボール）を管理するクラス。

    Attributes:
        x (float): 横位置
        y (float): 縦位置
        vx (float): x方向速度
    """

    def __init__(self, x, y, vx):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = -1
        self.g = 0.08

    def update(self):
        """
        速度・座標を更新し、端で跳ね返る。
        """
        self.vy += self.g
        self.y += self.vy
        self.x += self.vx

        # 左右端で跳ね返り
        if self.x >= 7:
            self.x = 7
            self.vx = -self.vx
        elif self.x <= 0:
            self.x = 0
            self.vx = -self.vx

        # 床で跳ね返り（y=7）
        if self.y >= 7:
            self.y = 7
            self.vy = -1  # めりこみによる減速防止のため速度を固定


# ボールの初期化
ball = Ball(x=0, y=7, vx=0.2)

while True:
    # 画面クリア
    matrix.fill(0)

    # 残像（前回位置）を表示
    matrix[int(ball.x), int(ball.y)] = 3

    # 座標・速度の更新
    ball.update()

    # 現在位置の点を表示
    matrix[int(ball.x), int(ball.y)] = 1

    # 画面更新・待機
    matrix.show()
    time.sleep(0.05)
