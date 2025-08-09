from games.device_manager import DeviceManager


class Game:
    """
    ゲームの基本インターフェース
    各ゲームはこのクラスを継承して実装する必要があります。
    """

    def __init__(self, devices: DeviceManager):
        self.devices = devices

    def initialize(self):
        raise NotImplementedError("Subclasses should implement this method")

    def update(self):
        raise NotImplementedError("Subclasses should implement this method")

    def finalize(self):
        raise NotImplementedError("Subclasses should implement this method")
