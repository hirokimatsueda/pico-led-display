from .game_interface import Game


class BouncingBallGame(Game):
    class Ball:
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

    def initialize(self):
        self.ball = self.Ball(x=0, y=7, vx=0.2)
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)

    def update(self):
        self.matrix.fill(0)
        # 残像（前回位置）
        self.matrix[self.prev_x, self.prev_y] = 3
        self.ball.update()
        # 現在位置
        self.matrix[int(self.ball.x), int(self.ball.y)] = 1
        self.prev_x = int(self.ball.x)
        self.prev_y = int(self.ball.y)
        self.matrix.show()

    def finalize(self):
        self.matrix.fill(0)
        self.matrix.show()
