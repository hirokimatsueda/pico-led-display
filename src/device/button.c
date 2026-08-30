#include "device/button.h"
#include "hardware/gpio.h"
#include "pico/time.h"

/* チャタリングとみなす時間 (adafruit_debouncer の既定値 0.01 秒に合わせる) */
#define DEBOUNCE_US 10000u

void button_init(button_t *btn, uint pin) {
    btn->pin = pin;
    gpio_init(pin);
    gpio_set_dir(pin, GPIO_IN);
    gpio_pull_up(pin);

    bool value = gpio_get(pin);
    btn->raw = value;
    btn->state = value;
    btn->fell = false;
    btn->rose = false;
    btn->last_change_us = time_us_32();
}

void button_update(button_t *btn) {
    btn->fell = false;
    btn->rose = false;

    bool value = gpio_get(btn->pin);
    uint32_t now = time_us_32();

    if (value != btn->raw) {
        /* 生の値が変化した時点から測り直す */
        btn->raw = value;
        btn->last_change_us = now;
        return;
    }

    /* 一定時間安定していれば確定させる */
    if (value != btn->state && (now - btn->last_change_us) >= DEBOUNCE_US) {
        btn->state = value;
        btn->fell = !value; /* Low アクティブなので、Low への変化が「押された」 */
        btn->rose = value;
    }
}
