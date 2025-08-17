from .encoder_manager import EncoderManager
from .game_manager import GameManager
from .selection_state import SelectionState


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
            devices: デバイス管理オブジェクト
            encoder: ロータリーエンコーダー
            game_list (list): 利用可能なゲームクラスのリスト
        """
        self.devices = devices
        self.mode = GameSelectorMode.NORMAL_GAME_MODE

        # 各種マネージャーの初期化
        self.encoder_manager = EncoderManager(encoder)
        self.game_manager = GameManager(devices, game_list)
        self.seg = devices.seg
        self.selection_state = SelectionState(len(game_list))

    def initialize(self):
        """
        ゲーム選択機能の初期化

        初期ゲームのインスタンス作成と初期化を行います。
        エンコーダーの初期位置も記録します。
        """
        # 各マネージャーの初期化
        self.encoder_manager.initialize()
        self.game_manager.initialize_game(0)

        # 選択状態を現在のゲームに合わせる
        self.selection_state.set_selected_index(
            self.game_manager.get_current_game_index()
        )

    def update(self):
        """
        メインループでの状態管理

        現在のモードに応じて適切な処理を実行します。
        - 通常モード: ゲームの更新とエンコーダー監視
        - 選択モード: エンコーダーとボタンの処理
        """

        if self.mode == GameSelectorMode.NORMAL_GAME_MODE:
            # 現在のゲームを更新
            self.game_manager.update_current_game()

            # エンコーダーの回転を監視して選択モードに移行
            rotation = self.encoder_manager.check_rotation()
            if rotation != 0:
                self.enter_selection_mode()
        elif self.mode == GameSelectorMode.GAME_SELECTION_MODE:
            # エンコーダーの回転処理
            self._handle_encoder_rotation()

            # ボタン処理
            self._handle_button_input()

    def _handle_encoder_rotation(self):
        """エンコーダーの回転によるゲーム選択処理"""
        rotation = self.encoder_manager.check_rotation()

        if rotation > 0:
            # 時計回り: 次のゲーム
            self.selection_state.select_next()
            self._update_selection_display()
        elif rotation < 0:
            # 反時計回り: 前のゲーム
            self.selection_state.select_previous()
            self._update_selection_display()

    def _handle_button_input(self):
        """ボタン入力の処理"""
        try:
            self.devices.btn_a.update()
            self.devices.btn_b.update()

            if self.devices.btn_a.fell:
                self.change_game()
            elif self.devices.btn_b.fell:
                self.cancel_selection()

        except Exception as e:
            print(f"Error handling button input: {e}")

    def enter_selection_mode(self):
        """
        ゲーム選択モードへの移行

        現在のゲームを一時停止し、ゲーム選択モードに移行して7セグメントディスプレイにゲーム番号を表示
        """
        # 現在のゲームを一時停止
        self.game_manager.pause_current_game()

        # モードを変更
        self.mode = GameSelectorMode.GAME_SELECTION_MODE

        # 選択状態を現在のゲームに設定
        self.selection_state.set_selected_index(
            self.game_manager.get_current_game_index()
        )

        # 選択表示に切り替え
        self._update_selection_display()

    def exit_selection_mode(self):
        """
        ゲーム選択モードからの復帰

        ゲーム選択モードを終了し、通常のゲームモードに戻って
        新しいゲームの実行を開始する (またはゲームを再開する)
        """
        # モードを変更
        self.mode = GameSelectorMode.NORMAL_GAME_MODE

        # ゲームを再開
        self.game_manager.resume_current_game()

        print(
            f"Exited selection mode, current game index: {self.game_manager.get_current_game_index()}"
        )

    def change_game(self):
        """
        選択されたゲームに変更

        btn_aが押された時に現在選択されているゲームに変更し、
        新しいゲームを初期化してゲーム選択モードを終了する
        """
        selected_index = self.selection_state.get_selected_index()

        # ゲームを変更
        if self.game_manager.change_game(selected_index):
            # 成功した場合は選択モードを終了
            self.exit_selection_mode()
        else:
            # 失敗した場合は選択を元に戻す
            self.selection_state.set_selected_index(
                self.game_manager.get_current_game_index()
            )
            self._update_selection_display()

    def cancel_selection(self):
        """
        ゲーム選択のキャンセル

        btn_bが押された時にゲーム選択をキャンセルし、
        ゲーム選択モードを終了して一時停止していたゲームを再開し、
        7セグメントディスプレイを元の表示に戻す
        """
        # 選択を元のゲームに戻す
        self.selection_state.set_selected_index(
            self.game_manager.get_current_game_index()
        )

        print(
            f"Selection cancelled, returning to game index: {self.game_manager.get_current_game_index()}"
        )

        # ゲーム選択モードを終了
        self.exit_selection_mode()

    def _update_selection_display(self):
        """
        ゲーム選択モード用の7セグメントディスプレイ更新

        7セグメントディスプレイに--XX--形式で
        ゲーム番号を表示する (1桁目と4桁目に「-」、2~3桁目にゲーム番号)
        """
        game_number = self.selection_state.get_selected_number()

        self.seg.fill(False)

        # --XX--形式で表示
        self.seg[0] = "-"

        if game_number < 10:
            self.seg[1] = "0"
            self.seg[2] = str(game_number)
        else:
            tens = game_number // 10
            ones = game_number % 10
            self.seg[1] = str(tens)
            self.seg[2] = str(ones)

        self.seg[3] = "-"
