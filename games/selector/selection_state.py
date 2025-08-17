class SelectionState:
    """
    ゲーム選択の状態管理を担当するクラス
    """

    def __init__(self, game_count):
        """
        選択状態の初期化

        Args:
            game_count (int): 利用可能なゲーム数
        """
        self.game_count = game_count
        self.selected_index = 0

    def select_next(self):
        """次のゲームを選択（循環）"""
        if self.game_count > 0:
            self.selected_index = (self.selected_index + 1) % self.game_count

    def select_previous(self):
        """前のゲームを選択（循環）"""
        if self.game_count > 0:
            self.selected_index = (self.selected_index - 1) % self.game_count

    def set_selected_index(self, index):
        """選択インデックスを設定"""
        if 0 <= index < self.game_count:
            self.selected_index = index

    def get_selected_index(self):
        """選択されているインデックスを取得"""
        return self.selected_index

    def get_selected_number(self):
        """選択されているゲーム番号を取得（1ベース）"""
        return self.selected_index + 1
