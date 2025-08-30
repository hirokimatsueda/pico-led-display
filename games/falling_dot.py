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
    プレイヤー (2x2緑) を左右ボタンで操作して避けるゲーム。
    衝突したら停止。
    """

    def __init__(self, devices):
        super().__init__(devices)

    def initialize(self):
        # ゲーム状態の初期化
        self.is_running = True

        # ゲーム終了時スコア表示済みフラグ
        self.score_shown = False

        # プレイヤー初期位置 (下中央)
        self.player_x = self.matrix_width // 2 - 1
        self.player_y = self.matrix_height - 2

        # 落下ドット (1個のみ)
        self.dot = None
        # ドット落下速度 (秒)
        self.dot_speed = 0.5
        # 避けたドット数
        self.dot_count = 0
        self.spawn_dot()

        # ドット落下タイマー
        self.last_drop_time = time.monotonic()

    def spawn_dot(self):
        # 新しいドットを生成 (1個のみ)
        self.dot = FallingDot(random.randint(0, self.matrix_width - 1), 0)
        # 新規生成ごとに速度を1.1で割る (加速)
        self.dot_speed /= 1.1
        # ゲーム開始直後はカウントしない
        if self.dot_count is not None:
            self.dot_count += 1

        # 7セグメントディスプレイをクリアして得点表示
        self._devices.seg.fill(0)  # 7セグメントディスプレイをクリア
        self._devices.seg.print(str(self.dot_count - 1))
        self._devices.seg.show()

    def update(self):
        # 一時停止中は更新処理をスキップ
        if self.is_paused:
            return

        m = self.matrix

        if not self.is_running:
            if not self.score_shown:
                self.score_shown = True

                print(f"Game over. score = {self.dot_count - 1}\n")
                # ゲームが終了している場合は赤枠を表示 (1回だけm.show)
                self.show_error()
                m.show()

            # 以降は何も表示しないが、ボタンクリックで再スタート可能
            self.btn_a.update()
            self.btn_b.update()
            if self.btn_a.fell and self.btn_b.fell:
                self.initialize()
            return

        # オブジェクトの位置更新
        obj_location_changed = self.move_objects()

        # 衝突判定 (表示中のドットのみ)
        if self.dot and self.dot.is_visible:
            for dx in range(2):
                for dy in range(2):
                    px = self.player_x + dx
                    py = self.player_y + dy
                    if px == self.dot.x and py == self.dot.y:
                        self.is_running = False

        # オブジェクトの位置が変わった場合のみ表示更新
        if obj_location_changed:
            self.refresh()

    def move_objects(self) -> bool:
        """オブジェクトの位置を更新し、必要ならば表示を更新する"""

        obj_location_changed = False

        # プレイヤー操作
        self.btn_a.update()
        if self.btn_a.fell:
            self.player_x = min(self.matrix_width - 2, self.player_x + 1)
            obj_location_changed = True

        self.btn_b.update()
        if self.btn_b.fell:
            self.player_x = max(0, self.player_x - 1)
            obj_location_changed = True

        # dot_speed秒ごとにドット落下
        now = time.monotonic()
        if now - self.last_drop_time >= self.dot_speed:
            self.last_drop_time = now
            if self.dot and self.dot.is_visible:
                self.dot.move(self.matrix_height)
            # 画面外に出たら新規生成
            if not self.dot.is_visible:
                self.spawn_dot()
            obj_location_changed = True

        # 移動したオブジェクトがあったかどうか返却する
        return obj_location_changed

    def refresh(self):
        """画面を更新してドットとプレイヤーを表示"""

        m = self.matrix

        # 画面をクリア
        m.fill(m.LED_OFF)

        # ドット表示
        if self.dot and self.dot.is_visible:
            m[self.dot.x, self.dot.y] = m.LED_YELLOW

        # プレイヤー表示 (2x2緑)
        for dx in range(2):
            for dy in range(2):
                px = self.player_x + dx
                py = self.player_y + dy
                if 0 <= px < self.matrix_width and 0 <= py < self.matrix_height:
                    m[px, py] = m.LED_GREEN

        # 表示更新
        m.show()

    def show_error(self):
        """ゲームオーバー時に赤枠を表示"""

        m = self.matrix

        # 外周に赤色を表示
        for x in range(self.matrix_width):
            m[x, 0] = m.LED_RED
            m[x, self.matrix_height - 1] = m.LED_RED
        for y in range(self.matrix_height):
            m[0, y] = m.LED_RED
            m[self.matrix_width - 1, y] = m.LED_RED

    def pause(self):
        """
        ゲームを一時停止

        ドットの落下とプレイヤーの動きを停止し、現在の表示状態を維持します。
        """
        super().pause()
        # ドットの落下タイマーを保存して、再開時に継続できるようにする
        if hasattr(self, "last_drop_time"):
            self._pause_time = time.monotonic()
        # LEDマトリクスと7セグメントディスプレイの表示は維持される

    def resume(self):
        """
        ゲームを再開

        ドットの落下とプレイヤーの動きを再開し、ゲーム状態を保持します。
        """
        super().resume()
        # 一時停止時間を考慮してタイマーを調整
        if hasattr(self, "_pause_time") and hasattr(self, "last_drop_time"):
            pause_duration = time.monotonic() - self._pause_time
            self.last_drop_time += pause_duration
            delattr(self, "_pause_time")

    def finalize(self):
        self.matrix.fill(self.matrix.LED_OFF)
        self.matrix.show()
