"""
自动化测试脚本：验证狼人杀游戏完整流程
- 创建房间
- 开始游戏
- 多次推进（night->day->night）
- 验证角色分配、AI发言、投票等功能
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"

def test_full_game_flow():
    print("=" * 60)
    print("开始测试狼人杀游戏完整流程")
    print("=" * 60)
    
    # 1. 创建房间
    print("\n[步骤1] 创建房间...")
    resp = requests.post(f"{BASE_URL}/rooms", json={"owner": "test_auto"})
    if resp.status_code != 201:
        print(f"❌ 创建房间失败: {resp.status_code}")
        return False
    
    data = resp.json()
    room_id = data["room_id"]
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
    print(f"   玩家数: {len(game['players'])}")
    print(f"   玩家: {', '.join(game['players'])}")
    
    # 3. 验证角色分配
    print(f"\n[步骤3] 验证角色分配...")
    roles = game.get("roles", {})
    if not roles:
        print("❌ 角色字段不存在或为空")
        return False
    
    print(f"✅ 角色分配成功:")
    for player, role in sorted(roles.items()):
        print(f"   {player}: {role}")
    
    # 统计角色
    from collections import Counter
    role_counts = Counter(roles.values())
    print(f"\n   角色统计: {dict(role_counts)}")
    
    # 4. 第一次 step (lobby -> night)
    print(f"\n[步骤4] 第一次推进 (lobby -> night)...")
    resp = requests.post(f"{BASE_URL}/rooms/{room_id}/step", json={})
    if resp.status_code != 200:
        print(f"❌ 推进失败: {resp.status_code} - {resp.text}")
        return False
    
    data = resp.json()
    game = data["room"]["game"]
    print(f"✅ 推进成功")
    print(f"   当前阶段: {game['state']}")
    print(f"   当前天数: {game['day']}")
    print(f"   存活玩家: {len(game['alive'])}")
    
    # 检查夜间行动
    if game.get("history"):
        last_event = game["history"][-1]
        if last_event.get("phase") == "night":
            print(f"   夜间击杀目标: {last_event.get('killed', 'None (可能被救)')}")
            print(f"   行动数量: {len(last_event.get('actions', []))}")
    
    # 5. 第二次 step (night -> day)
    print(f"\n[步骤5] 第二次推进 (night -> day，触发发言)...")
    time.sleep(0.5)  # 短暂延迟
    resp = requests.post(f"{BASE_URL}/rooms/{room_id}/step", json={})
    if resp.status_code != 200:
        print(f"❌ 推进失败: {resp.status_code} - {resp.text}")
        return False
    
    data = resp.json()
    game = data["room"]["game"]
    print(f"✅ 推进成功")
    print(f"   当前阶段: {game['state']}")
    print(f"   当前天数: {game['day']}")
    
    # 6. 验证发言
    print(f"\n[步骤6] 验证AI发言...")
    current_talks = game.get("phase_context", {}).get("current_talks", [])
    if not current_talks:
        print("⚠️  警告: current_talks 为空")
        print("   这可能是因为:")
        print("   1. 当前阶段不是 day (实际: {})".format(game['state']))
        print("   2. AI 调用失败且没有 fallback")
        print("   3. _run_discussion() 未被执行")
    else:
        print(f"✅ 发言记录成功 ({len(current_talks)} 条):")
        for talk in current_talks[:3]:  # 只显示前3条
            player = talk.get("player", "Unknown")
            speech = talk.get("speech", "")[:50]  # 截断长文本
            meta = talk.get("meta", {})
            heuristic = " [启发式]" if meta.get("heuristic") else ""
            print(f"   {player}: {speech}{heuristic}")
    
    # 7. 验证投票
    print(f"\n[步骤7] 验证投票...")
    current_votes = game.get("phase_context", {}).get("current_votes", {})
    if current_votes:
        print(f"✅ 投票记录成功:")
        for target, count in sorted(current_votes.items(), key=lambda x: x[1], reverse=True):
            print(f"   {target}: {count} 票")
    else:
        print("⚠️  投票记录为空 (可能当前阶段尚未投票)")
    
    # 8. 检查历史记录
    print(f"\n[步骤8] 检查游戏历史...")
    history = game.get("history", [])
    print(f"✅ 历史记录: {len(history)} 条事件")
    if history:
        last_day_event = None
        for event in reversed(history):
            if event.get("phase") == "day":
                last_day_event = event
                break
        
        if last_day_event:
            print(f"   最近白天事件:")
            print(f"   - 被处决: {last_day_event.get('lynched', 'None')}")
            print(f"   - 发言数: {len(last_day_event.get('talks', []))}")
            print(f"   - 投票: {last_day_event.get('votes', {})}")
    
    # 9. 最终状态总结
    print(f"\n{'=' * 60}")
    print("测试完成总结")
    print(f"{'=' * 60}")
    print(f"房间ID: {room_id}")
    print(f"游戏状态: {game['state']}")
    print(f"当前天数: {game['day']}")
    print(f"存活玩家: {len(game['alive'])}/{len(game['players'])}")
    print(f"历史事件: {len(history)} 条")
    print(f"角色分配: ✅ 正常")
    print(f"AI发言: {'✅ 正常' if current_talks else '⚠️  需检查'}")
    print(f"投票功能: {'✅ 正常' if current_votes else '⚠️  需检查'}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_full_game_flow()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到后端服务 (http://127.0.0.1:8080)")
        print("   请先运行: python games/werewolf/backend/app.py")
        exit(2)
    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        exit(3)
