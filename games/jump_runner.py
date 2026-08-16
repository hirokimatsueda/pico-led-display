import random
import time
from games.game_interface import Game


class Obstacle:
    """スクロールしてくる障害物"""

    GROUND = "ground"  # 地上障害物 (緑ボタンでジャンプして回避)
    AIR = "air"  # 空中障害物 (赤ボタンでしゃがんで回避)
    TALL = "tall"  # プレイヤーの高さ全体を塞ぐ障害物 (しゃがみ+ジャンプの大ジャンプでのみ回避可)

    def __init__(self, kind: str, x: int, rows):
        self.kind = kind
        self.x = x
        self.rows = rows  # 占有するY座標のリスト
        self.is_visible = True

    def move(self):
        self.x -= 1
        if self.x < 0:
            self.is_visible = False


class JumpRunnerGame(Game):
    """
    横スクロールのジャンプアクションゲーム。
    プレイヤーは画面左寄りに固定され、右から流れてくる障害物を
    緑ボタン(ジャンプ)・赤ボタン(しゃがみ)で避け続ける。

    障害物は3種類:
    - GROUND (地面, 赤): 通常ジャンプで回避
    - AIR (頭の高さ, 黄): しゃがみで回避
    - TALL (全高, 赤+黄): しゃがみ中にジャンプする「大ジャンプ」でのみ回避可能

    加えて画面上部には、地上/空中の障害物とは完全に独立したタイミングで
    洞窟の天井のようなギザギザした「壁」がスクロールしてくる (赤、複数列)。
    列ごとに深さがランダムなので、大ジャンプ中にどこかの列の高さへ
    到達すると頭をぶつける。TALLが画面内にいる間は、TALLがいる列だけ
    壁に動的に穴が開き逃げ場になる (壁全体が消えるわけではない)。
    これにより、地上/空中の障害物が無いタイミングでも「大ジャンプで無駄に
    高く跳ばない」という制約が常に効くようになる。

    衝突したら停止。
    """

    PLAYER_X = 1  # プレイヤーのX座標 (固定)

    # 通常ジャンプ (Aのみ): 地上障害物のみクリアできる高さ
    NORMAL_JUMP_MAX_OFFSET = 3
    # 大ジャンプ (しゃがみ中にA): プレイヤー全高の障害物もクリアできる高さ
    BIG_JUMP_MAX_OFFSET = 6
    JUMP_DURATION = 0.45  # ジャンプ1回の所要時間 (秒、通常・大ジャンプ共通)

    JUMP_KIND_NORMAL = "normal"
    JUMP_KIND_BIG = "big"

    # 障害物1マス移動あたりの間隔。初期値は「安全にジャンプで避けられる時間」より
    # 短く設定し、加速してもジャンプの避けやすさが極端に損なわれないようにする。
    INITIAL_OBSTACLE_INTERVAL = 0.25
    MIN_OBSTACLE_INTERVAL = 0.12
    SPEEDUP_FACTOR = 1.08

    # 障害物出現時にTALL(プレイヤー全高)が選ばれる確率。他は地上/空中で等分。
    TALL_OBSTACLE_PROBABILITY = 0.15

    # 画面上部の壁が、待機中(壁がまだ無い)の1移動ステップごとに新規出現する確率。
    # 地上/空中の障害物とは別のタイミングで出したいので、障害物の生成とは独立に判定する。
    WALL_SPAWN_CHANCE = 0.2

    # 壁パターンの横幅 (列数)。列ごとに深さ(何マス下まで垂れ下がるか)を
    # ランダムに変えることで、洞窟の天井のようなギザギザした形にする。
    WALL_PATTERN_WIDTH = 4

    # TALLの逃げ場として壁に穴を開ける範囲 (TALLの列を中心に前後何列まで)。
    # 大ジャンプは開始から着地まで数ティックかかるため、TALLがちょうど
    # プレイヤーの列にいる瞬間だけ穴を開けても、その直前・直後のティックで
    # 別の壁区画に引っかかってしまうことがある。前後に余裕を持たせることで、
    # 大ジャンプの上昇〜下降の間ずっと安全な区間を確保する。
    TALL_GAP_MARGIN = 2

    def __init__(self, devices):
        super().__init__(devices)

    def initialize(self):
        # ゲーム状態の初期化
        self.is_running = True
        self.score_shown = False

        # 地面 / 頭の高さのY座標
        self.ground_y = self.matrix_height - 1
        self.head_y = self.matrix_height - 2

        # 画面上部の壁が占有するY座標。通常ジャンプの最高点より上、
        # つまり大ジャンプでしか届かない範囲にすることで、通常ジャンプ/しゃがみでは
        # 絶対にぶつからず、大ジャンプでのみ危険になるようにする。
        self.ceiling_rows = list(range(0, self.head_y - self.NORMAL_JUMP_MAX_OFFSET))

        # TALL障害物が占有するY座標。通常ジャンプの最高点(head_y - NORMAL_JUMP_MAX_OFFSET)
        # まで完全に塞ぐことで、通常ジャンプでは絶対に避けられないようにする。
        self.tall_rows = list(
            range(self.head_y - self.NORMAL_JUMP_MAX_OFFSET + 1, self.matrix_height)
        )

        # ゲームオーバー時のリセット判定 (両ボタン同時押し検出用)
        self._both_pressed_prev = False

        # ジャンプ状態
        self.is_jumping = False
        self.jump_start_time = 0.0
        self.jump_offset = 0
        self.jump_kind = self.JUMP_KIND_NORMAL

        # 画面上部の壁 (wall_xがNoneなら非表示)。地上/空中の障害物とは独立に出現する。
        # wall_patternは列ごとの深さのリストで、洞窟の天井のようなギザギザ形状を作る。
        # wall_x は wall_pattern[0] が現在いる列 (以降 wall_pattern[j] は wall_x - j の列)。
        self.wall_x = None
        self.wall_pattern = None

        # 障害物
        self.obstacle = None
        self.obstacle_interval = self.INITIAL_OBSTACLE_INTERVAL
        self.score = 0
        self.last_move_time = time.monotonic()
        self.spawn_obstacle(initial=True)

        self.update_score_display()

    def spawn_obstacle(self, initial: bool = False):
        # 新しい障害物を生成 (地上 / 空中 / まれにプレイヤー全高)
        r = random.random()
        if r < self.TALL_OBSTACLE_PROBABILITY:
            kind = Obstacle.TALL
            rows = self.tall_rows
            # 壁自体は消さない。TALLがいる列だけ動的に穴を開ける
            # (is_tall_gap_at参照) ことで、壁がいきなり消える不自然さを避ける。
        elif r < self.TALL_OBSTACLE_PROBABILITY + (
            1.0 - self.TALL_OBSTACLE_PROBABILITY
        ) / 2:
            kind = Obstacle.GROUND
            rows = [self.ground_y]
        else:
            kind = Obstacle.AIR
            rows = [self.head_y]

        self.obstacle = Obstacle(kind, self.matrix_width - 1, rows)

        # 初期生成時は加速しない
        if not initial:
            self.obstacle_interval = max(
                self.MIN_OBSTACLE_INTERVAL,
                self.obstacle_interval / self.SPEEDUP_FACTOR,
            )

    def update_score_display(self):
        self._devices.show_text(str(self.score))

    def update(self):
        # 一時停止中は更新処理をスキップ
        if self.is_paused:
            return

        if not self.is_running:
            if not self.score_shown:
                self.score_shown = True
                print(f"Game over. score = {self.score}\n")
                self.show_game_over()

                # 大ジャンプ (Bを押しながらA) の失敗で衝突した場合、
                # 衝突した瞬間は両ボタンがまだ押されたままになっている。
                # このままだと「両方押されている状態への遷移」が即成立して
                # 意図せず即リセットされてしまうため、ゲームオーバーに
                # 入った直後は一度両方離されるまでリセット判定を無効化する。
                self._both_pressed_prev = True

            # 以降は何も表示しないが、両ボタン同時押しで再スタート可能。
            # fell同士 (押した瞬間) の一致で判定すると、両ボタンの押下が
            # 同一フレームに揃わない限りリセットされずタイミングがシビアに
            # なるため、代わりに「両方押されている」状態への遷移で判定する。
            self.btn_a.update()
            self.btn_b.update()
            both_pressed = not self.btn_a.value and not self.btn_b.value
            if both_pressed and not self._both_pressed_prev:
                self._both_pressed_prev = both_pressed
                self.initialize()
                return
            self._both_pressed_prev = both_pressed
            return

        self.handle_input()
        self.update_jump()
        self.move_world()
        self.refresh()

    def handle_input(self):
        self.btn_a.update()
        self.btn_b.update()

        # 緑ボタン (A) でジャンプ開始 (ジャンプ中は不可)
        # このとき赤ボタン (B) を押していれば大ジャンプになる
        if self.btn_a.fell and not self.is_jumping:
            crouch_held = not self.btn_b.value
            self.jump_kind = (
                self.JUMP_KIND_BIG if crouch_held else self.JUMP_KIND_NORMAL
            )
            self.is_jumping = True
            self.jump_start_time = time.monotonic()

    def is_crouching(self) -> bool:
        # 赤ボタン (B) を押している間だけしゃがむ (ジャンプ中は不可)
        return not self.is_jumping and not self.btn_b.value

    def update_jump(self):
        if not self.is_jumping:
            self.jump_offset = 0
            return

        elapsed = time.monotonic() - self.jump_start_time
        frac = elapsed / self.JUMP_DURATION

        if frac >= 1.0:
            self.is_jumping = False
            self.jump_offset = 0
            return

        max_offset = (
            self.BIG_JUMP_MAX_OFFSET
            if self.jump_kind == self.JUMP_KIND_BIG
            else self.NORMAL_JUMP_MAX_OFFSET
        )

        # 三角波でジャンプの上昇・下降を表現
        if frac < 0.5:
            self.jump_offset = round(max_offset * (frac / 0.5))
        else:
            self.jump_offset = round(max_offset * ((1.0 - frac) / 0.5))

    def move_world(self):
        now = time.monotonic()
        if now - self.last_move_time < self.obstacle_interval:
            return
        self.last_move_time = now

        # 判定はプレイヤーの列に進んできた瞬間の1回だけ行う。
        # 障害物/壁は次に動くまでの間ずっと同じ列に留まるため、
        # 毎フレーム判定するとジャンプ/しゃがみを滞在時間ぶんずっと
        # 維持しないと避けられなくなり、タイミングがシビアすぎる。

        if self.obstacle and self.obstacle.is_visible:
            self.obstacle.move()
            if self.obstacle.is_visible and self.obstacle.x == self.PLAYER_X:
                self.check_collision(self.obstacle.x, self.obstacle.rows)

        if not self.obstacle.is_visible:
            self.score += 1
            self.update_score_display()
            self.spawn_obstacle()

        self.move_wall()

    def is_tall_gap_at(self, x: int) -> bool:
        """
        列xに大ジャンプの逃げ場となる穴を開けるべきかどうか。

        TALL障害物が今いる列を中心に前後TALL_GAP_MARGIN列ぶん、壁があっても
        その部分だけ無視する。大ジャンプは上昇〜下降に数ティックかかるため、
        TALLがちょうどプレイヤーの列にいる瞬間だけ穴を開けても不十分で、
        前後にも余裕を持たせる必要がある。壁パターン全体を消すのではなく
        穴だけ動的に開けることで、TALLが来るたびに壁がまるごと消える
        不自然さも無くしている。
        """
        return (
            self.obstacle is not None
            and self.obstacle.kind == Obstacle.TALL
            and abs(self.obstacle.x - x) <= self.TALL_GAP_MARGIN
        )

    def move_wall(self):
        # 画面上部の壁は地上/空中の障害物とは独立したタイミングで出現・移動する。
        if self.wall_x is not None:
            self.wall_x -= 1
            if self.wall_x < 0:
                self.wall_x = None
                self.wall_pattern = None
            else:
                # wall_pattern[j] は列 (wall_x - j) にいる。プレイヤーの列と
                # 重なっている区画があれば、その深さぶんだけ判定する
                # (TALLの逃げ場になっている列は除く)。
                for j, depth in enumerate(self.wall_pattern):
                    col = self.wall_x - j
                    if col == self.PLAYER_X:
                        if not self.is_tall_gap_at(col):
                            self.check_collision(
                                self.PLAYER_X, self.ceiling_rows[:depth]
                            )
                        break
        elif random.random() < self.WALL_SPAWN_CHANCE:
            # 画面右端のさらに外側からスタートすることで、他の障害物と同様に
            # 1列ずつ画面に入ってくるように見せる (先頭からいきなり
            # WALL_PATTERN_WIDTH列ぶん出現すると唐突に見えるため)。
            self.wall_x = self.matrix_width - 1 + (self.WALL_PATTERN_WIDTH - 1)
            self.wall_pattern = [
                random.randint(1, len(self.ceiling_rows))
                for _ in range(self.WALL_PATTERN_WIDTH)
            ]

    def get_player_pixels(self):
        """現在のプレイヤーが占有するピクセル座標のリストを返す"""

        if self.is_crouching():
            # しゃがみ中は地面の1ピクセルのみ
            return [(self.PLAYER_X, self.ground_y)]

        offset = self.jump_offset
        return [
            (self.PLAYER_X, self.head_y - offset),
            (self.PLAYER_X, self.ground_y - offset),
        ]

    def check_collision(self, x: int, rows):
        player_pixels = self.get_player_pixels()
        for y in rows:
            if (x, y) in player_pixels:
                self.is_running = False
                return

    def refresh(self):
        """画面を更新して障害物とプレイヤーを表示"""

        m = self.matrix
        m.fill(m.LED_OFF)

        if self.obstacle and self.obstacle.is_visible:
            # 頭の高さは黄色、それ以外(地面)は赤で表示。
            # TALLは地面(赤)と頭の高さ(黄)が両方点灯し、
            # 「ジャンプ(赤を回避)+しゃがみ(黄を回避)の両方が要る」ことを示す。
            for y in self.obstacle.rows:
                color = m.LED_YELLOW if y == self.head_y else m.LED_RED
                m[self.obstacle.x, y] = color

        if self.wall_x is not None:
            # 洞窟の天井のように、列ごとに深さの違う「鍾乳石」を描画する。
            # TALLの逃げ場になっている列は穴として空けておく。
            for j, depth in enumerate(self.wall_pattern):
                x = self.wall_x - j
                if 0 <= x < self.matrix_width and not self.is_tall_gap_at(x):
                    for y in self.ceiling_rows[:depth]:
                        m[x, y] = m.LED_RED

        for x, y in self.get_player_pixels():
            if 0 <= x < self.matrix_width and 0 <= y < self.matrix_height:
                m[x, y] = m.LED_GREEN

        m.show()

    def show_game_over(self):
        """ゲームオーバー時に赤枠を表示"""

        self._devices.show_border(self.matrix.LED_RED)
        self.matrix.show()

    def pause(self):
        """
        ゲームを一時停止

        障害物の移動とジャンプの経過時間を停止し、現在の表示状態を維持します。
        """
        super().pause()
        self._pause_time = time.monotonic()

    def resume(self):
        """
        ゲームを再開

        一時停止していた時間を考慮して、障害物とジャンプのタイマーを調整します。
        """
        super().resume()
        if hasattr(self, "_pause_time"):
            pause_duration = time.monotonic() - self._pause_time
            self.last_move_time += pause_duration
            if self.is_jumping:
                self.jump_start_time += pause_duration
            delattr(self, "_pause_time")

    def finalize(self):
        self.matrix.fill(self.matrix.LED_OFF)
        self.matrix.show()
        self._devices.show_text()
