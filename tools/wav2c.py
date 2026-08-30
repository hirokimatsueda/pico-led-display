#!/usr/bin/env python3
"""
WAV ファイルを C の配列に変換する。

audio_play_sample() が扱う符号付き 8bit モノラルの PCM として出力する。
生成したヘッダをインクルードすればフラッシュに焼き込まれ、XIP でそのまま
再生されるので RAM を消費しない。

サンプリングレートは変換せず、元のレートをそのままヘッダに書き出す
(再生側が位相の進みで合わせるため、任意のレートで鳴らせる)。

使い方:
    python tools/wav2c.py explosion.wav src/game/sfx_explosion.h
"""

import argparse
import array
import re
import sys
import wave
from pathlib import Path


def read_samples(path):
    """WAV を読み、-128..127 に正規化したモノラルのサンプル列を返す"""
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        raw = wav.readframes(wav.getnframes())

    if width == 1:
        # 8bit WAV だけは符号なし
        samples = [b - 128 for b in raw]
    elif width == 2:
        buf = array.array("h")
        buf.frombytes(raw)
        if sys.byteorder == "big":
            buf.byteswap()  # WAV はリトルエンディアン
        samples = [v >> 8 for v in buf]
    elif width == 3:
        samples = [
            int.from_bytes(raw[i : i + 3], "little", signed=True) >> 16
            for i in range(0, len(raw) - 2, 3)
        ]
    elif width == 4:
        buf = array.array("i")
        buf.frombytes(raw)
        if sys.byteorder == "big":
            buf.byteswap()
        samples = [v >> 24 for v in buf]
    else:
        raise ValueError(f"未対応のサンプル幅です: {width * 8}bit")

    if channels > 1:
        # 全チャンネルを平均してモノラルに落とす
        frames = len(samples) // channels
        samples = [
            sum(samples[i * channels : (i + 1) * channels]) // channels
            for i in range(frames)
        ]

    samples = [max(-128, min(127, v)) for v in samples]
    return samples, rate


def to_symbol(path):
    """ファイル名から C の識別子を作る"""
    stem = re.sub(r"[^0-9a-zA-Z]+", "_", Path(path).stem).strip("_").lower()
    if not stem or stem[0].isdigit():
        stem = "sfx_" + stem
    return stem


def write_header(out_path, symbol, samples, rate):
    lines = [
        f"/* {symbol}: 自動生成 ({rate} Hz, {len(samples)} サンプル) */",
        "#pragma once",
        "",
        "#include <stdint.h>",
        "",
        f"#define {symbol.upper()}_RATE {rate}",
        f"#define {symbol.upper()}_LENGTH {len(samples)}",
        "",
        f"static const int8_t {symbol}[] = {{",
    ]
    for i in range(0, len(samples), 16):
        chunk = ", ".join(str(v) for v in samples[i : i + 16])
        lines.append(f"    {chunk},")
    lines.append("};")
    lines.append("")

    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="入力 WAV ファイル")
    parser.add_argument("output", help="出力 C ヘッダ")
    parser.add_argument("--name", help="生成する配列名 (既定はファイル名から)")
    args = parser.parse_args()

    samples, rate = read_samples(args.input)
    symbol = args.name or to_symbol(args.input)
    write_header(args.output, symbol, samples, rate)

    kib = len(samples) / 1024
    seconds = len(samples) / rate if rate else 0
    print(
        f"{args.input} -> {args.output}"
        f"  ({symbol}, {kib:.1f} KiB, {rate} Hz, {seconds:.2f} 秒)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
