#!/bin/bash
# 好时间 · 一键启动本地服务 + HTTPS 隧道
# 双击运行（首次需在“访达”右键→打开，或 chmod +x start.command）
cd "$(dirname "$0")"

echo "正在启动「好时间」..."
# 关闭可能已存在的旧服务
pkill -f "http.server 8000" 2>/dev/null
sleep 1

# 启动本地静态服务器
python3 -m http.server 8000 --bind 127.0.0.1 --directory "$(pwd)" >/tmp/haoshijian-server.log 2>&1 &
echo "本地服务器已启动: http://127.0.0.1:8000"
echo ""
echo "下面会显示一个 https://xxxx.lhr.life 网址，"
echo "用手机浏览器打开它，即可把「好时间」装到主屏幕。"
echo "（保持本窗口开着；装好后即使关掉，App 也能离线使用）"
echo "--------------------------------------------------------"

# 启动 localhost.run HTTPS 隧道（无需安装、无需账号，仅用系统自带 ssh）
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run
