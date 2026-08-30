/*
 * このファイルの 7 セグメント用フォントテーブル (SEG_FONT) は、
 * Adafruit CircuitPython HT16K33 ライブラリ (MIT) の segments.py にある
 * NUMBERS テーブルをそのまま使用しています。
 *
 * SPDX-FileCopyrightText: Radomir Dopieralski 2016 for Adafruit Industries
 * SPDX-FileCopyrightText: Tony DiCola 2016 for Adafruit Industries
 * SPDX-License-Identifier: MIT
 *
 * 出典と全文は THIRD_PARTY_NOTICES.md を参照。
 */
#include <string.h>
#include "device/ht16k33.h"

#define CMD_OSCILLATOR_ON 0x21
#define CMD_BLINK_DISPLAY_ON 0x81 /* 表示 ON・点滅なし */
#define CMD_BRIGHTNESS 0xE0

/* 7セグのフォント (adafruit_ht16k33 の NUMBERS と同じ並び: 0-9, a-z, '-') */
static const uint8_t SEG_FONT[] = {
    0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F, /* 0-9 */
    0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71, 0x3D, 0x76, 0x30, 0x1E, /* a-j */
    0x40, 0x38, 0x40, 0x54, 0x5C, 0x73, 0x67, 0x50, 0x6D, 0x78, /* k-t */
    0x3E, 0x1C, 0x40, 0x40, 0x6E, 0x40,                         /* u-z */
    0x40,                                                       /* '-' */
};

/* 7セグの桁 0..3 に対応する表示 RAM の番地 */
static const uint8_t SEG_POSITIONS[4] = {0, 2, 6, 8};

static void write_cmd(ht16k33_t *dev, uint8_t cmd) {
    i2c_write_blocking(dev->i2c, dev->addr, &cmd, 1, false);
}

void ht16k33_init(ht16k33_t *dev, i2c_inst_t *i2c, uint8_t addr) {
    dev->i2c = i2c;
    dev->addr = addr;
    memset(dev->ram, 0, sizeof(dev->ram));

    write_cmd(dev, CMD_OSCILLATOR_ON);
    write_cmd(dev, CMD_BLINK_DISPLAY_ON);
    ht16k33_set_brightness(dev, 15);
    ht16k33_show(dev);
}

void ht16k33_set_brightness(ht16k33_t *dev, uint8_t brightness) {
    write_cmd(dev, CMD_BRIGHTNESS | (brightness & 0x0F));
}

void ht16k33_show(ht16k33_t *dev) {
    /* 先頭バイトは書き込み開始アドレス (0x00)、続けて表示 RAM 16 バイトを送る */
    uint8_t buf[17];
    buf[0] = 0x00;
    memcpy(&buf[1], dev->ram, sizeof(dev->ram));
    i2c_write_blocking(dev->i2c, dev->addr, buf, sizeof(buf), false);
}

void ht16k33_matrix_fill(ht16k33_t *dev, led_color_t color) {
    uint8_t green = (color & 0x02) ? 0xFF : 0x00;
    uint8_t red = (color & 0x01) ? 0xFF : 0x00;
    for (int x = 0; x < 8; x++) {
        dev->ram[2 * x] = green;
        dev->ram[2 * x + 1] = red;
    }
}

void ht16k33_matrix_set_pixel(ht16k33_t *dev, int x, int y, led_color_t color) {
    if (x < 0 || x > 7 || y < 0 || y > 7) {
        return;
    }
    uint8_t mask = (uint8_t)(1u << y);
    if (color & 0x02) {
        dev->ram[2 * x] |= mask;
    } else {
        dev->ram[2 * x] &= (uint8_t)~mask;
    }
    if (color & 0x01) {
        dev->ram[2 * x + 1] |= mask;
    } else {
        dev->ram[2 * x + 1] &= (uint8_t)~mask;
    }
}

led_color_t ht16k33_matrix_get_pixel(const ht16k33_t *dev, int x, int y) {
    if (x < 0 || x > 7 || y < 0 || y > 7) {
        return LED_OFF;
    }
    uint8_t mask = (uint8_t)(1u << y);
    int color = 0;
    if (dev->ram[2 * x] & mask) {
        color |= 0x02;
    }
    if (dev->ram[2 * x + 1] & mask) {
        color |= 0x01;
    }
    return (led_color_t)color;
}

void ht16k33_seg_clear(ht16k33_t *dev) {
    memset(dev->ram, 0, sizeof(dev->ram));
}

void ht16k33_seg_put_char(ht16k33_t *dev, int index, char c) {
    if (index < 0 || index > 3) {
        return;
    }
    uint8_t addr = SEG_POSITIONS[index];

    if (c == '.') {
        dev->ram[addr] |= 0x80; /* 小数点は最上位ビット */
        return;
    }
    if (c == ' ') {
        dev->ram[addr] = 0x00;
        return;
    }

    int font_index;
    if (c >= '0' && c <= '9') {
        font_index = c - '0';
    } else if (c >= 'a' && c <= 'z') {
        font_index = c - 'a' + 10;
    } else if (c >= 'A' && c <= 'Z') {
        font_index = c - 'A' + 10;
    } else if (c == '-') {
        font_index = 36;
    } else {
        return; /* 表示できない文字は無視 */
    }
    dev->ram[addr] = SEG_FONT[font_index];
}

void ht16k33_seg_print(ht16k33_t *dev, const char *text) {
    ht16k33_seg_clear(dev);
    if (text == NULL) {
        return;
    }

    /* CircuitPython 版の print() は 1 文字ずつ左へスクロールさせるため右詰めになる */
    size_t len = strlen(text);
    size_t start = (len > 4) ? (len - 4) : 0; /* 4 文字を超える分は先頭から溢れる */
    int index = (int)(4 - (len - start));
    for (size_t i = start; i < len; i++) {
        ht16k33_seg_put_char(dev, index++, text[i]);
    }
}
