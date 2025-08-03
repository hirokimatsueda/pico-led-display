# pico-led-display

Raspberry Pi Pico 2 WH と Adafruit 902 (HT16K33 8x8 LED マトリクス) を使った、LED ディスプレイ制御のサンプルプロジェクトです。

## 前提・開発環境

- OS: Windows 11
- VS Code（拡張機能: CircuitPython v2）
- Python ライブラリ管理: uv（CircuitPython は uv で完全管理できませんが、パッケージ管理に利用）
- 使用ボード: Raspberry Pi Pico 2 WH（USB 接続）
  - 使用ピン:
    - GP17 (SCL)
    - GP16 (SDA)
    - 3V3_OUT (VCC)
- 使用ディスプレイ: Adafruit 902（HT16K33 8x8 LED マトリクス）
- CircuitPython バージョン: 9.2.8 で動作確認済み

## CircuitPython の導入（Pico 2 WH）

1. [CircuitPython 公式サイト](https://circuitpython.org/board/raspberry_pi_pico2_w/) にアクセス
2. 最新の CircuitPython UF2 ファイルをダウンロード
3. Pico 2 WH の BOOTSEL ボタンを押しながら PC に接続
4. マウントされた RPI-RP2 ドライブに UF2 ファイルをコピー
5. CIRCUITPY ドライブが現れたら導入完了

## 使い方

### CIRCUITPY へのファイルコピー

1. VS Code のコマンドパレット（Ctrl+Shift+P）を開く
2. 「タスクの実行」または「Run Task」を選択
3. 「Copy code.py to CIRCUITPY」タスクを選択

これで `code.py` が自動的に CIRCUITPY ドライブ直下にコピーされます。

> CIRCUITPY ドライブが接続されていない場合は、コピーは中止されます。

## 概要・補足

LED マトリクス制御用の CircuitPython サンプルコードと、必要なライブラリ（`adafruit_ht16k33` など）を CIRCUITPY ドライブに配置することで、Raspberry Pi Pico 2 WH 上で動作させることができます。
