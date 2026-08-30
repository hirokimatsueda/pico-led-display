#include <stdio.h>

#include "device/button.h"
#include "device/device_manager.h"
#include "device/encoder.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"

#define PIN_MATRIX_SCL 17
#define PIN_MATRIX_SDA 16
#define PIN_SEG_SCL 15
#define PIN_SEG_SDA 14
#define PIN_BTN_A 18
#define PIN_BTN_B 19
#define PIN_ENC_A 10
#define PIN_ENC_B 11
#define PIN_AUDIO 20

static ht16k33_t matrix_dev;
static ht16k33_t seg_dev;
static button_t btn_a;
static button_t btn_b;

static void i2c_bus_init(i2c_inst_t *i2c, uint sda, uint scl, uint baudrate) {
    i2c_init(i2c, baudrate);
    gpio_set_function(sda, GPIO_FUNC_I2C);
    gpio_set_function(scl, GPIO_FUNC_I2C);
    gpio_pull_up(sda);
    gpio_pull_up(scl);
}

void devices_init(void) {
    i2c_bus_init(i2c0, PIN_MATRIX_SDA, PIN_MATRIX_SCL, 400 * 1000);
    i2c_bus_init(i2c1, PIN_SEG_SDA, PIN_SEG_SCL, 100 * 1000);

    ht16k33_init(&matrix_dev, i2c0, HT16K33_ADDR);
    ht16k33_init(&seg_dev, i2c1, HT16K33_ADDR);

    button_init(&btn_a, PIN_BTN_A);
    button_init(&btn_b, PIN_BTN_B);
    encoder_init(PIN_ENC_A, PIN_ENC_B);

    audio_init(PIN_AUDIO);
}

void devices_update_inputs(void) {
    button_update(&btn_a);
    button_update(&btn_b);
}

void matrix_fill(led_color_t color) { ht16k33_matrix_fill(&matrix_dev, color); }

void matrix_set(int x, int y, led_color_t color) {
    ht16k33_matrix_set_pixel(&matrix_dev, x, y, color);
}

void matrix_show(void) { ht16k33_show(&matrix_dev); }

void matrix_border(led_color_t color) {
    for (int x = 0; x < MATRIX_WIDTH; x++) {
        matrix_set(x, 0, color);
        matrix_set(x, MATRIX_HEIGHT - 1, color);
    }
    for (int y = 0; y < MATRIX_HEIGHT; y++) {
        matrix_set(0, y, color);
        matrix_set(MATRIX_WIDTH - 1, y, color);
    }
}

void seg_text(const char *text) {
    ht16k33_seg_print(&seg_dev, text);
    ht16k33_show(&seg_dev);
}

void seg_int(int value) {
    char buf[8];
    snprintf(buf, sizeof(buf), "%d", value);
    seg_text(buf);
}

void seg_int02(int value) {
    char buf[8];
    snprintf(buf, sizeof(buf), "%02d", value);
    seg_text(buf);
}

void seg_selection(int game_number) {
    /* 1 桁目と 4 桁目に "-"、2〜3 桁目にゲーム番号を表示する */
    char buf[8];
    snprintf(buf, sizeof(buf), "-%02d-", game_number);
    seg_text(buf);
}

bool btn_a_pressed(void) { return button_pressed(&btn_a); }
bool btn_b_pressed(void) { return button_pressed(&btn_b); }
bool btn_a_fell(void) { return btn_a.fell; }
bool btn_b_fell(void) { return btn_b.fell; }

int32_t encoder_pos(void) { return encoder_position(); }
