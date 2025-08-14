import board
import busio
import digitalio
from adafruit_ht16k33.matrix import Matrix8x8x2
from adafruit_ht16k33.segments import Seg7x4
from adafruit_debouncer import Debouncer


class DeviceManager:
    """
    デバイス管理クラス
    LEDマトリクス、7セグメントディスプレイ、ボタンなどのデバイスを管理します。
    """

    def __init__(self):
        # LEDマトリクス初期化
        self._i2c_0 = busio.I2C(board.GP17, board.GP16, frequency=400000)
        self._matrix = Matrix8x8x2(self._i2c_0)

        # 7セグメントディスプレイ初期化
        self._i2c_1 = busio.I2C(board.GP15, board.GP14)
        self._seg = Seg7x4(self._i2c_1)

        # ボタン初期化
        self._pin_a = digitalio.DigitalInOut(board.GP0)
        self._pin_a.direction = digitalio.Direction.INPUT
        self._pin_a.pull = digitalio.Pull.UP
        self._btn_a = Debouncer(self._pin_a)

        self._pin_b = digitalio.DigitalInOut(board.GP1)
        self._pin_b.direction = digitalio.Direction.INPUT
        self._pin_b.pull = digitalio.Pull.UP
        self._btn_b = Debouncer(self._pin_b)

    @property
    def matrix(self) -> Matrix8x8x2:
        """LEDマトリクスへのアクセス"""
        return self._matrix

    @property
    def seg(self) -> Seg7x4:
        """7セグメントディスプレイへのアクセス"""
        return self._seg

    @property
    def btn_a(self) -> Debouncer:
        """Aボタンへのアクセス"""
        return self._btn_a

    @property
    def btn_b(self) -> Debouncer:
        """Bボタンへのアクセス"""
        return self._btn_b
