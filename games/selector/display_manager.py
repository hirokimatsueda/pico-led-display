class DisplayManager:
    """
    7セグメントディスプレイの管理を担当するクラス
    """

    def __init__(self, seg_display):
        """
        ディスプレイマネージャーの初期化

        Args:
            seg_display: 7セグメントディスプレイオブジェクト
        """
        self.seg = seg_display
        self.saved_state = None

    def show_game_selection(self, game_number):
        """
        ゲーム選択モード用の表示

        Args:
            game_number (int): 表示するゲーム番号（1ベース）
        """
        try:
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

        except Exception as e:
            print(f"Error updating selection display: {e}")

    def show_error(self, error_code):
        """
        エラーメッセージを表示

        Args:
            error_code (str): エラーコード（最大4文字）
        """
        try:
            self.seg.fill(False)
            for i, char in enumerate(error_code[:4]):
                self.seg[i] = char
        except Exception as e:
            print(f"Error displaying error message: {e}")

    def save_current_state(self):
        """現在の表示状態を保存"""
        try:
            # 実際の実装では表示状態の保存が困難なため、
            # 簡単な実装として空のリストを保存
            self.saved_state = []
        except Exception as e:
            print(f"Error saving display state: {e}")
            self.saved_state = None

    def restore_state(self):
        """保存された表示状態を復元"""
        try:
            if self.saved_state is not None:
                # 実際の復元は困難なため、クリアしてゲーム側での再描画を期待
                self.seg.fill(False)
                self.saved_state = None
            else:
                self.seg.fill(False)
        except Exception as e:
            print(f"Error restoring display state: {e}")
            self._safe_clear()

    def _safe_clear(self):
        """安全なディスプレイクリア"""
        try:
            self.seg.fill(False)
        except Exception as e:
            print(f"Error clearing display: {e}")
