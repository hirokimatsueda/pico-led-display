from games.game_interface import Game


class BreakoutGame(Game):
    """
    ブロック崩しゲーム
    プレイヤーは2つのボタンでパドルを操作し、オレンジ色のボールでブロックを破壊する
    クラシックなアーケードゲーム
    """

    class Paddle:
        """パドルクラス - プレイヤーが操作する緑色の3ドットパドル"""

        def __init__(self):
            self.x = 3  # 中央位置（画面幅8の中央）
            self.y = 7  # 最下行に固定
            self.width = 3  # パドル幅（3ドット）

        def move_left(self):
            """パドルを左に1ピクセル移動（画面端制限あり）"""
            if self.x > 1:  # 左端制限（3ドットパドルの左端が画面内に収まる）
                self.x -= 1

        def move_right(self):
            """パドルを右に1ピクセル移動（画面端制限あり）"""
            if self.x < 6:  # 右端制限（3ドットパドルの右端が画面内に収まる）
                self.x += 1

        def get_positions(self):
            """パドルの3ドットの座標を取得（最適化版）"""
            # タプルを直接返すことでリスト作成のオーバーヘッドを削減
            return ((self.x - 1, self.y), (self.x, self.y), (self.x + 1, self.y))

        def get_bounce_angle(self, ball_x):
            """ボール反射角度計算 - パドルの当たった位置による角度変化"""
            # パドル中央からの相対位置 (-1, 0, +1)
            relative_pos = ball_x - self.x
            # 角度係数 (-0.5, 0, +0.5)
            angle_factor = relative_pos * 0.5
            return angle_factor

    class Ball:
        """ボールクラス - オレンジ色の1ドットボール"""

        def __init__(self):
            self.x = 3.0  # X座標（float for smooth movement）
            self.y = 6.0  # Y座標（パドルの上に初期配置）
            self.vx = 0.125  # X方向速度
            self.vy = -0.125  # Y方向速度（上向き）
            self.speed = 0.125  # 基本速度

        def update(self):
            """ボール位置更新"""
            self.x += self.vx
            self.y += self.vy

        def bounce_horizontal(self):
            """水平方向の反射（左右の壁衝突時）"""
            self.vx = -self.vx

        def bounce_vertical(self):
            """垂直方向の反射（上壁、パドル、ブロック衝突時）"""
            self.vy = -self.vy

        def reset_position(self, paddle_x):
            """ボールをパドルの上に配置（ゲーム開始時）"""
            self.x = float(paddle_x)
            self.y = 6.0  # パドル（Y=7）の上
            self.vx = 0.125  # 右上方向に初期速度設定
            self.vy = -0.125  # 上向き

    class Block:
        """ブロッククラス - 破壊可能な赤色の1ドットブロック"""

        def __init__(self, x, y):
            self.x = x  # X座標
            self.y = y  # Y座標
            self.is_active = True  # ブロックの状態（True=存在、False=破壊済み）

        def destroy(self):
            """ブロックを破壊（非アクティブ化）"""
            self.is_active = False

        def is_at_position(self, x, y):
            """指定された位置にこのブロックが存在するかチェック"""
            return self.is_active and self.x == int(x) and self.y == int(y)

    def __init__(self, devices):
        super().__init__(devices)
        # メモリ最適化: 事前に計算済みの値をキャッシュ
        self._paddle_positions_cache = None
        self._last_paddle_x = None

        # 描画最適化フラグ
        self._force_full_refresh = False

    def initialize(self):
        """ゲーム初期化処理"""
        # ゲーム状態の初期化
        self.is_running = True
        self.score_shown = False
        self.score = 0
        self.game_state = "playing"  # "playing", "game_over", "game_clear"

        # パドル初期配置（画面下部中央、Y=7）
        self.paddle = self.Paddle()
        self._last_paddle_x = self.paddle.x
        self._paddle_positions_cache = None

        # ブロック配置システム（上部3行、Y=0,1,2に24個のブロック）
        # メモリ最適化: リスト内包表記を使用してメモリ効率を向上
        self.blocks = [self.Block(x, y) for y in range(3) for x in range(8)]

        # ボール初期配置（パドルの上に配置、初期速度設定）
        self.ball = self.Ball()
        self.ball.reset_position(self.paddle.x)

        # スコア表示初期化
        self._update_score_display()

        # 初期画面描画
        self._force_full_refresh = True
        self.refresh()

    def update(self):
        """ゲームループ処理"""
        if not self.is_running:
            # ゲーム終了時の処理
            if not self.score_shown:
                self.score_shown = True
                # ゲーム終了表示を実装
                self._show_game_end_display()

            # ゲーム再開始処理 - 両ボタン同時押し検出
            self._handle_restart_input()
            return

        # ボタン入力処理
        button_input_processed = self._handle_paddle_input_optimized()

        # オブジェクト位置変化検出 - 要件6.1, 6.2
        objects_moved = self._move_objects_optimized()

        # 衝突判定
        collision_occurred = self.check_collisions()

        # ゲーム終了条件チェック
        self._check_game_end_conditions()

        # スコア表示更新（変化時のみ）
        if collision_occurred:  # ブロック破壊時のみスコア更新
            self._update_score_display()

        # 変化時のみ画面更新実行 - 要件6.1, 6.2, 6.3
        # オブジェクトの画面上の位置変化または衝突（ブロック破壊等）時に画面更新
        if (
            objects_moved
            or collision_occurred
            or button_input_processed
            or self._force_full_refresh
        ):
            self.refresh()
            self._force_full_refresh = False

    def _handle_paddle_input_optimized(self):
        """最適化されたパドル操作の入力処理（応答性向上）"""
        # ボタン状態を更新（デバウンス処理）
        self.btn_a.update()
        self.btn_b.update()

        paddle_moved = False
        prev_x = self.paddle.x

        # ボタンA押下でパドル左移動（画面端制限あり）
        if self.btn_a.fell:
            self.paddle.move_left()
            paddle_moved = self.paddle.x != prev_x

        # ボタンB押下でパドル右移動（画面端制限あり）
        if self.btn_b.fell:
            self.paddle.move_right()
            paddle_moved = self.paddle.x != prev_x

        # パドル位置キャッシュの更新
        if paddle_moved:
            self._last_paddle_x = self.paddle.x
            self._paddle_positions_cache = None  # キャッシュを無効化

        return paddle_moved

    def _handle_restart_input(self):
        """ゲーム再開始の入力処理（両ボタン同時押し検出）"""
        # ボタン状態を更新
        self.btn_a.update()
        self.btn_b.update()

        # 両ボタンが同時に押された場合（同じフレームでfellが検出）
        if self.btn_a.fell and self.btn_b.fell:
            self._reset_game_state()

    def _reset_game_state(self):
        """ゲーム状態リセット処理"""
        # ゲーム状態を初期化してゲームを再開始
        self.initialize()

    def _move_ball(self):
        """ボール移動処理 - フレームごとの位置更新"""
        # 速度ベクトルによる移動計算
        self.ball.update()

    def _check_wall_collisions(self):
        """壁衝突判定処理"""
        collision_occurred = False

        # 左右壁での水平反射
        if self.ball.x <= 0 or self.ball.x >= 7:
            self.ball.bounce_horizontal()
            collision_occurred = True
            # 境界内に位置を修正
            if self.ball.x <= 0:
                self.ball.x = 0
            else:
                self.ball.x = 7

        # 上壁での垂直反射
        if self.ball.y <= 0:
            self.ball.bounce_vertical()
            self.ball.y = 0
            collision_occurred = True

        # 下端到達でのゲームオーバー判定
        if self.ball.y >= 8:
            self.game_state = "game_over"
            self.is_running = False
            collision_occurred = True

        return collision_occurred

    def _check_paddle_collision(self):
        """パドル衝突判定処理"""
        # ボールがパドルの高さ（Y=7）に到達し、下向きに移動している場合
        if (
            self.ball.y >= 7
            and self.ball.vy > 0
            and self.ball.x >= self.paddle.x - 1
            and self.ball.x <= self.paddle.x + 1
        ):
            # 垂直方向の反射
            self.ball.bounce_vertical()

            # 反射位置による角度変化計算
            angle_factor = self.paddle.get_bounce_angle(self.ball.x)

            # 速度ベクトルの更新（X方向の速度を角度に応じて調整）
            self.ball.vx = self.ball.speed * angle_factor
            # Y方向は上向きに固定
            self.ball.vy = -abs(self.ball.vy)

            # ボール位置をパドルの上に修正
            self.ball.y = 6.0

            return True

        return False

    def _check_block_collisions(self):
        """ブロック衝突判定処理"""
        ball_x = int(self.ball.x)  # round()よりint()が高速
        ball_y = int(self.ball.y)

        # 最適化: 範囲外チェックを先に実行
        if ball_x < 0 or ball_x >= 8 or ball_y < 0 or ball_y >= 3:
            return False

        # アクティブブロックのみ判定（最適化: 早期終了）
        for block in self.blocks:
            if block.is_active and block.x == ball_x and block.y == ball_y:
                # 衝突時のブロック破壊処理
                block.destroy()

                # ボールの垂直方向の速度が反転
                self.ball.bounce_vertical()

                # スコア増加（要件5.2: ブロックが破壊されたときスコアが1増加）
                self.score += 1

                # 1フレームで複数ブロック破壊を防ぐため、最初の衝突で処理終了
                return True

        return False

    def _check_game_end_conditions(self):
        """ゲーム終了条件チェック処理"""
        # 全ブロック破壊でのクリア判定（要件4.2）
        # 最適化: リスト内包表記を避けて、直接カウント
        active_count = 0
        for block in self.blocks:
            if block.is_active:
                active_count += 1
                if active_count > 0:  # 早期終了: 1つでもアクティブなら継続
                    return

        # 全ブロック破壊
        self.game_state = "game_clear"
        self.is_running = False

    def _update_score_display(self):
        """スコア表示更新処理（7セグメントディスプレイ）"""
        # 7セグメントディスプレイに破壊したブロック数を表示
        self._devices.seg.fill(0)  # ディスプレイをクリア
        self._devices.seg.print(str(self.score))  # スコアを文字列として表示
        self._devices.seg.show()  # 表示を更新

    def _show_game_end_display(self):
        """ゲーム終了表示処理（要件4.4, 5.4）"""
        # 画面をクリア
        self.matrix.fill(self.matrix.LED_OFF)

        if self.game_state == "game_clear":
            # ゲームクリア時の表示
            print(f"Game Clear! Score: {self.score}")
            # クリア時は緑色で画面全体を点滅させる
            self._show_clear_pattern()
        elif self.game_state == "game_over":
            # ゲームオーバー時の表示
            print(f"Game Over! Score: {self.score}")
            # ゲームオーバー時は赤色で画面全体を点滅させる
            self._show_game_over_pattern()

        # 最終スコア表示（7セグメントディスプレイ）
        self._show_final_score()

        # 画面を更新
        self.matrix.show()

    def _show_clear_pattern(self):
        """ゲームクリア時の画面表示パターン"""
        # 緑色で画面全体を点灯（クリア表示）
        for y in range(8):
            for x in range(8):
                self.matrix.pixel(x, y, self.matrix.LED_GREEN)

    def _show_game_over_pattern(self):
        """ゲームオーバー時の画面表示パターン"""
        # 赤色で画面全体を点灯（ゲームオーバー表示）
        for y in range(8):
            for x in range(8):
                self.matrix.pixel(x, y, self.matrix.LED_RED)

    def _show_final_score(self):
        """ゲーム終了時の最終スコア表示"""
        # 7セグメントディスプレイに最終スコアを表示
        self._devices.seg.fill(0)
        self._devices.seg.print(str(self.score))
        self._devices.seg.show()

    def _move_objects_optimized(self):
        """最適化されたオブジェクト位置変化検出システム"""
        objects_moved = False

        # 前回の画面上の位置を保存（ピクセル単位での変化検出用）
        prev_ball_pixel_x = int(self.ball.x)  # round()よりint()が高速
        prev_ball_pixel_y = int(self.ball.y)

        # 物理演算 - ボール移動処理（入力処理は別途高頻度で実行）
        self._move_ball()

        # ボールの画面上のピクセル位置変化チェック（最適化版）
        current_ball_pixel_x = int(self.ball.x)
        current_ball_pixel_y = int(self.ball.y)
        if (
            current_ball_pixel_x != prev_ball_pixel_x
            or current_ball_pixel_y != prev_ball_pixel_y
        ):
            objects_moved = True

        return objects_moved

    def check_collisions(self):
        """衝突判定システム統合"""
        # 壁衝突判定
        wall_collision = self._check_wall_collisions()

        # パドル衝突判定
        paddle_collision = self._check_paddle_collision()

        # ブロック衝突判定
        block_collision = self._check_block_collisions()

        # 衝突があった場合は画面更新が必要
        return wall_collision or paddle_collision or block_collision

    def refresh(self):
        """画面描画システム - 最適化されたオブジェクト描画"""
        # 画面をクリア
        self.matrix.fill(self.matrix.LED_OFF)

        # ブロック描画（赤色1ドット）- 要件3.2, 3.3
        # 最適化: アクティブブロックのみを効率的に描画
        led_red = self.matrix.LED_RED  # 定数の事前取得
        for block in self.blocks:
            if block.is_active:
                self.matrix[block.x, block.y] = led_red

        # パドル描画（緑色3ドット）- 要件1.5
        # 最適化: キャッシュされた位置を使用
        if self._paddle_positions_cache is None or self._last_paddle_x != self.paddle.x:
            self._paddle_positions_cache = self.paddle.get_positions()
            self._last_paddle_x = self.paddle.x

        led_green = self.matrix.LED_GREEN  # 定数の事前取得
        for x, y in self._paddle_positions_cache:
            # パドルは常に画面内なので範囲チェック不要（最適化）
            self.matrix[x, y] = led_green

        # ボール描画（オレンジ色1ドット）- 要件2.1
        ball_x = int(self.ball.x)  # round()よりint()が高速
        ball_y = int(self.ball.y)
        if 0 <= ball_x < 8 and 0 <= ball_y < 8:  # 画面範囲内チェック
            self.matrix[ball_x, ball_y] = self.matrix.LED_YELLOW  # オレンジに最も近い色

        # 画面更新
        self.matrix.show()

    def finalize(self):
        """ゲーム終了処理"""
        # 画面をクリア
        self.matrix.fill(self.matrix.LED_OFF)
        self.matrix.show()

        # 7セグメントディスプレイをクリア
        self._devices.seg.fill(0)
        self._devices.seg.show()
