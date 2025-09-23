import time
import random
from games.game_interface import Game


class GameState:
    """ゲーム状態を管理するクラス定数"""

    PLAYING = "playing"
    SUCCESS = "success"
    GAME_OVER = "game_over"
    PAUSED = "paused"


class BombDefuseGame(Game):
    class Timer:
        """
        高精度時間管理のための内部クラス
        time.monotonic()を使用した正確な時間計測と一時停止・再開機能を提供
        """

        def __init__(self, initial_time: float):
            """
            タイマーを初期化

            Args:
                initial_time: 初期制限時間（秒）
            """
            self.initial_time = initial_time
            self.remaining_time = initial_time
            self.start_time = None
            self.pause_time = None
            self.is_running = False
            self.is_paused = False

        def start(self):
            """
            タイマーを開始
            現在時刻を記録してカウントダウンを開始
            """
            self.start_time = time.monotonic()
            self.is_running = True
            self.is_paused = False
            self.pause_time = None

        def pause(self):
            """
            タイマーを一時停止
            現在の残り時間を保存して時間の進行を停止
            """
            if self.is_running and not self.is_paused:
                current_time = time.monotonic()
                elapsed = current_time - self.start_time
                self.remaining_time = max(0, self.initial_time - elapsed)
                self.is_paused = True
                self.pause_time = current_time

        def resume(self):
            """
            タイマーを再開
            一時停止前の残り時間から再開
            """
            if self.is_running and self.is_paused:
                # 新しい開始時刻を設定（残り時間を考慮）
                current_time = time.monotonic()
                self.start_time = current_time - (
                    self.initial_time - self.remaining_time
                )
                self.is_paused = False
                self.pause_time = None

        def update(self) -> float:
            """
            タイマーを更新して現在の残り時間を返す

            Returns:
                float: 現在の残り時間（秒）、0以下の場合は0
            """
            if not self.is_running or self.is_paused or self.start_time is None:
                return self.remaining_time

            current_time = time.monotonic()
            elapsed = current_time - self.start_time
            self.remaining_time = max(0, self.initial_time - elapsed)
            return self.remaining_time

        def is_expired(self) -> bool:
            """
            タイマーが期限切れかどうかを判定

            Returns:
                bool: 期限切れの場合True、そうでなければFalse
            """
            return self.update() <= 0

        def reset(self, new_time: float):
            """
            タイマーを新しい時間でリセット

            Args:
                new_time: 新しい制限時間（秒）
            """
            self.initial_time = new_time
            self.remaining_time = new_time
            self.start_time = None
            self.pause_time = None
            self.is_running = False
            self.is_paused = False

    class VisualEffects:
        """
        LED マトリクス表示効果のための内部クラス
        爆弾の表示、爆発エフェクト、成功エフェクトなどの視覚表現を管理
        """

        def __init__(self, matrix):
            """
            VisualEffects を初期化

            Args:
                matrix: LED マトリクスオブジェクト
            """
            self.matrix = matrix
            self.blink_state = False
            self.last_blink_time = 0
            self.blink_interval = 0.5  # 点滅間隔（秒）

        def show_bomb(self, warning: bool = False):
            """
            爆弾の表示（通常表示または警告表示）

            Args:
                warning: True の場合は警告表示（点滅）、False の場合は通常表示

            Requirements: 4.1, 4.4
            - LED マトリクスに爆弾の状態を表示
            - 時間が少なくなる（3秒以下）時は警告を示すビジュアル効果を表示
            """
            # 警告表示の場合は点滅制御
            if warning:
                current_time = time.monotonic()
                if current_time - self.last_blink_time >= self.blink_interval:
                    self.blink_state = not self.blink_state
                    self.last_blink_time = current_time

                # 点滅状態がオフの場合は何も表示しない
                if not self.blink_state:
                    self.matrix.fill(self.matrix.LED_OFF)
                    self.matrix.show()
                    return

            # 爆弾のパターンを描画（赤色で爆弾の形を表現）
            # 中央に爆弾本体、周囲に導火線を表現
            bomb_pattern = [
                (3, 2),
                (4, 2),  # 上部導火線
                (2, 3),
                (3, 3),
                (4, 3),
                (5, 3),  # 爆弾本体上部
                (2, 4),
                (3, 4),
                (4, 4),
                (5, 4),  # 爆弾本体中央
                (2, 5),
                (3, 5),
                (4, 5),
                (5, 5),  # 爆弾本体下部
                (3, 6),
                (4, 6),  # 爆弾本体底部
            ]

            # 画面をクリア
            self.matrix.fill(self.matrix.LED_OFF)

            # 爆弾パターンを描画
            for x, y in bomb_pattern:
                if 0 <= x < 8 and 0 <= y < 8:
                    self.matrix[x, y] = self.matrix.LED_RED

            self.matrix.show()

        def show_explosion(self):
            """
            爆発エフェクトの表示

            Requirements: 3.3
            - ゲームオーバー時に爆発を示すビジュアルエフェクトを表示
            """
            # 爆発パターン（全画面に赤色で爆発を表現）
            # 中央から外側に向かって爆発が広がるイメージ
            explosion_pattern = [
                # 中央部（最も明るい）
                (3, 3),
                (4, 3),
                (3, 4),
                (4, 4),
                # 内側の爆発
                (2, 2),
                (5, 2),
                (2, 5),
                (5, 5),
                (1, 3),
                (6, 3),
                (3, 1),
                (4, 1),
                (3, 6),
                (4, 6),
                # 外側の爆発
                (0, 0),
                (7, 0),
                (0, 7),
                (7, 7),
                (1, 1),
                (6, 1),
                (1, 6),
                (6, 6),
                (0, 3),
                (7, 3),
                (0, 4),
                (7, 4),
                (3, 0),
                (4, 0),
                (3, 7),
                (4, 7),
            ]

            # 画面をクリア
            self.matrix.fill(self.matrix.LED_OFF)

            # 爆発パターンを描画（赤色）
            for x, y in explosion_pattern:
                if 0 <= x < 8 and 0 <= y < 8:
                    self.matrix[x, y] = self.matrix.LED_RED

            self.matrix.show()

        def show_success(self):
            """
            成功エフェクトの表示

            Requirements: 2.3
            - 正解ボタン押下時に成功を示すビジュアルフィードバックを表示
            """
            # 成功パターン（緑色でチェックマークや星を表現）
            # チェックマーク風のパターン
            success_pattern = [
                # チェックマークの形
                (2, 4),
                (3, 5),
                (4, 4),
                (5, 3),
                (6, 2),
                # 周囲の装飾
                (1, 1),
                (6, 1),
                (1, 6),
                (6, 6),
                (0, 3),
                (7, 3),
                (3, 0),
                (4, 0),
                (3, 7),
                (4, 7),
            ]

            # 画面をクリア
            self.matrix.fill(self.matrix.LED_OFF)

            # 成功パターンを描画（緑色）
            for x, y in success_pattern:
                if 0 <= x < 8 and 0 <= y < 8:
                    self.matrix[x, y] = self.matrix.LED_GREEN

            self.matrix.show()

        def clear(self):
            """
            LED マトリクスをクリア

            Requirements: 6.1
            - LED マトリクスをクリア
            """
            self.matrix.fill(self.matrix.LED_OFF)
            self.matrix.show()

    def __init__(self, devices):
        """
        ゲームの初期化

        Args:
            devices: DeviceManager インスタンス
        """
        super().__init__(devices)

        # ゲーム状態の初期化
        self.state = GameState.PLAYING
        self.current_stage = 1
        self.correct_button = "A"  # "A" または "B"
        self.max_stage_reached = 1

        # タイマー関連の設定
        self.base_time = 10.0  # 初期制限時間（秒）
        self.min_time = 3.0  # 最小制限時間（秒）
        self.time_reduction = 0.2  # ステージごとの時間短縮（秒）

        # Timer インスタンスを初期化
        self.timer = self.Timer(self.base_time)

        # VisualEffects インスタンスを初期化
        self.visual_effects = self.VisualEffects(self.matrix)

        # 表示効果関連
        self.effect_timer = 0.0
        self.success_effect_duration = 1.0  # 成功エフェクト表示時間（秒）
        self.explosion_effect_duration = 2.0  # 爆発エフェクト表示時間（秒）

        # ボタン状態管理
        self.button_pressed = False
        self.last_button_state_a = False
        self.last_button_state_b = False

        # ボタン入力待機時間の設定
        self.input_delay_duration = 1.0  # ゲーム開始後1秒間はボタン入力を無視
        self.input_delay_start_time = 0.0  # 入力待機開始時刻

    def _start_new_stage(self):
        """
        新しいステージを開始する処理

        ランダムにAまたはBボタンを正解として設定し、
        ステージに応じた制限時間を計算してタイマーを開始する。

        Requirements: 2.1, 2.4
        - 新しいステージが開始される時、AボタンまたはBボタンのどちらかをランダムに正解として設定
        - ステージ進行時の制限時間計算（0.2秒ずつ短縮、最小3秒）
        """
        # ランダムに正解ボタンを選択（AまたはB）
        self.correct_button = random.choice(["A", "B"])

        # ステージに応じた制限時間を計算
        # 基本時間からステージ数に応じて時間を短縮（最小時間まで）
        # ステージ1: 10.0秒, ステージ2: 9.8秒, ステージ3: 9.6秒, ... 最小3.0秒
        stage_time = max(
            self.min_time,
            self.base_time - (self.current_stage - 1) * self.time_reduction,
        )

        # タイマーをリセットして新しい時間で開始
        self.timer.reset(stage_time)
        self.timer.start()

        # ボタン押下状態をリセット（重複入力防止のため）
        self.button_pressed = False

        # ボタン入力待機時間を開始
        self.input_delay_start_time = time.monotonic()

        # ゲーム状態をプレイ中に設定
        self.state = GameState.PLAYING

        print(
            f"Stage {self.current_stage} started - Correct button: {self.correct_button}, Time: {stage_time:.1f}s"
        )

    def _is_input_delay_active(self):
        """
        ボタン入力待機時間中かどうかを判定する

        Returns:
            bool: 入力待機時間中の場合True、そうでなければFalse
        """
        if self.input_delay_start_time == 0.0:
            return False

        current_time = time.monotonic()
        elapsed = current_time - self.input_delay_start_time
        return elapsed < self.input_delay_duration

    def initialize(self):
        """
        ゲーム初期化処理

        Requirements: 1.1, 1.2, 1.3, 1.4
        - 初期ステージ（ステージ1）を設定
        - 初期制限時間（10秒）を設定
        - LEDマトリクスに爆弾のビジュアル表示
        - 7セグメントディスプレイに残り時間を表示
        """
        # 全ての内部状態を適切に初期化
        self.state = GameState.PLAYING
        self.current_stage = 1
        self.max_stage_reached = 1
        self.correct_button = "A"  # デフォルト値、_start_new_stage()で再設定される

        # ボタン状態をリセット
        self.button_pressed = False
        self.last_button_state_a = False
        self.last_button_state_b = False

        # エフェクトタイマーをリセット
        self.effect_timer = 0.0

        # タイマーを初期状態にリセット
        self.timer.reset(self.base_time)

        # 7セグメントディスプレイをクリアしてから初期化
        self._devices.seg.fill(0)
        self._devices.seg.show()

        # LEDマトリクスに初期爆弾表示
        self.visual_effects.show_bomb(warning=False)

        # 最初のステージを開始（タイマーもここで初期化される）
        self._start_new_stage()

        print(f"Bomb Defuse Game initialized - Stage {self.current_stage}")

    def _handle_button_press(self, button: str):
        """
        ボタン入力を処理する

        Args:
            button: 押されたボタン（"A" または "B"）

        Requirements: 2.2, 2.3, 3.1
        - 正解ボタン押下時は次のステージに進む
        - 正解ボタン押下時は成功を示すビジュアルフィードバックを表示
        - 間違ったボタン押下時はゲームオーバー状態に移行
        """
        # 既にボタンが押されている場合は重複入力を防止
        if self.button_pressed:
            return

        # ゲーム中でない場合は入力を無視
        if self.state != GameState.PLAYING:
            return

        # ボタン押下フラグを設定（重複入力防止）
        self.button_pressed = True

        print(f"Button {button} pressed - Correct: {self.correct_button}")

        # 正解・不正解の判定
        if button == self.correct_button:
            # 正解の場合
            self._handle_correct_answer()
        else:
            # 不正解の場合
            self._handle_incorrect_answer()

    def _handle_correct_answer(self):
        """
        正解ボタンが押された時の処理

        Requirements: 2.2, 2.3
        - 次のステージに進む
        - 成功を示すビジュアルフィードバックを表示
        """
        # 成功状態に移行
        self.state = GameState.SUCCESS

        # タイマーを停止
        self.timer.pause()

        # 成功エフェクトを表示
        self.visual_effects.show_success()

        # エフェクトタイマーを開始
        self.effect_timer = time.monotonic()

        # ステージを進行
        self.current_stage += 1
        self.max_stage_reached = max(self.max_stage_reached, self.current_stage)

        print(f"Correct! Advancing to stage {self.current_stage}")

    def _handle_incorrect_answer(self):
        """
        不正解ボタンが押された時の処理

        Requirements: 3.1
        - ゲームオーバー状態に移行
        """
        # ゲームオーバー状態に移行
        self.state = GameState.GAME_OVER

        # タイマーを停止
        self.timer.pause()

        # 爆発エフェクトを表示
        self.visual_effects.show_explosion()

        # エフェクトタイマーを開始
        self.effect_timer = time.monotonic()

        print(f"Wrong button! Game Over at stage {self.current_stage}")

    def update(self):
        """
        メインゲームループ処理

        一時停止中は更新処理をスキップし、
        ゲーム状態に応じて適切な処理を実行します。
        フレームレート制御との連携を考慮した設計。

        Requirements: 4.1, 4.2, 4.3
        - LEDマトリクスに爆弾の状態を表示
        - 7セグメントディスプレイに残り時間をカウントダウン表示
        - 現在のステージ数を何らかの方法で表示
        """
        # 一時停止中は更新処理をスキップ（フレームレート制御との連携）
        if self.is_paused:
            return

        # ゲーム状態に応じた処理を実行
        if self.state == GameState.PLAYING:
            # プレイ中の処理順序：
            # 1. ボタン入力処理（ユーザーインタラクション）
            self._check_button_input()
            # 2. タイマー更新と時間切れ判定（ゲームロジック）
            self._check_timer()
            # 3. ディスプレイ更新（視覚フィードバック）
            self._update_display()
        elif self.state == GameState.SUCCESS:
            # 成功エフェクト処理
            self._show_success_effect()
        elif self.state == GameState.GAME_OVER:
            # ゲームオーバーエフェクト処理
            self._show_game_over_effect()

    def _check_button_input(self):
        """
        ボタン入力をチェックして処理する

        重複入力を防止するため、ボタンの状態変化を監視し、
        押下された瞬間のみを検出する。
        一時停止中はボタン入力を無効化する。

        Requirements: 5.1, 5.2
        - 一時停止中のボタン入力無効化
        """
        # 現在のボタン状態を取得
        # ボタンの状態を更新（デバウンス処理）
        self.btn_a.update()
        self.btn_b.update()

        current_button_a = not self.btn_a.value  # プルアップなので反転
        current_button_b = not self.btn_b.value  # プルアップなので反転

        # 一時停止中はボタン入力を無効化（リセット以外）
        if self.is_paused:
            # 前回の状態は更新して、再開時の誤検出を防ぐ
            self.last_button_state_a = current_button_a
            self.last_button_state_b = current_button_b
            return

        # ボタン入力待機時間中はボタン入力を無効化
        if self._is_input_delay_active():
            # 前回の状態は更新して、待機時間終了後の誤検出を防ぐ
            self.last_button_state_a = current_button_a
            self.last_button_state_b = current_button_b
            return

        # ボタンAの押下検出（立ち下がりエッジ検出）
        if self.last_button_state_a and not current_button_a:
            self._handle_button_press("A")

        # ボタンBの押下検出（立ち下がりエッジ検出）
        if self.last_button_state_b and not current_button_b:
            self._handle_button_press("B")

        # 前回の状態を更新
        self.last_button_state_a = current_button_a
        self.last_button_state_b = current_button_b

    def _check_game_over_input(self):
        """
        ゲームオーバー時のボタン入力をチェックする

        左右同時押しでゲームリセット機能を提供する。
        ゲームオーバー状態でのみ呼び出される。
        """
        # ボタンの状態を更新（デバウンス処理）
        self.btn_a.update()
        self.btn_b.update()

        current_button_a = not self.btn_a.value  # プルアップなので反転
        current_button_b = not self.btn_b.value  # プルアップなので反転

        # 左右同時押しでリセット
        if current_button_a and current_button_b:
            if not (self.last_button_state_a and self.last_button_state_b):
                # 同時押しが検出された瞬間にリセット実行
                self.initialize()

        # 前回の状態を更新
        self.last_button_state_a = current_button_a
        self.last_button_state_b = current_button_b

    def _check_timer(self):
        """
        タイマーの状態をチェックして時間切れ判定を行う

        Requirements: 3.2
        - 制限時間が0になった時にゲームオーバー状態に移行
        """
        # タイマーが期限切れかチェック
        if self.timer.is_expired():
            # 時間切れでゲームオーバー
            self.state = GameState.GAME_OVER

            # タイマーを停止
            self.timer.pause()

            # 爆発エフェクトを表示
            self.visual_effects.show_explosion()

            # エフェクトタイマーを開始
            self.effect_timer = time.monotonic()

            print(f"Time's up! Game Over at stage {self.current_stage}")

    def _update_display(self):
        """
        LEDマトリクスと7セグメントディスプレイの表示更新

        フレームレート制御との連携を考慮し、効率的な表示更新を行う。
        ゲーム状態に応じた適切な視覚フィードバックを提供する。

        Requirements: 4.1, 4.2, 4.3
        - LEDマトリクスに爆弾の状態を表示
        - 7セグメントディスプレイに残り時間をカウントダウン表示
        - 現在のステージ数を何らかの方法で表示
        """
        # ボタン入力待機時間中の表示
        if self._is_input_delay_active():
            self._show_input_delay_display()
            return

        # 残り時間を取得（タイマーの更新も同時に行う）
        remaining_time = self.timer.update()

        # 警告表示の閾値判定（3秒以下で警告）
        warning_threshold = 3.0
        is_warning = remaining_time <= warning_threshold

        # LEDマトリクスに爆弾の状態を表示
        # 警告状態の場合は点滅効果を適用
        self.visual_effects.show_bomb(warning=is_warning)

        # 7セグメントディスプレイに残り時間をカウントダウン表示
        # 残り時間を整数秒で表示（小数点以下切り上げで直感的な表示）
        display_time = max(0, int(remaining_time + 0.99))  # 切り上げ処理

        # 7セグメントディスプレイをクリアして時間を表示
        self._devices.seg.fill(0)
        self._devices.seg.print(f"{display_time:02d}")  # 2桁ゼロパディング形式で表示
        self._devices.seg.show()

        # デバッグ情報（開発時の確認用）
        if hasattr(self, "_last_display_time"):
            if abs(display_time - self._last_display_time) >= 1:
                print(
                    f"Stage {self.current_stage} - Time: {display_time:02d}s"
                    + (" [WARNING]" if is_warning else "")
                )
                self._last_display_time = display_time
        else:
            self._last_display_time = display_time

    def _show_input_delay_display(self):
        """
        ボタン入力待機時間中の表示

        LEDマトリクスに待機中であることを示す表示を行い、
        7セグメントディスプレイに残り待機時間を表示する。
        """
        # 残り待機時間を計算
        current_time = time.monotonic()
        elapsed = current_time - self.input_delay_start_time
        remaining_delay = max(0, self.input_delay_duration - elapsed)

        # LEDマトリクスに待機中表示（青色で点滅）
        current_time_ms = int(current_time * 1000)
        blink_on = (current_time_ms // 250) % 2 == 0  # 250ms間隔で点滅

        if blink_on:
            # 待機中パターン（青色で四角形を表示）
            self.matrix.fill(self.matrix.LED_OFF)
            for x in range(2, 6):
                for y in range(2, 6):
                    self.matrix[x, y] = self.matrix.LED_BLUE
        else:
            # 点滅オフ時はクリア
            self.matrix.fill(self.matrix.LED_OFF)

        self.matrix.show()

        # 7セグメントディスプレイに残り待機時間を表示
        display_delay = max(0, int(remaining_delay + 0.99))  # 切り上げ処理
        self._devices.seg.fill(0)
        self._devices.seg.print(f"--")  # 待機中を示す表示
        self._devices.seg.show()

    def _show_success_effect(self):
        """
        成功時の視覚効果を表示する

        Requirements: 2.3
        - 正解ボタン押下時に成功を示すビジュアルフィードバックを表示
        """
        # 成功エフェクトの表示時間を管理
        current_time = time.monotonic()
        effect_elapsed = current_time - self.effect_timer

        # エフェクト表示時間
        success_effect_duration = self.success_effect_duration

        if effect_elapsed < success_effect_duration:
            # 成功エフェクトを表示
            self.visual_effects.show_success()

            # 7セグメントディスプレイに現在のステージ数を表示
            # ステージ数を2桁で表示（例：01, 02, 03, ...）
            stage_display = self.current_stage - 1  # 完了したステージ数

            self._devices.seg.fill(0)
            self._devices.seg.print(f"{stage_display:02d}")
            self._devices.seg.show()
        else:
            # エフェクト終了後、次のステージを開始
            self._start_new_stage()

    def _show_game_over_effect(self):
        """
        ゲームオーバー時の爆発エフェクトと最終スコア表示

        Requirements: 3.3, 3.4
        - 爆発を示すビジュアルエフェクトを表示
        - 最終スコア（到達ステージ）を表示
        """
        # ゲームオーバー時のボタン入力をチェック（リセット機能）
        self._check_game_over_input()

        # ゲームオーバーエフェクトの表示時間を管理
        current_time = time.monotonic()
        effect_elapsed = current_time - self.effect_timer

        # エフェクト表示時間
        explosion_effect_duration = self.explosion_effect_duration

        if effect_elapsed < explosion_effect_duration:
            # 爆発エフェクトを表示
            self.visual_effects.show_explosion()

            # 7セグメントディスプレイに最終スコア（到達ステージ）を表示
            # 到達したステージ数を2桁で表示
            final_score = self.max_stage_reached

            self._devices.seg.fill(0)
            self._devices.seg.print(f"{final_score:02d}")
            self._devices.seg.show()

            print(f"Final Score: Stage {final_score}")
        else:
            # エフェクト終了後はゲーム終了状態を維持
            # ゲーム選択システムが finalize() を呼び出すまで待機
            pass

    def finalize(self):
        """
        ゲーム終了処理

        Requirements: 6.1, 6.2, 6.3
        - LEDマトリクスをクリア
        - 7セグメントディスプレイをクリア
        - 全ての内部状態をリセット
        """
        # LEDマトリクスをクリア（VisualEffectsを使用）
        self.visual_effects.clear()

        # 7セグメントディスプレイをクリア
        self._devices.seg.fill(0)
        self._devices.seg.show()

        # 全ての内部状態を完全にリセット
        self.state = GameState.PLAYING
        self.current_stage = 1
        self.max_stage_reached = 1
        self.correct_button = "A"

        # ボタン状態をリセット
        self.button_pressed = False
        self.last_button_state_a = False
        self.last_button_state_b = False

        # エフェクトタイマーをリセット
        self.effect_timer = 0.0

        # タイマーを完全にリセット
        if hasattr(self, "timer") and self.timer:
            self.timer.reset(self.base_time)

        # 一時停止状態もリセット（基底クラスの状態）
        self.is_paused = False

        print("Bomb Defuse Game finalized")

    def pause(self):
        """
        ゲームを一時停止

        フレームレート制御との連携により、一時停止中は
        update()メソッドでの処理をスキップする。

        Requirements: 5.1, 5.2
        - タイマーを停止
        - 現在の表示状態を維持
        """
        # 基底クラスの一時停止処理を呼び出し
        super().pause()

        # タイマーを一時停止（プレイ中の場合のみ）
        if self.state == GameState.PLAYING and hasattr(self, "timer") and self.timer:
            self.timer.pause()

        print("Bomb Defuse Game paused")

    def resume(self):
        """
        ゲームを再開

        フレームレート制御との連携により、再開後は
        update()メソッドでの処理を正常に実行する。

        Requirements: 5.3, 5.4
        - タイマーを再開
        - 一時停止前の状態を復元
        """
        # 基底クラスの再開処理を呼び出し
        super().resume()

        # タイマーを再開（プレイ中の場合のみ）
        if self.state == GameState.PLAYING and hasattr(self, "timer") and self.timer:
            self.timer.resume()

        print("Bomb Defuse Game resumed")
