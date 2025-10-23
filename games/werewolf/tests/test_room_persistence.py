"""
测试房间持久化和生命周期管理
验证房间创建后不会意外消失的问题
"""
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), "games", "werewolf", "backend"))

import time
import requests
import json

BASE_URL = "http://localhost:5000"

def test_room_persistence():
    """测试房间在创建后是否持久存在"""
    print("\n=== 测试1: 房间持久化 ===")
    
    # 1. 创建房间
    print("1. 创建房间...")
    resp = requests.post(f"{BASE_URL}/rooms", json={"owner": "TestOwner", "max_players": 6})
    assert resp.status_code in [200, 201], f"创建失败: {resp.status_code}"
    data = resp.json()
    room_id = data.get("room_id") or data.get("room", {}).get("id")
    assert room_id, "未返回房间ID"
    print(f"   ✓ 房间已创建: {room_id}")
    
    # 2. 立即查询房间列表
    print("2. 查询房间列表...")
    resp = requests.get(f"{BASE_URL}/rooms")
    rooms = resp.json().get("rooms", [])
    assert len(rooms) > 0, "房间列表为空!"
    assert any(r["id"] == room_id for r in rooms), f"房间 {room_id} 不在列表中"
    print(f"   ✓ 房间列表包含 {room_id}")
    
    # 3. 多次查询,验证房间不会消失
    print("3. 多次查询验证持久化...")
    for i in range(5):
        time.sleep(0.5)
        resp = requests.get(f"{BASE_URL}/rooms")
        rooms = resp.json().get("rooms", [])
        assert len(rooms) > 0, f"第{i+1}次查询时房间列表为空!"
        assert any(r["id"] == room_id for r in rooms), f"第{i+1}次查询时房间 {room_id} 消失了!"
    print(f"   ✓ 房间在5次查询后仍然存在")
    
    # 4. 查询房间状态
    print("4. 查询房间状态...")
    resp = requests.get(f"{BASE_URL}/rooms/{room_id}/state")
    assert resp.status_code == 200, f"查询状态失败: {resp.status_code}"
    state = resp.json()
    assert state["id"] == room_id, "房间ID不匹配"
    assert state["state"] == "waiting", f"房间状态异常: {state['state']}"
    print(f"   ✓ 房间状态正常: {state['state']}")
    
    # 5. 再次查询房间列表,验证查询状态后房间不会消失
    print("5. 验证查询状态后房间仍存在...")
    resp = requests.get(f"{BASE_URL}/rooms")
    rooms = resp.json().get("rooms", [])
    assert any(r["id"] == room_id for r in rooms), "查询状态后房间消失了!"
    print(f"   ✓ 房间仍然存在")
    
    print("\n✅ 测试1通过: 房间持久化正常\n")

def test_single_room_policy():
    """测试单房间策略"""
    print("\n=== 测试2: 单房间策略 ===")
    
    # 1. 创建第一个房间
    print("1. 创建第一个房间...")
    resp = requests.post(f"{BASE_URL}/rooms", json={"owner": "Owner1", "max_players": 6})
    data = resp.json()
    room_id_1 = data.get("room_id") or data.get("room", {}).get("id")
    print(f"   ✓ 房间1: {room_id_1}")
    
    # 2. 尝试创建第二个房间(应返回第一个房间ID)
    print("2. 尝试创建第二个房间...")
    resp = requests.post(f"{BASE_URL}/rooms", json={"owner": "Owner2", "max_players": 6})
    data = resp.json()
    room_id_2 = data.get("room_id") or data.get("room", {}).get("id")
    assert room_id_2 == room_id_1, f"单房间策略失败: 返回了新房间 {room_id_2} 而不是复用 {room_id_1}"
    print(f"   ✓ 复用了房间1: {room_id_2}")
    
    # 3. 查询房间列表,应只有一个房间
    print("3. 验证只有一个活跃房间...")
    resp = requests.get(f"{BASE_URL}/rooms")
    rooms = resp.json().get("rooms", [])
    active_rooms = [r for r in rooms if r["state"] != "ended"]
    assert len(active_rooms) == 1, f"应只有1个活跃房间,实际有 {len(active_rooms)} 个"
    print(f"   ✓ 只有1个活跃房间")
    
    print("\n✅ 测试2通过: 单房间策略正常\n")

def test_room_lifecycle():
    """测试房间生命周期(waiting -> running -> ended)"""
    print("\n=== 测试3: 房间生命周期 ===")
    
    # 1. 创建房间
    print("1. 创建房间...")
    resp = requests.post(f"{BASE_URL}/rooms", json={"owner": "LifecycleOwner", "max_players": 6})
    data = resp.json()
    room_id = data.get("room_id") or data.get("room", {}).get("id")
    
    # 2. 验证初始状态为waiting
    print("2. 验证初始状态...")
    resp = requests.get(f"{BASE_URL}/rooms/{room_id}/state")
    state = resp.json()
    assert state["state"] == "waiting", f"初始状态应为waiting,实际为 {state['state']}"
    print(f"   ✓ 初始状态: waiting")
    
    # 3. 加入AI玩家
    print("3. 加入AI玩家...")
    for i in range(5):
        resp = requests.post(f"{BASE_URL}/rooms/{room_id}/join", json={"player": f"AI_{i}"})
        assert resp.status_code == 200, f"加入玩家失败: {resp.status_code}"
    print(f"   ✓ 已加入5名AI玩家")
    
    # 4. 开始游戏
    print("4. 开始游戏...")
    resp = requests.post(f"{BASE_URL}/rooms/{room_id}/start")
    assert resp.status_code == 200, f"开始游戏失败: {resp.status_code}"
    
    # 5. 验证状态变为running
    print("5. 验证状态变为running...")
    resp = requests.get(f"{BASE_URL}/rooms/{room_id}/state")
    state = resp.json()
    assert state["state"] == "running", f"游戏状态应为running,实际为 {state['state']}"
    print(f"   ✓ 游戏状态: running")
    
    # 6. 验证房间仍在列表中
    print("6. 验证running状态房间仍在列表中...")
    resp = requests.get(f"{BASE_URL}/rooms")
    rooms = resp.json().get("rooms", [])
    assert any(r["id"] == room_id for r in rooms), "running状态房间从列表中消失了!"
    print(f"   ✓ 房间仍在列表中")
    
    print("\n✅ 测试3通过: 房间生命周期正常\n")

def main():
    print("=" * 60)
    print("房间持久化与生命周期测试")
    print("=" * 60)
    print("\n⚠️  请确保后端正在运行: python games/werewolf/backend/app.py")
    print(f"⚠️  后端地址: {BASE_URL}\n")
    
    try:
        # 测试后端连接
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        assert resp.status_code == 200, "后端未响应"
        print("✓ 后端连接正常\n")
    except Exception as e:
        print(f"❌ 无法连接到后端: {e}")
        print("   请先启动后端: python games/werewolf/backend/app.py")
        return 1
    
    try:
        test_room_persistence()
        test_single_room_policy()
        test_room_lifecycle()
        
        print("=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
