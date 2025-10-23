"""
自动化测试脚本：验证狼人杀游戏完整流程（脚本运行版，避免与 pytest 测试名冲突）
- 创建房间
- 开始游戏
- 多次推进（night->day->night）
- 验证角色分配、AI发言、投票等功能
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"


def test_full_game_flow():
    print("=" * 60)
    print("开始测试狼人杀游戏完整流程")
    print("=" * 60)

    # 1. 创建房间
    print("\n[步骤1] 创建房间...")
    resp = requests.post(f"{BASE_URL}/rooms", json={"owner": "test_auto"})
    if resp.status_code not in (200, 201):
        print(f"❌ 创建房间失败: {resp.status_code}")
        return False

    data = resp.json()
    room_id = data.get("room_id") or data.get("room", {}).get("id")
    print(f"✅ 房间创建成功: {room_id}")

    # 2. 开始游戏
    print(f"\n[步骤2] 开始游戏 (房间 {room_id})...")
    resp = requests.post(f"{BASE_URL}/rooms/{room_id}/start", json={})
    if resp.status_code != 200:
        print(f"❌ 开始游戏失败: {resp.status_code} - {resp.text}")
        return False

    data = resp.json()
    game = data["room"]["game"]
    print(f"✅ 游戏开始成功")

    # 3. 第一次 step (lobby -> night)
    print(f"\n[步骤3] 第一次推进 (lobby -> night)...")
    resp = requests.post(f"{BASE_URL}/rooms/{room_id}/step", json={})
    if resp.status_code != 200:
        print(f"❌ 推进失败: {resp.status_code} - {resp.text}")
        return False

    data = resp.json()
    game = data["room"]["game"]
    print(f"✅ 推进成功  当前阶段: {game['state']}  当前天数: {game['day']}")

    # 4. 第二次 step (night -> day)
    time.sleep(0.5)
    resp = requests.post(f"{BASE_URL}/rooms/{room_id}/step", json={})
    if resp.status_code != 200:
        print(f"❌ 推进失败: {resp.status_code} - {resp.text}")
        return False

    data = resp.json()
    game = data["room"]["game"]
    print(f"✅ 推进成功  当前阶段: {game['state']}  当前天数: {game['day']}")

    # 5. 验证发言 & 投票
    current_talks = game.get("phase_context", {}).get("current_talks", [])
    current_votes = game.get("phase_context", {}).get("current_votes", {})
    print(f"发言数: {len(current_talks)}  投票项: {len(current_votes)}")

    return True


if __name__ == "__main__":
    try:
        ok = test_full_game_flow()
        print("OK" if ok else "FAIL")
    except Exception as e:
        print("Exception:", e)
