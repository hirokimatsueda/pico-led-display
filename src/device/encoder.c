#include "device/encoder.h"
#include "hardware/gpio.h"
#include "hardware/sync.h"

/*
 * グレイコードの遷移表。前回の (A,B) と今回の (A,B) の 4 ビットから
 * +1 / -1 / 0 を引く。ありえない遷移 (2 ビット同時変化) は 0 として捨てる。
 */
static const int8_t TRANSITION_TABLE[16] = {
    0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0,
};

static uint enc_pin_a;
static uint enc_pin_b;
static volatile int32_t quarter_position;
static volatile uint8_t prev_state;

static void encoder_irq(uint gpio, uint32_t events) {
    (void)gpio;
    (void)events;

    uint8_t state = (uint8_t)((gpio_get(enc_pin_a) << 1) | gpio_get(enc_pin_b));
    uint8_t index = (uint8_t)((prev_state << 2) | state);
    quarter_position += TRANSITION_TABLE[index & 0x0F];
    prev_state = state;
}

void encoder_init(uint pin_a, uint pin_b) {
    enc_pin_a = pin_a;
    enc_pin_b = pin_b;

    gpio_init(pin_a);
    gpio_set_dir(pin_a, GPIO_IN);
    gpio_pull_up(pin_a);
    gpio_init(pin_b);
    gpio_set_dir(pin_b, GPIO_IN);
    gpio_pull_up(pin_b);

    prev_state = (uint8_t)((gpio_get(pin_a) << 1) | gpio_get(pin_b));
    quarter_position = 0;

    gpio_set_irq_enabled_with_callback(pin_a, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true,
                                       &encoder_irq);
    gpio_set_irq_enabled(pin_b, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true);
}

int32_t encoder_position(void) {
    uint32_t save = save_and_disable_interrupts();
    int32_t quarters = quarter_position;
    restore_interrupts(save);

    /* 1 クリックは 4 クォーターステップ。負値でも一貫するよう算術シフトで丸める */
    return quarters >> 2;
}
