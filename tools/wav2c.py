#!/usr/bin/env python3
"""
WAV ファイルを C の配列に変換する。

audio_play_sample() が扱う符号付き 8bit モノラルの PCM として出力する。
生成したヘッダをインクルードすればフラッシュに焼き込まれ、XIP でそのまま
再生されるので RAM を消費しない。

使い方:
    python tools/wav2c.py explosion.wav src/game/sfx_explosion.h
"""

import argparse
import audioop
import sys
import wave


def convert(src_path: str, dst_path: str, name: str | None = None) -> None:
    with wave.open(src_path, "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    # モノラル・符号付き 8bit に揃える
    if channels > 1:
        frames = audioop.tomono(frames, width, 0.5, 0.5)
    if width != 1:
        frames = audioop.lin2lin(frames, width, 1)
    else:
        # 8bit WAV は符号なしなので符号付きに直す
        frames = audioop.bias(frames, 1, -128)

    symbol = name or "sfx_" + "".join(c if c.isalnum() else "_" for c in src_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]).lower()

    lines = [
        "/* {} から自動生成 ({} Hz, {} サンプル) */".format(src_path, rate, len(frames)),
        "#pragma once",
        "#include <stdint.h>",
        "",
        "#define {}_RATE {}".format(symbol.upper(), rate),
        "#define {}_LENGTH {}".format(symbol.upper(), len(frames)),
        "",
        "static const int8_t {}[] = {{".format(symbol),
    ]
    for i in range(0, len(frames), 16):
        chunk = frames[i : i + 16]
        values = ", ".join(str(b - 256 if b > 127 else b) for b in chunk)
        lines.append("    " + values + ",")
    lines.append("};")
    lines.append("")

    with open(dst_path, "w", encoding="utf-8") as out:
        out.write("\n".join(lines))

    kib = len(frames) / 1024
    print("{} -> {} ({:.1f} KiB, {} Hz)".format(src_path, dst_path, kib, rate))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="入力 WAV ファイル")
    parser.add_argument("output", help="出力 C ヘッダ")
    parser.add_argument("--name", help="生成する配列名", default=None)
    args = parser.parse_args()

    convert(args.input, args.output, args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
