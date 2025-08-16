import rotaryio
from games.device_manager import DeviceManager
from games.game_interface import Game


class GameSelectorMode:
    """
    ゲーム選択機能の状態を表現するクラス定数

    NORMAL_GAME_MODE: 通常のゲーム実行モード
    GAME_SELECTION_MODE: ゲーム選択モード
    """

    NORMAL_GAME_MODE = "normal"
    GAME_SELECTION_MODE = "selection"


class GameSelector:
    """
    ロータリーエンコーダーを使用したゲーム選択機能を管理するクラス

    このクラスは通常のゲーム実行モードとゲーム選択モードの状態管理を行い、
    ロータリーエンコーダーの回転によるゲーム選択とボタン操作による
    ゲーム変更・キャンセル機能を提供します。
    """

    def __init__(self, devices, encoder, game_list):
        """
        GameSelectorの初期化

        Args:
            devices (DeviceManager): デバイス管理オブジェクト
            encoder (rotaryio.IncrementalEncoder): ロータリーエンコーダー
            game_list (list): 利用可能なゲームクラスのリスト
        """
        self.devices = devices
        self.encoder = encoder
        self.game_list = game_list

        # ゲーム選択状態の管理
        self.current_game_index = 0  # 現在実行中のゲームのインデックス
        self.selected_game_index = (
            0  # ゲーム選択モードで選択されているゲームのインデックス
        )
        self.mode = GameSelectorMode.NORMAL_GAME_MODE  # 現在のモード

        # エンコーダー状態の管理
        self.last_encoder_position = 0  # 前回のエンコーダー位置

        # ゲームインスタンスの管理
        self.current_game = None  # 現在のゲームインスタンス (Game)

        # 7セグメントディスプレイの状態保存用
        self.previous_seg_display = None  # 保存された表示状態

        # エラーハンドリング用の状態管理
        self.encoder_error_count = 0  # エンコーダー読み取りエラーの連続回数
        self.max_encoder_errors = 5  # エンコーダーエラーの最大許容回数
        self.encoder_disabled = False  # エンコーダー機能の無効化フラグ
        self.encoder_recovery_attempts = 0  # エンコーダー回復試行回数
        self.max_recovery_attempts = 3  # 最大回復試行回数

    def initialize(self):
        """
        ゲーム選択機能の初期化

        初期ゲームのインスタンス作成と初期化を行います。
        エンコーダーの初期位置も記録します。
        """
        # 初期ゲームのインスタンス作成
        if self.game_list and len(self.game_list) > 0:
            self.current_game = self._safe_game_initialize(
                self.game_list[self.current_game_index]
            )

        # エンコーダーの初期位置を記録
        self.last_encoder_position = self._safe_encoder_read()

        # 選択されているゲームインデックスを現在のゲームに設定
        self.selected_game_index = self.current_game_index

    def _safe_encoder_read(self):
        """
        安全なエンコーダー読み取り

        エラー回復機能付きでエンコーダーの位置を読み取ります。
        連続エラー時はエンコーダー機能を無効化します。

        Returns:
            int: エンコーダーの位置（エラー時は前回の値）
        """
        if self.encoder_disabled:
            return self.last_encoder_position

        try:
            position = self.encoder.position
            # 正常に読み取れた場合はエラーカウントをリセット
            self.encoder_error_count = 0
            return position
        except Exception as e:
            self.encoder_error_count += 1
            print(
                f"Encoder read error ({self.encoder_error_count}/{self.max_encoder_errors}): {e}"
            )

            # 連続エラーが最大回数に達した場合はエンコーダー機能を無効化
            if self.encoder_error_count >= self.max_encoder_errors:
                self.encoder_disabled = True
                print("Encoder functionality disabled due to consecutive errors")
                self._display_error_message("Err")

            return self.last_encoder_position

    def _safe_game_initialize(self, game_class):
        """
        安全なゲーム初期化

        エラーハンドリング付きでゲームを初期化します。
        初期化に失敗した場合は適切なエラー処理を行います。

        Args:
            game_class (type): 初期化するゲームクラス

        Returns:
            Game or None: 初期化されたゲームインスタンス（失敗時はNone）
        """
        try:
            # ゲームインスタンスの作成
            game = game_class(self.devices)

            # ゲームの初期化
            if game and hasattr(game, "initialize"):
                game.initialize()
                print(f"Successfully initialized game: {game_class.__name__}")
                return game
            else:
                print(
                    f"Error: Game class {game_class.__name__} does not have initialize method"
                )
                self._display_error_message("Init")
                return None

        except Exception as e:
            print(f"Game initialization error for {game_class.__name__}: {e}")
            self._display_error_message("Err")
            return None

    def _display_error_message(self, message):
        """
        7セグメントディスプレイにエラーメッセージを表示

        Args:
            message (str): 表示するエラーメッセージ（最大4文字）
        """
        try:
            self.devices.seg.fill(False)
            # メッセージを4文字に制限して表示
            for i, char in enumerate(message[:4]):
                self.devices.seg[i] = char
        except Exception as e:
            print(f"Error displaying error message: {e}")
            # 7セグメントディスプレイでエラーが発生した場合は何もしない

    def _attempt_encoder_recovery(self):
        """
        エンコーダーの回復を試行

        エンコーダーが無効化されている場合に、回復を試行します。

        Returns:
            bool: 回復に成功した場合True、失敗した場合False
        """
        if (
            not self.encoder_disabled
            or self.encoder_recovery_attempts >= self.max_recovery_attempts
        ):
            return False

        self.encoder_recovery_attempts += 1
        print(
            f"Attempting encoder recovery ({self.encoder_recovery_attempts}/{self.max_recovery_attempts})"
        )

        try:
            # エンコーダーの読み取りを試行
            test_position = self.encoder.position

            # 成功した場合はエンコーダーを再有効化
            self.encoder_disabled = False
            self.encoder_error_count = 0
            self.last_encoder_position = test_position
            print("Encoder recovery successful")
            return True

        except Exception as e:
            print(f"Encoder recovery failed: {e}")
            return False

    def check_encoder_health(self):
        """
        エンコーダーの健全性をチェックし、必要に応じて回復を試行

        定期的に呼び出されることを想定しています。
        """
        if self.encoder_disabled:
            # 無効化されている場合は回復を試行
            if self._attempt_encoder_recovery():
                print("Encoder functionality restored")
            elif self.encoder_recovery_attempts >= self.max_recovery_attempts:
                print(
                    "Encoder recovery attempts exhausted, functionality permanently disabled"
                )

    def _validate_game_index(self, index):
        """
        ゲームインデックスの境界チェック

        Args:
            index (int): チェックするゲームインデックス

        Returns:
            bool: インデックスが有効な場合True、無効な場合False
        """
        return 0 <= index < len(self.game_list) and len(self.game_list) > 0

    def update(self):
        """
        メインループでの状態管理

        現在のモードに応じて適切な処理を実行します。
        - 通常モード: ゲームの更新とエンコーダー監視
        - 選択モード: エンコーダーとボタンの処理
        """
        # エンコーダーの健全性をチェック
        self.check_encoder_health()

        if self.mode == GameSelectorMode.NORMAL_GAME_MODE:
            # 通常のゲーム実行モード
            if self.current_game:
                try:
                    self.current_game.update()
                except Exception as e:
                    print(f"Error updating current game: {e}")
                    # ゲーム更新でエラーが発生した場合は継続

            # エンコーダーの回転を監視（ゲーム選択モードへの移行判定）
            self._monitor_encoder_for_mode_change()

        elif self.mode == GameSelectorMode.GAME_SELECTION_MODE:
            # ゲーム選択モード
            self._handle_selection_mode()

    def _monitor_encoder_for_mode_change(self):
        """
        エンコーダーの回転を監視してゲーム選択モードへの移行を判定

        Requirements 1.1, 1.2: ロータリーエンコーダーが回転した時に
        現在のゲームを一時停止してゲーム選択モードに移行する
        """
        if self.encoder_disabled:
            return

        current_position = self._safe_encoder_read()
        if current_position != self.last_encoder_position:
            # エンコーダーが回転した場合、ゲーム選択モードに移行
            self.enter_selection_mode()
            self.last_encoder_position = current_position

    def _handle_selection_mode(self):
        """
        ゲーム選択モードでの処理

        エンコーダーの回転によるゲーム選択とボタン操作を処理します。
        """
        # エンコーダーの回転処理
        self.handle_encoder_rotation()

        # ボタン処理
        try:
            self.devices.btn_a.update()
            self.devices.btn_b.update()

            # btn_a: ゲーム変更
            if self.devices.btn_a.fell:
                self.change_game()

            # btn_b: 選択キャンセル
            if self.devices.btn_b.fell:
                self.cancel_selection()

        except Exception as e:
            print(f"Error handling button input in selection mode: {e}")
            # ボタン処理でエラーが発生した場合は継続

    def enter_selection_mode(self):
        """
        ゲーム選択モードへの移行

        Requirements 1.1, 1.2, 1.3: 現在のゲームを一時停止し、
        ゲーム選択モードに移行して7セグメントディスプレイにゲーム番号を表示
        """
        # 現在のゲームを一時停止
        if self.current_game and hasattr(self.current_game, "pause"):
            self.current_game.pause()

        # モードを変更
        self.mode = GameSelectorMode.GAME_SELECTION_MODE

        # 選択されているゲームを現在のゲームに設定
        self.selected_game_index = self.current_game_index

        # 7セグメントディスプレイの現在の状態を保存
        self.previous_seg_display = self._save_current_seg_display()

        # ゲーム選択モード用の表示に切り替え
        self._update_selection_display()

    def exit_selection_mode(self):
        """
        ゲーム選択モードからの復帰

        Requirements 3.3, 3.4: ゲーム選択モードを終了し、通常のゲームモードに戻って
        新しいゲームの実行を開始する（またはゲームを再開する）
        """
        # モードを変更
        self.mode = GameSelectorMode.NORMAL_GAME_MODE

        # 7セグメントディスプレイの状態を復元
        self._restore_seg_display()

        # ゲームを再開（新しいゲームの場合は既に初期化済み、
        # キャンセルの場合は一時停止していたゲームを再開）
        if self.current_game and hasattr(self.current_game, "resume"):
            self.current_game.resume()

        print(f"Exited selection mode, current game index: {self.current_game_index}")

    def handle_encoder_rotation(self):
        """
        エンコーダーの回転によるゲーム選択処理

        Requirements 2.4, 5.1, 5.2, 5.3, 5.4: ロータリーエンコーダーの回転を検出し、
        ゲーム番号を循環的に変更して7セグメントディスプレイを更新する
        """
        if self.encoder_disabled:
            return

        current_position = self._safe_encoder_read()

        # エンコーダーの位置変化を検出
        if current_position != self.last_encoder_position:
            position_change = current_position - self.last_encoder_position

            # 時計回りの回転（正の値）: 次のゲームを選択
            if position_change > 0:
                self._select_next_game()
            # 反時計回りの回転（負の値）: 前のゲームを選択
            elif position_change < 0:
                self._select_previous_game()

            # エンコーダー位置を更新
            self.last_encoder_position = current_position

            # 7セグメントディスプレイを更新
            self._update_selection_display()

    def _select_next_game(self):
        """
        次のゲームを選択（循環処理）

        Requirements 5.1, 5.3: 時計回りの回転で次のゲーム番号を選択し、
        最後のゲームの場合は最初のゲームに戻る
        """
        if len(self.game_list) > 0:
            next_index = (self.selected_game_index + 1) % len(self.game_list)
            if self._validate_game_index(next_index):
                self.selected_game_index = next_index
            else:
                print(f"Error: Invalid next game index {next_index}")

    def _select_previous_game(self):
        """
        前のゲームを選択（循環処理）

        Requirements 5.2, 5.4: 反時計回りの回転で前のゲーム番号を選択し、
        最初のゲームの場合は最後のゲームに戻る
        """
        if len(self.game_list) > 0:
            prev_index = (self.selected_game_index - 1) % len(self.game_list)
            if self._validate_game_index(prev_index):
                self.selected_game_index = prev_index
            else:
                print(f"Error: Invalid previous game index {prev_index}")

    def change_game(self):
        """
        選択されたゲームに変更

        Requirements 3.1, 3.2, 3.3, 3.4: btn_aが押された時に現在選択されている
        ゲームに変更し、新しいゲームを初期化してゲーム選択モードを終了する
        """
        # ゲームインデックスの境界チェック
        if not self._validate_game_index(self.selected_game_index):
            print(f"Error: Invalid game index {self.selected_game_index}")
            self._display_error_message("Idx")
            return

        # 現在のゲームを終了処理
        if self.current_game:
            try:
                if hasattr(self.current_game, "finalize"):
                    self.current_game.finalize()
            except Exception as e:
                print(f"Error finalizing current game: {e}")
            finally:
                self.current_game = None

        # 新しいゲームのインスタンス作成と初期化
        new_game_class = self.game_list[self.selected_game_index]
        new_game = self._safe_game_initialize(new_game_class)

        if new_game is not None:
            # 新しいゲームの初期化が成功した場合
            self.current_game = new_game
            self.current_game_index = self.selected_game_index
            print(f"Game changed to: {new_game_class.__name__}")

            # ゲーム選択モードを終了して新しいゲームの実行を開始
            self.exit_selection_mode()
        else:
            # 新しいゲームの初期化が失敗した場合は前のゲームに戻る
            print(
                f"Failed to initialize game {new_game_class.__name__}, staying in selection mode"
            )
            # 選択されているゲームインデックスを元のゲームに戻す
            self.selected_game_index = self.current_game_index
            self._update_selection_display()

            # 前のゲームが存在しない場合は、利用可能な最初のゲームを試す
            if self.current_game is None:
                self._fallback_to_working_game()

    def cancel_selection(self):
        """
        ゲーム選択のキャンセル

        Requirements 4.1, 4.2, 4.3, 4.4: btn_bが押された時にゲーム選択をキャンセルし、
        ゲーム選択モードを終了して一時停止していたゲームを再開し、
        7セグメントディスプレイを元の表示に戻す
        """
        # 選択されているゲームインデックスを元のゲームに戻す
        # (ユーザーが選択を変更していても、元のゲームに戻る)
        self.selected_game_index = self.current_game_index

        print(
            f"Selection cancelled, returning to game index: {self.current_game_index}"
        )

        # ゲーム選択モードを終了して一時停止していたゲームを再開
        # exit_selection_mode()が7セグメントディスプレイの復元とゲーム再開を行う
        self.exit_selection_mode()

    def _fallback_to_working_game(self):
        """
        利用可能なゲームにフォールバックする

        現在のゲームが利用できない場合に、利用可能な最初のゲームを見つけて初期化します。
        """
        print("Attempting to fallback to a working game...")

        for i, game_class in enumerate(self.game_list):
            game = self._safe_game_initialize(game_class)
            if game is not None:
                self.current_game = game
                self.current_game_index = i
                self.selected_game_index = i
                print(f"Successfully fell back to game: {game_class.__name__}")
                return

        # すべてのゲームの初期化に失敗した場合
        print("Error: All games failed to initialize")
        self._display_error_message("NoGm")

    def _update_selection_display(self):
        """
        ゲーム選択モード用の7セグメントディスプレイ更新

        Requirements 2.1, 2.2, 2.3: 7セグメントディスプレイに--XX--形式で
        ゲーム番号を表示する（1桁目と4桁目に「-」、2~3桁目にゲーム番号）
        """
        try:
            # ゲーム番号を1ベースで表示（内部は0ベース）
            game_number = self.selected_game_index + 1

            # 7セグメントディスプレイをクリア
            self.devices.seg.fill(False)

            # --XX--形式で表示
            # 1桁目: - (ダッシュ)
            self.devices.seg[0] = "-"

            # 2~3桁目: ゲーム番号（2桁で表示）
            if game_number < 10:
                self.devices.seg[1] = "0"
                self.devices.seg[2] = str(game_number)
            else:
                tens = game_number // 10
                ones = game_number % 10
                self.devices.seg[1] = str(tens)
                self.devices.seg[2] = str(ones)

            # 4桁目: - (ダッシュ)
            self.devices.seg[3] = "-"

        except Exception as e:
            print(f"Error updating selection display: {e}")
            # 7セグメントディスプレイでエラーが発生した場合は何もしない

    def _save_current_seg_display(self):
        """
        現在の7セグメントディスプレイの状態を保存

        Returns:
            list or None: 現在の表示内容のリスト（各桁の文字列）
        """
        try:
            # 7セグメントディスプレイの現在の状態を読み取り
            # 注意: adafruit_ht16k33では直接読み取りができないため、
            # 実際の実装では別の方法で状態を管理する必要がある
            # ここでは簡単な実装として空のリストを返す
            return []
        except Exception as e:
            print(f"Error saving seg display state: {e}")
            return None

    def _restore_seg_display(self):
        """
        7セグメントディスプレイの状態を復元

        ゲーム選択モードから通常モードに戻る際に、
        以前の7セグメントディスプレイの状態を復元します。
        """
        try:
            # 保存された状態がある場合は復元
            if self.previous_seg_display is not None:
                # 実際の復元処理
                # 注意: adafruit_ht16k33では直接復元ができないため、
                # 実際の実装では各ゲームが自身の表示を管理する必要がある
                # ここでは7セグメントディスプレイをクリアして、
                # ゲーム側で再描画されることを期待する
                self.devices.seg.fill(False)
                self.previous_seg_display = None
            else:
                # 保存された状態がない場合はクリア
                self.devices.seg.fill(False)

        except Exception as e:
            print(f"Error restoring seg display state: {e}")
            # エラーが発生した場合はクリアして継続
            try:
                self.devices.seg.fill(False)
            except Exception as clear_error:
                print(f"Error clearing seg display: {clear_error}")
                # 7セグメントディスプレイのクリアも失敗した場合は何もしない
