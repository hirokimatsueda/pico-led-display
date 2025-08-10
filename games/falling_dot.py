import random
import time
from games.game_interface import Game


class FallingDot:
    """落下ドット管理クラス"""

    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y
        self._is_visible = True

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, value: int):
        self._x = value

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, value: int):
        self._y = value

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool):
        self._is_visible = value

    def move(self, height: int):
        self._y += 1
        if self._y >= height:
            self._is_visible = False


class FallingDotGame(Game):
    """
    上からランダムな位置にオレンジ色のドットが落ちてきて、
    プレイヤー（2x2緑）を左右ボタンで操作して避けるゲーム。
    衝突したら停止。
    """

    def __init__(self, devices):
        super().__init__(devices)

    def initialize(self):
        # ゲーム状態の初期化
        self.is_running = True

        # ゲーム終了時スコア表示済みフラグ
        self.score_shown = False

        # プレイヤー初期位置（下中央）
        self.player_x = self.matrix_width // 2 - 1
        self.player_y = self.matrix_height - 2

        # 落下ドット（1個のみ）
        self.dot = None
        # ドット落下速度（秒）
        self.dot_speed = 0.5
        # 避けたドット数
        self.dot_count = 0
        self.spawn_dot()

        # ドット落下タイマー
        self.last_drop_time = time.monotonic()

    def spawn_dot(self):
        # 新しいドットを生成（1個のみ）
        self.dot = FallingDot(random.randint(0, self.matrix_width - 1), 0)
        # 新規生成ごとに速度を1.1で割る（加速）
        self.dot_speed /= 1.1
        # ゲーム開始直後はカウントしない
        if self.dot_count is not None:
            self.dot_count += 1

    def update(self):
        m = self.matrix

        if not self.is_running:
            if not self.score_shown:
                self.score_shown = True

                print(f"Game over. score = {self.dot_count - 1}\n")
                # ゲームが終了している場合は得点を表示（1回だけm.show）
                m.fill(m.LED_OFF)
                self.show_count(self.dot_count - 1)  # 最初の生成分を除外
                m.show()
            # 以降は何も表示しない
            return

        # 画面をクリア
        m.fill(0)

        # プレイヤー操作
        if self.button_a and not self.button_a.value:
            self.player_x = max(0, self.player_x - 1)
        if self.button_b and not self.button_b.value:
            self.player_x = min(self.matrix_width - 2, self.player_x + 1)

        # dot_speed秒ごとにドット落下
        now = time.monotonic()
        if now - self.last_drop_time >= self.dot_speed:
            self.last_drop_time = now
            if self.dot and self.dot.is_visible:
                self.dot.move(self.matrix_height)
            # 画面外に出たら新規生成
            if not self.dot.is_visible:
                self.spawn_dot()

        # ドット表示
        if self.dot and self.dot.is_visible:
            m[self.dot.x, self.dot.y] = m.LED_YELLOW

        # プレイヤー表示（2x2緑）
        for dx in range(2):
            for dy in range(2):
                px = self.player_x + dx
                py = self.player_y + dy
                if 0 <= px < self.matrix_width and 0 <= py < self.matrix_height:
                    m[px, py] = m.LED_GREEN

        # 衝突判定（表示中のドットのみ）
        if self.dot and self.dot.is_visible:
            for dx in range(2):
                for dy in range(2):
                    px = self.player_x + dx
                    py = self.player_y + dy
                    if px == self.dot.x and py == self.dot.y:
                        self.is_running = False

        m.show()

    def show_count(self, count):
        m = self.matrix

        # 2桁の数字を3x5領域で表示（LED_GREEN）
        # 0-9のみ対応、各桁3x5で表示
        # 7セグメント風パターン（3x5）
        segment_patterns = {
            0: [
                [1, 1, 1],
                [1, 0, 1],
                [1, 0, 1],
                [1, 0, 1],
                [1, 1, 1],
            ],
            1: [
                [0, 1, 0],
                [0, 1, 1],
                [0, 1, 0],
                [0, 1, 0],
                [1, 1, 1],
            ],
            2: [
                [1, 1, 1],
                [1, 0, 0],
                [1, 1, 1],
                [0, 0, 1],
                [1, 1, 1],
            ],
            3: [
                [1, 1, 1],
                [1, 0, 0],
                [1, 1, 1],
                [1, 0, 0],
                [1, 1, 1],
            ],
            4: [
                [1, 0, 1],
                [1, 0, 1],
                [1, 1, 1],
                [1, 0, 0],
                [1, 0, 0],
            ],
            5: [
                [1, 1, 1],
                [0, 0, 1],
                [1, 1, 1],
                [1, 0, 0],
                [1, 1, 1],
            ],
            6: [
                [1, 1, 1],
                [0, 0, 1],
                [1, 1, 1],
                [1, 0, 1],
                [1, 1, 1],
            ],
            7: [
                [1, 1, 1],
                [1, 0, 0],
                [0, 1, 0],
                [0, 1, 0],
                [0, 1, 0],
            ],
            8: [
                [1, 1, 1],
                [1, 0, 1],
                [1, 1, 1],
                [1, 0, 1],
                [1, 1, 1],
            ],
            9: [
                [1, 1, 1],
                [1, 0, 1],
                [1, 1, 1],
                [1, 0, 0],
                [1, 1, 1],
            ],
        }
        # 2桁に丸める
        c = max(0, min(99, count))
        left = c % 10
        right = c // 10
        # 左桁（十の位）: x=0..2, y=0..4
        for j in range(5):
            for i in range(3):
                if segment_patterns[left][j][i]:
                    m[i, j] = m.LED_GREEN
        # 右桁（一の位）: x=4..6, y=0..4
        for j in range(5):
            for i in range(3):
                if segment_patterns[right][j][i]:
                    m[i + 4, j] = m.LED_GREEN

    def finalize(self):
        self.matrix.fill(0)
        self.matrix.show()
