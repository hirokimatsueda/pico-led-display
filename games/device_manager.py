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
        self.i2c_0 = busio.I2C(board.GP17, board.GP16)
        self.matrix = Matrix8x8x2(self.i2c_0)

        # 7セグメントディスプレイ初期化（必要ならコメント解除）
        # self.i2c_1 = busio.I2C(board.GP15, board.GP14)
        # self.seg = Seg7x4(self.i2c_1)

        # ボタン初期化
        self.button_a = digitalio.DigitalInOut(board.GP0)
        self.button_a.direction = digitalio.Direction.INPUT
        self.button_a.pull = digitalio.Pull.UP

        self.button_b = digitalio.DigitalInOut(board.GP1)
        self.button_b.direction = digitalio.Direction.INPUT
        self.button_b.pull = digitalio.Pull.UP
