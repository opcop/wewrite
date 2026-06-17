#!/usr/bin/env bash
# 给任务容器网络做出站硬化：放行公网，DROP 到内网私有段 + 云元数据。
# 在宿主以 root 跑一次（开机自启建议写进 systemd / rc.local）。
# 需先： docker network create wewrite-jobs
set -euo pipefail

NET="${1:-wewrite-jobs}"
BRIDGE_ID="$(docker network inspect "$NET" -f '{{.Id}}' | cut -c1-12)"
IFACE="br-${BRIDGE_ID}"

echo "锁定网络 $NET（接口 $IFACE）的出站：堵内网 + 元数据"
iptables -I DOCKER-USER -i "$IFACE" -d 169.254.169.254/32 -j DROP
for cidr in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
  iptables -I DOCKER-USER -i "$IFACE" -d "$cidr" -j DROP
done
echo "完成。验证：docker run --rm --network $NET curlimages/curl -m 5 http://169.254.169.254 应超时/被拒"
