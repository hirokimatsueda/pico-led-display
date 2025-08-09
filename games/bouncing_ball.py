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

        def __init__(self, x, y, vx, width, height):
            self.x = x
            self.y = y
            self.vx = vx
            self.vy = -1
            self.g = 0.08
            self.width = width
            self.height = height

        def update(self):
            self.vy += self.g
            self.y += self.vy
            self.x += self.vx
            if self.x >= self.width - 1:
                self.x = self.width - 1
                self.vx = -self.vx
            elif self.x <= 0:
                self.x = 0
                self.vx = -self.vx
            if self.y >= self.height - 1:
                self.y = self.height - 1
                self.vy = -1

    def __init__(self, devices):
        super().__init__(devices)

    def initialize(self):
        self.ball = self.Ball(
            x=0,
            y=self.matrix_height - 1,
            vx=0.2,
            width=self.matrix_width,
            height=self.matrix_height,
        )
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)

    def update(self):
        # 画面をクリア
        self.matrix.fill(0)

        # 残像（前回位置）を表示
        self.matrix[self.prev_x, self.prev_y] = 3
        self.ball.update()

        # 現在位置を表示
        self.matrix[int(self.ball.x), int(self.ball.y)] = 1

        # 前回位置を更新
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)

        # ボタンの状態表示
        if self.button_a and not self.button_a.value:
            self.matrix[0, 0] = 2
        if self.button_b and not self.button_b.value:
            self.matrix[7, 0] = 2

        # 表示更新
        self.matrix.show()

    def finalize(self):
        self.matrix.fill(0)
        self.matrix.show()
