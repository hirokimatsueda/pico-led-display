from games.game_interface import Game


class BouncingBallGame(Game):
    """
    ボールが跳ねるゲーム
    """

    class Ball:
        """
        ボールのクラス
        ボールの位置と速度を管理し、重力の影響を受けて跳ねる動きを実装します。
        """

        def __init__(self, x, y, vx):
            self.x = x
            self.y = y
            self.vx = vx
            self.vy = -1
            self.g = 0.08

        def update(self):
            self.vy += self.g
            self.y += self.vy
            self.x += self.vx
            if self.x >= 7:
                self.x = 7
                self.vx = -self.vx
            elif self.x <= 0:
                self.x = 0
                self.vx = -self.vx
            if self.y >= 7:
                self.y = 7
                self.vy = -1

    def __init__(self, devices):
        super().__init__(devices)

    def initialize(self):
        self.ball = self.Ball(x=0, y=7, vx=0.2)
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)

    def update(self):
        # 画面をクリア
        self.devices.matrix.fill(0)

        # 残像（前回位置）を表示
        self.devices.matrix[self.prev_x, self.prev_y] = 3
        self.ball.update()

        # 現在位置を表示
        self.devices.matrix[int(self.ball.x), int(self.ball.y)] = 1

        # 前回位置を更新
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)

        # ボタンの状態表示
        if self.devices.button_a and not self.devices.button_a.value:
            self.devices.matrix[0, 0] = 2
        if self.devices.button_b and not self.devices.button_b.value:
            self.devices.matrix[7, 0] = 2

        # 表示更新
        self.devices.matrix.show()

    def finalize(self):
        self.devices.matrix.fill(0)
        self.devices.matrix.show()
