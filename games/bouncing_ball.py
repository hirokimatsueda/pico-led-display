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
        self.btn_a_toggle = True
        self.btn_b_toggle = True

    def update(self):
        # 一時停止中は更新処理をスキップ（要件6.2）
        if self.is_paused:
            return

        # 画面をクリア
        self.matrix.fill(self.matrix.LED_OFF)

        # 残像（前回位置）を表示
        self.matrix[self.prev_x, self.prev_y] = self.matrix.LED_YELLOW
        self.ball.update()

        # 現在位置を表示
        self.matrix[int(self.ball.x), int(self.ball.y)] = self.matrix.LED_RED

        # 前回位置を更新
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)

        # ボタンの状態表示
        self.btn_a.update()
        if self.btn_a.fell:
            self.btn_a_toggle = not self.btn_a_toggle

        self.btn_b.update()
        if self.btn_b.fell:
            self.btn_b_toggle = not self.btn_b_toggle

        self.matrix[0, 0] = (
            self.matrix.LED_GREEN if self.btn_a_toggle else self.matrix.LED_OFF
        )
        self.matrix[7, 0] = (
            self.matrix.LED_GREEN if self.btn_b_toggle else self.matrix.LED_OFF
        )

        # 表示更新
        self.matrix.show()

    def pause(self):
        """
        ゲームを一時停止

        ボールの動きを停止し、現在の表示状態を維持します。
        """
        super().pause()
        # ボールの動きを停止するため、現在の状態を保存
        # LEDマトリクスの表示は維持される（要件6.3）

    def resume(self):
        """
        ゲームを再開

        ボールの動きを再開し、ゲーム状態を保持します。
        """
        super().resume()
        # ゲーム状態は保持される（要件6.4）
        # ボールの位置や速度などの状態は変更されない

    def finalize(self):
        self.matrix.fill(self.matrix.LED_OFF)
        self.matrix.show()
