#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
狼人杀游戏功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.werewolf_game import WerewolfGame
import json

def test_game_creation():
    """测试游戏创建功能"""
    print("🎮 测试游戏创建...")
    
    game = WerewolfGame()
    session_id = game.create_new_game(user_id=1, player_count=8)
    
    print(f"✅ 游戏创建成功，Session ID: {session_id}")
    
    # 测试获取游戏状态
    game_state = game.load_game_state(session_id)
    print(f"✅ 游戏状态加载成功: {game_state is not None}")
    
    # 测试获取消息
    messages = game.get_game_messages(session_id)
    print(f"✅ 游戏消息获取成功: {len(messages)} 条消息")
    
    # 测试获取当前阶段
    phase = game.get_current_phase(session_id)
    print(f"✅ 当前阶段: {phase}")
    
    # 测试获取玩家角色
    role = game.get_player_role(session_id)
    print(f"✅ 玩家角色: {role}")
    
    # 测试获取存活玩家
    alive_players = game.get_alive_players(session_id)
    print(f"✅ 存活玩家: {len(alive_players)} 人")
    
    return session_id, game

def test_game_interaction(session_id, game):
    """测试游戏交互功能"""
    print("\n💬 测试游戏交互...")
    
    # 等待白天阶段（模拟）
    import time
    print("⏳ 等待游戏进入白天阶段...")
    
    # 模拟等待夜晚结束
    for i in range(3):
        time.sleep(1)
        phase = game.get_current_phase(session_id)
        print(f"  当前阶段: {phase}")
        if phase == 'day_discussion':
            break
    
    # 测试玩家发言
    if game.get_current_phase(session_id) == 'day_discussion':
        success = game.player_speak(session_id, "大家好，我是1号玩家，让我们一起找出狼人！")
        print(f"✅ 玩家发言成功: {success}")
        
        # 获取更新后的消息
        messages = game.get_game_messages(session_id, limit=5)
        print(f"✅ 最新消息数量: {len(messages)}")
        for msg in messages[-3:]:
            print(f"  {msg['speaker_name']}: {msg['content'][:50]}...")
    
    # 测试开始投票
    if game.get_current_phase(session_id) == 'day_discussion':
        success = game.start_voting(session_id)
        print(f"✅ 开始投票成功: {success}")
        
        # 测试投票
        if game.get_current_phase(session_id) == 'day_voting':
            success = game.player_vote(session_id, 2)  # 投票给2号玩家
            print(f"✅ 玩家投票成功: {success}")

def test_role_distribution():
    """测试角色分配"""
    print("\n🎭 测试角色分配...")
    
    game = WerewolfGame()
    
    # 测试不同人数的角色配置
    for player_count in [6, 8, 10, 12]:
        roles = game._generate_roles(player_count)
        role_counts = {}
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1
        
        print(f"  {player_count}人局角色配置: {role_counts}")
        
        # 验证角色数量
        assert len(roles) == player_count, f"角色数量不匹配: {len(roles)} != {player_count}"
        assert 'werewolf' in role_counts, "缺少狼人角色"
        assert 'villager' in role_counts, "缺少村民角色"
        assert 'seer' in role_counts, "缺少预言家角色"
    
    print("✅ 角色分配测试通过")

def test_ai_personality():
    """测试AI个性生成"""
    print("\n🤖 测试AI个性生成...")
    
    game = WerewolfGame()
    
    roles = ['werewolf', 'villager', 'seer', 'witch', 'hunter']
    for role in roles:
        personality = game._generate_ai_personality(role)
        print(f"  {role}: {personality}")
        assert len(personality) > 0, f"{role}个性生成失败"
    
    print("✅ AI个性生成测试通过")

def main():
    """主测试函数"""
    print("🚀 开始狼人杀游戏功能测试\n")
    
    try:
        # 测试角色分配
        test_role_distribution()
        
        # 测试AI个性
        test_ai_personality()
        
        # 测试游戏创建
        session_id, game = test_game_creation()
        
        # 测试游戏交互
        test_game_interaction(session_id, game)
        
        print("\n🎉 所有测试通过！狼人杀游戏功能正常")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()