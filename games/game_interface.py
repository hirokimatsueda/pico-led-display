from games.device_manager import DeviceManager


class Game:
    """
    ゲームの基本インターフェース
    各ゲームはこのクラスを継承して実装する必要があります。
    """

    def __init__(self, devices: DeviceManager):
        self._devices = devices
        self._is_paused = False  # 一時停止状態の初期化

    @property
    def matrix(self):
        return self._devices.matrix

    @property
    def btn_a(self):
        return self._devices.btn_a

    @property
    def btn_b(self):
        return self._devices.btn_b

    @property
    def matrix_width(self):
        return self.matrix.columns

    @property
    def matrix_height(self):
        return self.matrix.rows

    def initialize(self):
        raise NotImplementedError("Subclasses should implement this method")

    def update(self):
        raise NotImplementedError("Subclasses should implement this method")

    def finalize(self):
        raise NotImplementedError("Subclasses should implement this method")

    def pause(self):
        """
        ゲームを一時停止

        ゲーム選択機能で使用されます。
        デフォルト実装では一時停止状態フラグを設定し、LEDマトリクスの表示を維持します。
        必要に応じてサブクラスでオーバーライドしてください。
        """
        # 一時停止状態フラグを設定
        self._is_paused = True

        # LEDマトリクスの現在の表示状態を保存
        # 表示は維持されるため、特別な処理は不要

    def resume(self):
        """
        ゲームを再開

        ゲーム選択機能で使用されます。
        デフォルト実装では一時停止状態フラグを解除し、ゲーム状態を保持します。
        必要に応じてサブクラスでオーバーライドしてください。
        """
        # 一時停止状態フラグを解除
        self._is_paused = False

        # ゲーム状態は保持される
        # サブクラスで必要に応じて追加の復帰処理を実装

    @property
    def is_paused(self):
        """
        ゲームが一時停止中かどうかを返す

        Returns:
            bool: 一時停止中の場合True、そうでなければFalse
        """
        return getattr(self, "_is_paused", False)
