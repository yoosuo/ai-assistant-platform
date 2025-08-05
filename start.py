#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能AI工具平台启动文件
"""

import os
import sys
from app import create_app
from config import Config

def main():
    """主函数"""
    print("🚀 智能AI工具平台启动中...")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 错误: 需要Python 3.7或更高版本")
        sys.exit(1)
    
    # 创建必要的目录
    os.makedirs('data', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    # 检查配置
    config_file = Config.CONFIG_FILE
    if not os.path.exists(config_file):
        print("⚠️  未检测到配置文件，请先访问 /config 页面进行配置")
    
    # 创建Flask应用
    app = create_app()
    
    print(f"🌟 服务器启动成功！")
    print(f"📍 访问地址: http://{Config.HOST}:{Config.PORT}")
    print(f"⚙️  配置页面: http://{Config.HOST}:{Config.PORT}/config")
    print(f"🔧 调试模式: {'开启' if Config.DEBUG else '关闭'}")
    print("=" * 50)
    print("💡 提示:")
    print("   1. 首次使用请先访问配置页面设置API密钥")
    print("   2. 支持阿里云百炼和OpenRouter双平台")
    print("   3. 按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        # 启动服务器
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
            use_reloader=False  # 避免重复启动消息
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()