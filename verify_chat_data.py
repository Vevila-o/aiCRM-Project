#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
驗證聊天系統數據是否正確保存
"""

import os
import sys
import django
from pathlib import Path

# 設定 Django 環境
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiCRM.settings')

django.setup()

from myCRM.models import AiSuggection, Campaign, ChatRecord

def verify_data():
    """驗證數據保存"""
    
    print("=== 驗證聊天系統數據保存 ===")
    
    # 1. 檢查 AI 建議表
    print(f"\n1. AI 建議表 (AiSuggection):")
    suggestions = AiSuggection.objects.all().order_by('-suggectid')[:5]
    
    for suggestion in suggestions:
        print(f"   ID: {suggestion.suggectid}")
        print(f"   類別: {suggestion.categoryID}")
        print(f"   用戶: {suggestion.userID}")
        print(f"   建議: {suggestion.aiRecommedGuideline}")
        print(f"   預期成果: {suggestion.expectedResults}")
        print(f"   建議時間: {suggestion.suggestDate}")
        print("   " + "-" * 50)
    
    # 2. 檢查優惠券表
    print(f"\n2. 優惠券表 (Campaign):")
    campaigns = Campaign.objects.all().order_by('-campaignid')[:5]
    
    for campaign in campaigns:
        print(f"   ID: {campaign.campaignid}")
        print(f"   類型: {campaign.type}")
        print(f"   發放時間: {campaign.givetime}")
        print(f"   開始時間: {campaign.starttime}")
        print(f"   結束時間: {campaign.endtime}")
        print(f"   使用狀態: {campaign.isuse}")
        print("   " + "-" * 50)
    
    # 3. 檢查聊天記錄表
    print(f"\n3. 聊天記錄表 (ChatRecord):")
    chats = ChatRecord.objects.all().order_by('-chatID')[:3]
    
    for chat in chats:
        print(f"   ID: {chat.chatID}")
        print(f"   用戶ID: {chat.user_id}")
        print(f"   類別: {chat.categoryID}")
        print(f"   用戶問題: {(chat.userContent or '')[:100]}...")
        print(f"   AI 回覆: {(chat.aiContent or '')[:100]}...")
        print("   " + "-" * 50)
    
    # 統計信息
    print(f"\n=== 統計信息 ===")
    print(f"AI 建議總數: {AiSuggection.objects.count()}")
    print(f"優惠券總數: {Campaign.objects.count()}")
    print(f"聊天記錄總數: {ChatRecord.objects.count()}")

if __name__ == "__main__":
    verify_data()