#!/usr/bin/env bash
# Triển khai tay emotion-chatbot lên realestate-vm (bình thường GitHub Actions tự làm, xem deploy.yml).
# Dùng:  deploy/deploy.sh [COMMIT]   (mặc định: origin/main; rollback = truyền commit cũ)
# Chạy cùng script phía server với GitHub Actions: /opt/emotion-chatbot/remote-deploy.sh,
# dưới user deploy. Image của commit phải đã có trên GHCR (workflow Images chạy xong).
set -euo pipefail

HOST="${DEPLOY_HOST:-realestate-vm}"
DOMAIN="${DEPLOY_DOMAIN:-emotion.hiennguyen.io.vn}"

git fetch --quiet origin main
SHA="$(git rev-parse --verify "${1:-origin/main}^{commit}")"

echo ">> Deploy commit ${SHA:0:7} lên ${HOST}"
ssh "$HOST" "runuser -u deploy -- env SSH_ORIGINAL_COMMAND='deploy ${SHA}' /opt/emotion-chatbot/remote-deploy.sh"

echo ">> Kiểm tra sức khỏe https://${DOMAIN}/api/health"
for i in $(seq 1 12); do
  if curl -fsS --max-time 10 "https://${DOMAIN}/api/health"; then
    echo
    echo ">> Xong: sha-${SHA:0:7}"
    exit 0
  fi
  echo "   chưa sẵn sàng (lần ${i}/12), thử lại sau 5 giây..." >&2
  sleep 5
done

echo "Health check thất bại. Xem log: ssh ${HOST} 'docker logs --tail 50 javis-proxy'" >&2
exit 1
