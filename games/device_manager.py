import board
import busio
import digitalio
from adafruit_ht16k33.matrix import Matrix8x8x2
from adafruit_ht16k33.segments import Seg7x4


class DeviceManager:
    """
    デバイス管理クラス
    LEDマトリクス、7セグメントディスプレイ、ボタンなどのデバイスを管理します。
    """

    def __init__(self):
        # LEDマトリクス初期化
        self._i2c_0 = busio.I2C(board.GP17, board.GP16)
        self._matrix = Matrix8x8x2(self._i2c_0)

        # 7セグメントディスプレイ初期化（必要ならコメント解除）
        # self._i2c_1 = busio.I2C(board.GP15, board.GP14)
        # self._seg = Seg7x4(self._i2c_1)

        # ボタン初期化
        self._button_a = digitalio.DigitalInOut(board.GP0)
        self._button_a.direction = digitalio.Direction.INPUT
        self._button_a.pull = digitalio.Pull.UP

        self._button_b = digitalio.DigitalInOut(board.GP1)
        self._button_b.direction = digitalio.Direction.INPUT
        self._button_b.pull = digitalio.Pull.UP

    @property
    def matrix(self) -> Matrix8x8x2:
        """LEDマトリクスへのアクセス"""
        return self._matrix

    # 7セグメントディスプレイ（必要ならコメント解除）
    # @property
    # def seg(self) -> Seg7x4:
    #     return self._seg

    @property
    def button_a(self) -> digitalio.DigitalInOut:
        """Aボタンへのアクセス"""
        return self._button_a

    @property
    def button_b(self) -> digitalio.DigitalInOut:
        """Bボタンへのアクセス"""
        return self._button_b
