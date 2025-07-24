#!/bin/bash

# 环境设置脚本

echo "🔧 设置 Project2025-Backend开发环境..."

# 检查 Python 版本
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python 版本: $python_version"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "⬆️  升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js"
    exit 1
fi

# 检查 pnpm
if ! command -v pnpm &> /dev/null; then
    echo "📦 安装 pnpm..."
    npm install -g pnpm
fi

# 安装前端依赖
echo "📦 安装前端依赖..."
cd admin
pnpm install
cd ..

echo "✅ 环境设置完成！"
echo ""
echo "🚀 启动方式："
echo "  开发环境: ./start_development.sh"
echo "  生产环境: ./start_production.sh"
echo ""
echo "📝 其他命令："
echo "  构建前端: ./build_admin.sh"
echo "  停止服务: pkill -f gunicorn 或 pkill -f 'python run.py'" 