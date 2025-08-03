import board
import busio
import time
import random
from adafruit_ht16k33.matrix import Matrix8x8x2

i2c = busio.I2C(board.GP17, board.GP16)
matrix = Matrix8x8x2(i2c)

while True:
    matrix.fill(random.randrange(4))  # fill the matrix with a random color
    matrix[random.randrange(8), random.randrange(8)] = random.randrange(4)

    matrix.show()
    time.sleep(1)  # wait for a second
