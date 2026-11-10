#!/usr/bin/env bash
# Chạy TRÊN SERVER, là forced command của deploy key GitHub Actions (xem deploy/README.md).
# Key đó chỉ gọi được script này, không mở shell, không forward cổng.
#
# Lệnh nhận qua SSH_ORIGINAL_COMMAND:
#   deploy <commit-sha-40-ký-tự>   kéo compose của đúng commit đó từ GitHub, pull image sha-<7 ký tự>, up --wait
#   status                         in trạng thái container và tag đang chạy
#
# Compose được lấy từ GitHub theo commit, không nhận từ phía gọi: lộ key cũng chỉ
# deploy được các commit đã có trong repo, không chạy được cấu hình tuỳ ý.
set -euo pipefail
umask 027

REPO="NguyenTatHien/emotion-chatbot"
DIR="/opt/emotion-chatbot"
COMPOSE="docker-compose.prod.yml"
IMAGE_RE='^ghcr\.io/nguyentathien/emotion-chatbot-(api|web):sha-[0-9a-f]{7}$'

cmd="${SSH_ORIGINAL_COMMAND:-$*}"
action="" sha="" extra=""
read -r action sha extra <<<"$cmd" || true

cd "$DIR"

case "$action" in
  status)
    echo "tag hiện tại: $(cat .tag 2>/dev/null || echo '(chưa có)')"
    if [[ -f "$COMPOSE" ]]; then
      docker compose -f "$COMPOSE" ps
    else
      echo "chưa deploy lần nào"
    fi
    exit 0
    ;;
  deploy) ;;
  *)
    echo "Lệnh không hợp lệ. Dùng: deploy <commit-sha> | status" >&2
    exit 2
    ;;
esac

if [[ -n "$extra" || ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SHA phải là commit đầy đủ 40 ký tự hex" >&2
  exit 2
fi

if [[ ! -f .env ]]; then
  echo "Thiếu $DIR/.env trên server" >&2
  exit 1
fi

tag="sha-${sha:0:7}"
prev="$(cat .tag 2>/dev/null || true)"
export TAG="$tag"

echo ">> Lấy $COMPOSE của commit ${sha:0:7}"
tmp="$(mktemp "$DIR/.compose.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
curl -fsSL --max-time 30 \
  "https://raw.githubusercontent.com/${REPO}/${sha}/deploy/${COMPOSE}" -o "$tmp"
docker compose -f "$tmp" config -q
chmod 640 "$tmp"
mv "$tmp" "$COMPOSE"
trap - EXIT

echo ">> Pull và khởi động TAG=$tag (trước đó: ${prev:-không có})"
docker compose -f "$COMPOSE" pull --quiet
docker compose -f "$COMPOSE" up -d --remove-orphans --wait --wait-timeout 180
docker compose -f "$COMPOSE" ps

if [[ -n "$prev" && "$prev" != "$tag" ]]; then
  echo "$prev" > .tag-truoc
fi
echo "$tag" > .tag

# Dọn image cũ của project, giữ tag hiện tại và tag trước đó để rollback nhanh.
docker images --format '{{.Repository}}:{{.Tag}}' \
  | grep -E "$IMAGE_RE" \
  | grep -v -e ":${tag}\$" ${prev:+-e ":${prev}\$"} \
  | xargs -r docker rmi >/dev/null 2>&1 || true

echo ">> Xong: $tag"
