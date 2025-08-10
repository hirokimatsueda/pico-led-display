from games.device_manager import DeviceManager


class Game:
    """
    ゲームの基本インターフェース
    各ゲームはこのクラスを継承して実装する必要があります。
    """

    def __init__(self, devices: DeviceManager):
        self._devices = devices

    @property
    def matrix(self):
        return self._devices.matrix

    @property
    def button_a(self):
        return self._devices.button_a

    @property
    def button_b(self):
        return self._devices.button_b

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
