class GameManager:
    """
    ゲームのライフサイクル管理を担当するクラス
    """

    def __init__(self, devices, game_list):
        """
        ゲームマネージャーの初期化

        Args:
            devices: デバイス管理オブジェクト
            game_list (list): 利用可能なゲームクラスのリスト
        """
        self.devices = devices
        self.game_list = game_list
        self.current_game = None
        self.current_game_index = 0

    def initialize_game(self, game_index=0):
        """
        指定されたインデックスのゲームを初期化

        Args:
            game_index (int): 初期化するゲームのインデックス

        Returns:
            bool: 初期化に成功した場合True
        """
        if not self._validate_game_index(game_index):
            return False

        game = self._safe_initialize(self.game_list[game_index])
        if game is not None:
            self.current_game = game
            self.current_game_index = game_index
            return True
        return False

    def change_game(self, new_game_index):
        """
        ゲームを変更

        Args:
            new_game_index (int): 新しいゲームのインデックス

        Returns:
            bool: 変更に成功した場合True
        """
        if not self._validate_game_index(new_game_index):
            return False

        # 現在のゲームを終了
        self._finalize_current_game()

        # 新しいゲームを初期化
        if self.initialize_game(new_game_index):
            print(f"Game changed to: {self.game_list[new_game_index].__name__}")
            return True
        else:
            # 失敗した場合は利用可能なゲームにフォールバック
            self._fallback_to_working_game()
            return False

    def update_current_game(self):
        """現在のゲームを更新"""
        if self.current_game:
            try:
                self.current_game.update()
            except Exception as e:
                print(f"Error updating current game: {e}")

    def pause_current_game(self):
        """現在のゲームを一時停止"""
        if self.current_game and hasattr(self.current_game, "pause"):
            try:
                self.current_game.pause()
            except Exception as e:
                print(f"Error pausing current game: {e}")

    def resume_current_game(self):
        """現在のゲームを再開"""
        if self.current_game and hasattr(self.current_game, "resume"):
            try:
                self.current_game.resume()
            except Exception as e:
                print(f"Error resuming current game: {e}")

    def _safe_initialize(self, game_class):
        """
        安全なゲーム初期化

        Args:
            game_class: 初期化するゲームクラス

        Returns:
            Game or None: 初期化されたゲームインスタンス
        """
        try:
            game = game_class(self.devices)
            if game and hasattr(game, "initialize"):
                game.initialize()
                print(f"Successfully initialized game: {game_class.__name__}")
                return game
            else:
                print(
                    f"Error: Game class {game_class.__name__} does not have initialize method"
                )
                return None
        except Exception as e:
            print(f"Game initialization error for {game_class.__name__}: {e}")
            return None

    def _finalize_current_game(self):
        """現在のゲームを終了処理"""
        if self.current_game:
            try:
                if hasattr(self.current_game, "finalize"):
                    self.current_game.finalize()
            except Exception as e:
                print(f"Error finalizing current game: {e}")
            finally:
                self.current_game = None

    def _validate_game_index(self, index):
        """ゲームインデックスの妥当性をチェック"""
        return 0 <= index < len(self.game_list) and len(self.game_list) > 0

    def _fallback_to_working_game(self):
        """利用可能なゲームにフォールバック"""
        print("Attempting to fallback to a working game...")

        for i, game_class in enumerate(self.game_list):
            if self.initialize_game(i):
                print(f"Successfully fell back to game: {game_class.__name__}")
                return

        print("Error: All games failed to initialize")

    def get_game_count(self):
        """ゲーム数を取得"""
        return len(self.game_list)

    def get_current_game_index(self):
        """現在のゲームインデックスを取得"""
        return self.current_game_index
