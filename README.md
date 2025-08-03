# pico-led-display

Raspberry Pi Pico 2 WH で LED ディスプレイを制御するサンプルプロジェクトです。

---

## 前提・開発環境

- OS: Windows 11
- VS Code
  - 拡張機能: CircuitPython v2
- Python ライブラリ管理: uv
  - CircuitPython は uv で完全管理できませんが、パッケージ管理に利用します
- 使用ボード: Raspberry Pi Pico 2 WH（USB 接続）

---

## 使い方

### CIRCUITPY へのファイルコピー

1. VS Code のコマンドパレット（Ctrl+Shift+P）を開く
2. 「タスクの実行」または「Run Task」を選択
3. 「Copy code.py to CIRCUITPY」タスクを選択

これで、`code.py` が自動的に CIRCUITPY ドライブ直下にコピーされます。

> CIRCUITPY ドライブが接続されていない場合は、コピーは中止されます。

---

## 概要

LED マトリクス制御用の CircuitPython サンプルコードと、必要なライブラリ（`adafruit_ht16k33` など）を CIRCUITPY ドライブに配置することで、Raspberry Pi Pico 2 WH 上で動作させることができます。
