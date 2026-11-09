#!/usr/bin/env bash
# Triển khai emotion-chatbot lên realestate-vm.
# Dùng:  deploy/deploy.sh [TAG]      (TAG mặc định: latest; rollback = chạy lại với sha cũ, ví dụ sha-1a2b3c4)
# Yêu cầu: đã có DNS, /opt/emotion-chatbot/.env trên server và image đã lên GHCR (xem deploy/README.md).
set -euo pipefail

TAG="${1:-latest}"
HOST="${DEPLOY_HOST:-realestate-vm}"
REMOTE_DIR="${DEPLOY_DIR:-/opt/emotion-chatbot}"
DOMAIN="${DEPLOY_DOMAIN:-emotion.hiennguyen.io.vn}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! "$TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]; then
  echo "TAG không hợp lệ: $TAG" >&2
  exit 1
fi

echo ">> Đồng bộ docker-compose.prod.yml lên ${HOST}:${REMOTE_DIR}"
ssh "$HOST" "mkdir -p '${REMOTE_DIR}'"
scp "${SCRIPT_DIR}/docker-compose.prod.yml" "${HOST}:${REMOTE_DIR}/docker-compose.prod.yml"

echo ">> Kéo image và khởi động (TAG=${TAG})"
ssh "$HOST" "cd '${REMOTE_DIR}' && test -f .env || { echo 'Thiếu ${REMOTE_DIR}/.env trên server' >&2; exit 1; }; \
  TAG='${TAG}' docker compose -f docker-compose.prod.yml pull && \
  TAG='${TAG}' docker compose -f docker-compose.prod.yml up -d --remove-orphans && \
  TAG='${TAG}' docker compose -f docker-compose.prod.yml ps"

echo ">> Kiểm tra sức khỏe https://${DOMAIN}/api/health"
ok=0
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "https://${DOMAIN}/api/health"; then
    ok=1
    echo
    break
  fi
  echo "   chưa sẵn sàng (lần ${i}/10), thử lại sau 5 giây..." >&2
  sleep 5
done

if [[ "$ok" -ne 1 ]]; then
  echo "Health check thất bại. Xem log: ssh ${HOST} 'docker logs --tail 50 javis-proxy'" >&2
  exit 1
fi
echo ">> Xong: TAG=${TAG}"
