cmake_minimum_required(VERSION 3.13)

# Raspberry Pi Pico 2 WH (RP2350)
set(PICO_BOARD pico2_w CACHE STRING "Board type")

include(pico_sdk_import.cmake)

project(pico_led_display C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(pico_led_display
    src/main.c
    src/device/ht16k33.c
    src/device/button.c
    src/device/encoder.c
    src/device/audio.c
    src/device/device_manager.c
    src/game/selector.c
    src/game/bouncing_ball.c
    src/game/falling_dot.c
    src/game/breakout.c
    src/game/bomb_defuse.c
    src/game/jump_runner.c
)

target_include_directories(pico_led_display PRIVATE src)

target_link_libraries(pico_led_display
    pico_stdlib
    pico_rand
    hardware_i2c
    hardware_pwm
    hardware_dma
    hardware_gpio
    hardware_clocks
)

# USB シリアルにログを出す (picotool や VS Code のシリアルモニタで確認できる)
pico_enable_stdio_usb(pico_led_display 1)
pico_enable_stdio_uart(pico_led_display 0)

# .uf2 / .elf / .bin などを生成
pico_add_extra_outputs(pico_led_display)
