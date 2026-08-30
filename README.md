# pico-led-display

Raspberry Pi Pico 2 WH と HT16K33 8x8 LED マトリクスを使った、LED ディスプレイ制御ゲームのプロジェクトです。
2 つのボタンによる操作、HT16K33 4 桁 7 セグ LED への得点表示、ロータリーエンコーダーを用いたゲーム切り替え、
PAM8302A アンプによる効果音を実装しています。

ファームウェアは pico-sdk による C 実装です。
CircuitPython による実装は [`v1`](https://github.com/hirokimatsueda/pico-led-display/tree/v1) タグに残してあります。

## 前提・開発環境

- OS: Windows 11
- VS Code (拡張機能: Raspberry Pi Pico)
- ビルドツール: pico-sdk 2.3.0 / arm-none-eabi-gcc / CMake / Ninja
  (いずれも Pico 拡張機能が `~/.pico-sdk` に入れたものをそのまま使います)
- 使用ボード: Raspberry Pi Pico 2 WH (USB 接続)
  - 使用ピンと接続部品 (GND は明確なものは省略):
    - Adafruit 902 (HT16K33 8x8 LED マトリクス)
      - GP17 (SCL)
      - GP16 (SDA)
      - 3V3_OUT (VCC)
    - Adafruit 5599 (HT16K33 4 桁 7 セグ LED)
      - GP15 (SCL)
      - GP14 (SDA)
      - 3V3_OUT (VCC)
    - LP01-15CCKNS1M (押しボタン)
      - GP18 (N.O.)
      - GND (COM)
    - LP01-15CCKNS1R (押しボタン)
      - GP19 (N.O.)
      - GND (COM)
    - EC12E1220406 (ロータリーエンコーダー)
      - GP10 (A)
      - GP11 (B)
      - GND (C)
    - Adafruit 2130 (PAM8302A モノラルアンプ) + 4〜8Ω スピーカー
      - GP20 (PWM オーディオ出力) → RC フィルタ経由で A+
      - GND (A-)
      - VBUS (Vin) ※3V3_OUT でも鳴るが音量は下がる

### 効果音 (アンプ) の接続

Pico の GPIO から PWM で音声を出力し、PAM8302A で増幅してスピーカーを鳴らします。
PAM8302A はゲイン固定 24dB (×15.8) のため GPIO を直結すると完全にクリップします。
下図のように分圧 (約 1/11) とローパス (カットオフ約 17kHz) を兼ねた RC を挟んでください。

```
GP20 ──[10kΩ]──┬──→ A+
               │
             [1kΩ] ∥ [10nF]   ← 1kΩ と 10nF を並列に GND へ
               │
              GND              A- → GND
```

- 音量は基板上のトリムポットで調整します (ソフト側の調整は「音量の調整」を参照)
- スピーカーは Class-D の BTL 出力なので、出力の片側を GND に落とさないでください
- アンプの Vin 直近に 100µF 程度のコンデンサを入れると、LED と電源を共有したときの
  ノイズや電圧降下を抑えられます
- SD ピンは未接続で動作します (基板上でプルアップ済み)

## 使い方

### ビルド

VS Code のコマンドパレット (Ctrl+Shift+P) から「タスクの実行」→「Build firmware」を選ぶか、
直接以下を実行します。

```sh
pwsh -ExecutionPolicy Bypass -File ./build.ps1          # ビルド
pwsh -ExecutionPolicy Bypass -File ./build.ps1 -Clean   # build を消してから
```

SDK・ツールチェーン・Ninja・picotool は `~/.pico-sdk` 配下から自動検出します
(VS Code の Raspberry Pi Pico 拡張機能をインストールしておいてください)。

### 書き込み

1. BOOTSEL ボタンを押しながら Pico 2 WH を PC に接続
2. マウントされた RP2350 ドライブに `build/pico_led_display.uf2` をコピー

`printf()` の出力は USB シリアルに出るので、VS Code のシリアルモニタなどで確認できます。

## 構成

```
CMakeLists.txt         ビルド定義
build.ps1              ビルドスクリプト (~/.pico-sdk を自動検出)
src/
  main.c               FPS = 50 の固定タイムステップループ、ゲームのレジストリ
  device/
    device_manager.c   ピン定義と全デバイスの集約
    ht16k33.c          LED マトリクス / 7 セグのドライバ
    button.c           デバウンス
    encoder.c          ロータリーエンコーダー (GPIO 割り込みで 4 逓倍デコード)
    audio.c            PWM + DMA の多声ミキサー
  game/
    game.h             ゲームインターフェース (関数ポインタの表)
    selector.c         ゲームセレクター (通常モード / 選択モードの状態機械)
    bouncing_ball.c    ボールが跳ねるだけのデモ
    falling_dot.c      落ちてくるドットを避ける
    breakout.c         ブロック崩し
    bomb_defuse.c      爆弾解除 (ワイヤーの色を記憶して正解ボタンを押す)
    jump_runner.c      横スクロールのジャンプアクション (効果音つき)
tools/wav2c.py         WAV を C 配列に変換する
```

### 実測値

| | 使用量 |
|---|---|
| フラッシュ | **43.6 KiB** (`build/pico_led_display.bin`) / 4 MiB |
| 静的 RAM (bss) | **5.0 KiB** / 520 KiB |

音声データに約 3.95 MB 使えます (22050Hz / 8bit モノラルで約 3 分、11025Hz で約 6 分)。

## ゲームの操作

- **エンコーダーを回す** → ゲーム選択モードに入る (7 セグに `-NN-` 形式でゲーム番号を表示)
  - さらに回して選択、**ボタン A** で確定、**ボタン B** でキャンセル
  - 選択モード中も元のゲームは一時停止されるだけなので、キャンセルすれば続きから再開します
- ゲームオーバー後は **両ボタン同時押し** で再スタート (ゲームによる)

## 効果音

### 書き方

効果音は「(周波数, 長さ)」の並びによる簡易譜面で表現します。

```c
static const sfx_step_t SFX_JUMP_STEPS[] = {
    SFX_TONE(587, 35),        /* D5 を 35ms */
    SFX_SWEEP(784, 1175, 75), /* G5 -> D6 へ 75ms でスイープ */
};
static const sfx_t SFX_JUMP = SFX_DEF(SFX_JUMP_STEPS, AUDIO_WAVE_SQUARE, 255); /* 振幅 0..255 */

audio_play(&SFX_JUMP);
```

`SFX_TONE(周波数, ms)` / `SFX_SWEEP(開始, 終了, ms)` / `SFX_REST(ms)` の 3 種類を並べます。
波形は矩形波 / 三角波 / ノイズから選べます。同時発音数は 6 なので、鳴っている音の上に
別の音を重ねられます (衝突音はノイズの衝撃音と下降する三角波を重ねています)。

効果音データはゲーム間で共有せず、各ゲームのファイル内に置いてください
(`src/game/jump_runner.c` の先頭が例です)。

### 音づくりの方針

音程は D を中心とした 4 度堆積 (D - G - C - F) から選んでいます。この手のゲームで
定番の「長三和音の上昇アルペジオ」「完全 5 度の取得音」を避けることで、レトロな
音色は保ったまま響きだけを独自のものにする狙いです。ジャンプ系は「刻んだ音 +
スイープ」を共通のモチーフにして、通常ジャンプと大ジャンプが同じ仲間に聞こえる
ようにしてあります。

### WAV を焼き込む

録音した音を使いたい場合は、WAV を C 配列に変換してビルドに含めます。フラッシュから
XIP で直接再生されるため RAM は消費しません。

```sh
python tools/wav2c.py explosion.wav src/game/sfx_explosion.h
```

```c
#include "game/sfx_explosion.h"
audio_play_sample(sfx_explosion, SFX_EXPLOSION_LENGTH, SFX_EXPLOSION_RATE, 200);
```

### 音量の調整

出力レベルは「1 音でフルスケールの約 77% (±395/511)」になるよう設計してあります。
足りない / 大きすぎる場合は、次の順で調整してください。

**1. ソフト側 (再ビルドが必要)**

| 調整箇所 | 効果 |
|---|---|
| `audio_set_volume(0..255)` / `AUDIO_DEFAULT_VOLUME` (`src/device/audio.h`) | 全体の音量。下げる方向の調整はここが一番手軽 |
| 各効果音の `SFX_DEF(..., 振幅)` (0..255) | 効果音ごとの相対的な大きさ |
| `VOICE_SHIFT` / `LIMIT_KNEE` (`src/device/audio.c`) | 1 音あたりの最大レベルとリミッターの効き始め。触るのは最後の手段 |

**2. ハード側**

- **PAM8302A 基板のトリムポット** — まずここを上げる。入力側の減衰なので効きが大きい
- **アンプの Vin を VBUS (5V) にする** — 3V3 だと最大振幅が 6.6Vpp 程度に制限される
- **分圧比を変える** — 10kΩ/1kΩ (÷11) を 4.7kΩ/1kΩ (÷5.7) にすると約 +6dB。
  この場合はカットオフを保つためコンデンサを 10nF → 15nF に変えること
- スピーカーは口径が大きいほど、また箱に入れるほど体感音量が上がる

参考: ソフト側フルボリューム + 10kΩ/1kΩ 分圧 + ポット最大で、スピーカー端は約 3.7Vpp
(8Ω で約 0.2W) の計算になります。

### オーディオの内部

- PWM: GP20 を 10bit (wrap 1023) で駆動。キャリアは 150MHz / 1024 = **約 146kHz**
- サンプリングレート: 22050Hz。DMA タイマー (`clk_sys` の 1/6802) が DREQ を刻む
- バッファ: 256 サンプル × 2 面をチェーンで交互に再生 (1 面あたり 11.6ms)
- 割り込みで再生済みの面をミックスし直す。1 ボイス (振幅 255) で ±506 まで振れ、
  合計は ±340 を超えた分を 1/3 に圧縮するソフトリミッターで ±511 に収める。
  単音は大きく鳴らしつつ、重なった瞬間だけ穏やかに頭打ちになる
- スイープは 32 サンプル (約 1.45ms) ごとに周波数を再計算し、位相増分は Q16.16 固定小数点

ミックスは DMA 完了割り込みの中で行うため、メインループには音の処理が出てきません。
ゲーム側は `audio_play()` を投げっぱなしにできます。

## v1 (CircuitPython 版) について

`v1` タグに CircuitPython 実装が残っています。同じ 5 ゲーム・同じ配線で動作しますが、
C 版とは次の点が異なります。

- 効果音は `audiopwmio` + `synthio` による**単音**。新しい音を鳴らすと前の音が止まる
- ファームウェアがフラッシュの大半を占めるため、音声データを置く余裕がほとんどない
- `code.py` を CIRCUITPY ドライブにコピーするだけで動かせる手軽さがある

戻したい場合は CircuitPython の UF2 を焼き直し、`git checkout v1` で取り出してください。
