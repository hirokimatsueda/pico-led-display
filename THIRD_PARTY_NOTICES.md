# サードパーティの著作権表示

このプロジェクトには、以下のソフトウェア由来のデータが含まれています。

## Adafruit CircuitPython HT16K33

`src/device/ht16k33.c` の 7 セグメント表示用フォントテーブル (`SEG_FONT`) は、
Adafruit CircuitPython HT16K33 ライブラリの `segments.py` にある `NUMBERS` テーブルを
そのまま使用しています。

同ライブラリは MIT ライセンスで提供されており、以下の条件に従って利用しています。

- 出典: https://github.com/adafruit/Adafruit_CircuitPython_HT16K33
- SPDX-FileCopyrightText: Radomir Dopieralski 2016 for Adafruit Industries
- SPDX-FileCopyrightText: Tony DiCola 2016 for Adafruit Industries
- SPDX-License-Identifier: MIT

```
MIT License

Copyright (c) 2016 Radomir Dopieralski for Adafruit Industries
Copyright (c) 2016 Tony DiCola for Adafruit Industries

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Raspberry Pi Pico SDK (pico_sdk_import.cmake)

リポジトリ直下の `pico_sdk_import.cmake` は、Raspberry Pi Pico SDK に同梱されている
`external/pico_sdk_import.cmake` をそのまま複製したものです (SDK を外部プロジェクトから
参照するための定型ファイルで、そのまま置くことが想定されています)。

BSD 3-Clause ライセンスで提供されており、著作権表示とライセンス条文はファイル先頭に
そのまま残してあります。

- 出典: https://github.com/raspberrypi/pico-sdk
- Copyright 2020 (c) 2020 Raspberry Pi (Trading) Ltd.
- SPDX-License-Identifier: BSD-3-Clause

なお、ビルドされるバイナリには Pico SDK 本体 (同じく BSD 3-Clause) のコードが含まれます。
SDK 自体はこのリポジトリには含めておらず、ビルド時に `~/.pico-sdk` から参照しています。

## 補足: 参照しているが複製ではないもの

`src/device/ht16k33.c` および `src/device/button.c` には、Adafruit のライブラリを参照した
旨のコメントが他にもありますが、それらが指しているのは次のような内容で、著作物性のある
表現の複製ではありません。

- HT16K33 のコマンド値 (発振器 ON / 表示 ON / 輝度) — チップのデータシート由来
- 表示 RAM のレイアウトや 7 セグの桁とアドレスの対応 — Adafruit 902 / 5599 の
  基板配線から決まる事実
- デバウンス時間 10ms — パラメータ値のみ (実装は独自)
