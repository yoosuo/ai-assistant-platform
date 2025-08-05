#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生产环境启动文件
用于Gunicorn部署
"""

import os
import sys

# 添加项目路径到Python路径
project_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_dir)
sys.path.insert(0, parent_dir)

# 导入应用
from app import create_app

# 创建应用实例
app = create_app('production')

if __name__ == '__main__':
    # 直接运行时的配置（开发环境）
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )