#!/bin/bash

# 构建 React Admin 前端
echo "开始构建 React Admin 前端..."

# 进入 admin 目录
cd admin

# 安装依赖（如果 node_modules 不存在）
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    pnpm install
fi

# 构建项目
echo "构建项目..."
pnpm run build

# 检查构建是否成功
if [ $? -eq 0 ]; then
    echo "✅ React Admin 前端构建成功！"
    echo "构建产物位于: admin/dist/"
    echo "现在可以通过 https://your-domain.com/admin 访问管理界面"
else
    echo "❌ 构建失败，请检查错误信息"
    exit 1
fi

cd .. 