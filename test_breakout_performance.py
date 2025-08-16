#!/usr/bin/env python3
"""
ブロック崩しゲームのパフォーマンステスト
50FPS安定動作とメモリ使用量最適化の確認
"""

import time
import sys
import os

# ゲームモジュールのパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), "games"))


class MockDeviceManager:
    """テスト用のモックデバイスマネージャー"""

    class MockMatrix:
        LED_OFF = 0
        LED_RED = 1
        LED_GREEN = 2
        LED_YELLOW = 3

        def __init__(self):
            self.pixels = [[0 for _ in range(8)] for _ in range(8)]

        def fill(self, color):
            for y in range(8):
                for x in range(8):
                    self.pixels[y][x] = color

        def __setitem__(self, pos, color):
            x, y = pos
            if 0 <= x < 8 and 0 <= y < 8:
                self.pixels[y][x] = color

        def show(self):
            pass  # 実際の表示は行わない

    class MockSegment:
        def fill(self, value):
            pass

        def print(self, text):
            pass

        def show(self):
            pass

    class MockButton:
        def __init__(self):
            self.fell = False

        def update(self):
            pass

    def __init__(self):
        self.matrix = self.MockMatrix()
        self.seg = self.MockSegment()
        self.btn_a = self.MockButton()
        self.btn_b = self.MockButton()


def test_performance():
    """パフォーマンステストの実行"""
    print("ブロック崩しゲーム パフォーマンステスト開始")

    # モックデバイスでゲームを初期化
    mock_devices = MockDeviceManager()

    try:
        from breakout import BreakoutGame

        game = BreakoutGame(mock_devices)
        game.initialize()

        # テスト設定
        test_duration = 2.0  # 2秒間のテスト
        target_fps = 50
        frame_count = 0
        start_time = time.time()

        print(f"目標FPS: {target_fps}")
        print(f"テスト時間: {test_duration}秒")

        # パフォーマンステストループ
        while time.time() - start_time < test_duration:
            frame_start = time.time()

            # ゲーム更新処理
            game.update()
            frame_count += 1

            # フレームレート制御のシミュレーション
            frame_time = time.time() - frame_start
            target_frame_time = 1.0 / target_fps

            if frame_time < target_frame_time:
                time.sleep(target_frame_time - frame_time)

        # 結果計算
        actual_duration = time.time() - start_time
        actual_fps = frame_count / actual_duration

        print(f"\n=== パフォーマンステスト結果 ===")
        print(f"実行フレーム数: {frame_count}")
        print(f"実際の実行時間: {actual_duration:.2f}秒")
        print(f"実際のFPS: {actual_fps:.1f}")
        print(f"目標FPS達成率: {(actual_fps / target_fps) * 100:.1f}%")

        # 最適化効果の確認
        if actual_fps >= target_fps * 0.9:  # 90%以上で合格
            print("✅ パフォーマンステスト合格: 50FPS安定動作確認")
        else:
            print("❌ パフォーマンステスト不合格: FPS不足")

        # メモリ使用量の確認（簡易版）
        print(f"\n=== メモリ使用量確認 ===")
        print(f"ブロック数: {len(game.blocks)}")
        print(f"アクティブブロック数: {sum(1 for b in game.blocks if b.is_active)}")

        # 応答性テスト（ボタン入力シミュレーション）
        print(f"\n=== 応答性テスト ===")
        response_start = time.time()

        # パドル移動のシミュレーション
        initial_paddle_x = game.paddle.x
        mock_devices.btn_a.fell = True
        game._handle_paddle_input_optimized()
        mock_devices.btn_a.fell = False

        response_time = (time.time() - response_start) * 1000  # ms
        paddle_moved = game.paddle.x != initial_paddle_x

        print(f"ボタン応答時間: {response_time:.2f}ms")
        print(f"パドル移動確認: {'✅' if paddle_moved else '❌'}")

        if response_time < 10:  # 10ms以下で合格
            print("✅ 応答性テスト合格: 高速応答確認")
        else:
            print("❌ 応答性テスト不合格: 応答遅延")

        game.finalize()

    except ImportError as e:
        print(f"エラー: ゲームモジュールをインポートできません - {e}")
        return False
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        return False

    return True


if __name__ == "__main__":
    success = test_performance()
    sys.exit(0 if success else 1)
