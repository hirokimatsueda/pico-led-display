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
