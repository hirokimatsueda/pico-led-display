class EncoderManager:
    """
    ロータリーエンコーダーの読み取りを担当するクラス
    """

    def __init__(self, encoder):
        """
        エンコーダーマネージャーの初期化

        Args:
            encoder: ロータリーエンコーダーオブジェクト
        """
        self.encoder = encoder
        self.last_position = 0

    def initialize(self):
        """エンコーダーの初期位置を設定"""
        self.last_position = self.read_position()

    def read_position(self):
        """
        エンコーダー位置読み取り

        Returns:
            int: エンコーダーの位置
        """

        return self.encoder.position

    def check_rotation(self):
        """
        エンコーダーの回転をチェック

        Returns:
            int: 回転量 (0=回転なし、正=時計回り、負=反時計回り)
        """
        current_position = self.read_position()
        rotation = current_position - self.last_position

        if rotation != 0:
            self.last_position = current_position

        return rotation
