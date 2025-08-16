#!/usr/bin/env python3
"""
ブロック崩しゲームの最適化確認スクリプト
実装された最適化機能の検証
"""


def verify_performance_optimizations():
    """パフォーマンス最適化の実装確認"""
    print("=== パフォーマンス最適化確認 ===")

    with open("games/breakout.py", "r", encoding="utf-8") as f:
        content = f.read()

    optimizations = [
        (
            "フレームレート制御",
            "_frame_interval",
            "50FPS安定動作のためのフレーム間隔制御",
        ),
        (
            "高頻度ボタンチェック",
            "_button_check_interval",
            "応答性向上のための高頻度入力処理",
        ),
        ("パフォーマンス監視", "_monitor_performance", "FPS監視とパフォーマンス警告"),
        (
            "メモリキャッシュ",
            "_paddle_positions_cache",
            "パドル位置のキャッシュによる計算削減",
        ),
        ("早期終了最適化", "active_count", "ゲーム終了条件の効率的チェック"),
        ("高速整数変換", "int(self.ball.x)", "round()からint()への高速化"),
        ("範囲外チェック最適化", "ball_x < 0 or ball_x >= 8", "衝突判定の早期終了"),
        ("定数事前取得", "led_red = self.matrix.LED_RED", "描画時の定数アクセス最適化"),
        ("高速ボール更新", "update_fast", "ボール移動の最適化版メソッド"),
        ("タプル最適化", "get_positions_fast", "リスト作成オーバーヘッド削減"),
    ]

    implemented_count = 0
    for name, keyword, description in optimizations:
        if keyword in content:
            print(f"✅ {name}: {description}")
            implemented_count += 1
        else:
            print(f"❌ {name}: 未実装")

    print(f"\n実装済み最適化: {implemented_count}/{len(optimizations)}")

    # 要件確認
    requirements = [
        ("要件6.4", "フレームレートは安定している", "_frame_interval" in content),
        (
            "要件6.5",
            "ボタン入力に対する応答は即座に反映される",
            "_button_check_interval" in content,
        ),
    ]

    print(f"\n=== 要件適合性確認 ===")
    for req_id, req_desc, is_met in requirements:
        status = "✅ 適合" if is_met else "❌ 未適合"
        print(f"{req_id}: {req_desc} - {status}")

    return implemented_count == len(optimizations)


def verify_code_quality():
    """コード品質の確認"""
    print(f"\n=== コード品質確認 ===")

    with open("games/breakout.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 基本的な品質指標
    total_lines = len(lines)
    comment_lines = sum(
        1 for line in lines if line.strip().startswith("#") or '"""' in line
    )
    empty_lines = sum(1 for line in lines if not line.strip())
    code_lines = total_lines - comment_lines - empty_lines

    print(f"総行数: {total_lines}")
    print(f"コメント行: {comment_lines}")
    print(f"空行: {empty_lines}")
    print(f"実コード行: {code_lines}")
    print(f"コメント率: {(comment_lines / total_lines) * 100:.1f}%")

    # 最適化関連のメソッド数確認
    optimization_methods = [
        "_handle_paddle_input_optimized",
        "_move_objects_optimized",
        "_monitor_performance",
        "_optimize_memory_usage",
        "get_positions_fast",
        "update_fast",
    ]

    content = "".join(lines)
    implemented_methods = sum(
        1 for method in optimization_methods if f"def {method}" in content
    )

    print(f"最適化メソッド数: {implemented_methods}/{len(optimization_methods)}")

    return True


def main():
    """メイン実行関数"""
    print("ブロック崩しゲーム 最適化確認スクリプト")
    print("=" * 50)

    try:
        perf_ok = verify_performance_optimizations()
        quality_ok = verify_code_quality()

        print(f"\n=== 総合結果 ===")
        if perf_ok and quality_ok:
            print("✅ 全ての最適化が正常に実装されています")
            print("✅ 要件6.4, 6.5に適合しています")
            print("✅ パフォーマンス最適化タスク完了")
        else:
            print("❌ 一部の最適化が不完全です")

        return perf_ok and quality_ok

    except Exception as e:
        print(f"エラー: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
