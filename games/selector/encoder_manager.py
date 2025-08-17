class EncoderManager:
    """
    ロータリーエンコーダーの安全な読み取りとエラー管理を担当するクラス
    """

    # 定数
    MAX_ENCODER_ERRORS = 5
    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self, encoder):
        """
        エンコーダーマネージャーの初期化

        Args:
            encoder: ロータリーエンコーダーオブジェクト
        """
        self.encoder = encoder
        self.last_position = 0
        self.error_count = 0
        self.disabled = False
        self.recovery_attempts = 0

    def initialize(self):
        """エンコーダーの初期位置を設定"""
        self.last_position = self.read_position()

    def read_position(self):
        """
        安全なエンコーダー位置読み取り

        Returns:
            int: エンコーダーの位置（エラー時は前回の値）
        """
        if self.disabled:
            return self.last_position

        try:
            position = self.encoder.position
            self.error_count = 0  # 正常読み取り時はエラーカウントをリセット
            return position
        except Exception as e:
            return self._handle_read_error(e)

    def _handle_read_error(self, error):
        """エンコーダー読み取りエラーの処理"""
        self.error_count += 1
        print(
            f"Encoder read error ({self.error_count}/{self.MAX_ENCODER_ERRORS}): {error}"
        )

        if self.error_count >= self.MAX_ENCODER_ERRORS:
            self.disabled = True
            print("Encoder functionality disabled due to consecutive errors")

        return self.last_position

    def check_rotation(self):
        """
        エンコーダーの回転をチェック

        Returns:
            int: 回転量（0=回転なし、正=時計回り、負=反時計回り）
        """
        if self.disabled:
            return 0

        current_position = self.read_position()
        rotation = current_position - self.last_position

        if rotation != 0:
            self.last_position = current_position

        return rotation

    def attempt_recovery(self):
        """
        エンコーダーの回復を試行

        Returns:
            bool: 回復に成功した場合True
        """
        if not self.disabled or self.recovery_attempts >= self.MAX_RECOVERY_ATTEMPTS:
            return False

        self.recovery_attempts += 1
        print(
            f"Attempting encoder recovery ({self.recovery_attempts}/{self.MAX_RECOVERY_ATTEMPTS})"
        )

        try:
            test_position = self.encoder.position
            # 成功した場合は再有効化
            self.disabled = False
            self.error_count = 0
            self.last_position = test_position
            print("Encoder recovery successful")
            return True
        except Exception as e:
            print(f"Encoder recovery failed: {e}")
            return False

    def check_health(self):
        """エンコーダーの健全性をチェックし、必要に応じて回復を試行"""
        if self.disabled:
            if self.attempt_recovery():
                print("Encoder functionality restored")
            elif self.recovery_attempts >= self.MAX_RECOVERY_ATTEMPTS:
                print(
                    "Encoder recovery attempts exhausted, functionality permanently disabled"
                )
