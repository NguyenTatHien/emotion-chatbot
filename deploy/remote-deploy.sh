#!/usr/bin/env bash
# Chạy TRÊN SERVER, là forced command của deploy key GitHub Actions (xem deploy/README.md).
# Key đó chỉ gọi được script này, không mở shell, không forward cổng.
#
# Lệnh nhận qua SSH_ORIGINAL_COMMAND:
#   deploy <commit-sha-40-ký-tự>   kéo compose của đúng commit đó từ GitHub, pull image sha-<7 ký tự>, up --wait
#   status                         in trạng thái container, tag đang chạy và cấu hình LLM
#
# Kèm `deploy`, stdin có thể chứa vài dòng KEY=VALUE (GitHub Secret/Variable) để ghi vào .env.
# Chỉ nhận GEMINI_API_KEY, GEMINI_MODEL, LLM_MODE, kiểm tra định dạng từng giá trị; log chỉ in
# tên biến, không in giá trị. Gửi qua stdin để bí mật không nằm trên dòng lệnh.
#
# Compose được lấy từ GitHub theo commit, không nhận từ phía gọi: lộ key cũng chỉ
# deploy được các commit đã có trong repo, không chạy được cấu hình tuỳ ý.
set -euo pipefail
umask 027

REPO="NguyenTatHien/emotion-chatbot"
DIR="/opt/emotion-chatbot"
COMPOSE="docker-compose.prod.yml"
IMAGE_RE='^ghcr\.io/nguyentathien/emotion-chatbot-(api|web):sha-[0-9a-f]{7}$'

declare -A ENV_RULES=(
  [GEMINI_API_KEY]='^[A-Za-z0-9_-]{20,200}$'
  [GEMINI_MODEL]='^[a-z0-9][a-z0-9.-]{1,63}$'
  [LLM_MODE]='^(mock|local|remote|gemini)$'
)
updates=()

# Đọc KEY=VALUE từ stdin (bỏ qua khi stdin là terminal); sai một dòng là dừng, không ghi gì.
read_env_updates() {
  [[ -t 0 ]] && return 0
  local line key value n=0
  while IFS= read -r -t 10 line || [[ -n "${line:-}" ]]; do
    n=$((n + 1))
    if ((n > 20)); then
      echo "stdin quá nhiều dòng" >&2
      exit 2
    fi
    [[ -z "$line" ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    if [[ "$line" != *=* || ! "$key" =~ ^[A-Z_]{1,40}$ || -z "${ENV_RULES[$key]+x}" ]]; then
      echo "Biến không được phép: ${key:0:40}" >&2
      exit 2
    fi
    if [[ ! "$value" =~ ${ENV_RULES[$key]} ]]; then
      echo "Giá trị của $key sai định dạng" >&2
      exit 2
    fi
    updates+=("$key=$value")
    line=""
  done
}

# Ghi các biến vào .env (giữ bản cũ ở .env.truoc). Trả 0 nếu .env thực sự đổi.
apply_env_updates() {
  ((${#updates[@]} == 0)) && return 1
  local tmpenv kv key names=()
  tmpenv="$(mktemp "$DIR/.env.XXXXXX")"
  cat .env >"$tmpenv"
  for kv in "${updates[@]}"; do
    key="${kv%%=*}"
    if grep -q "^${key}=" "$tmpenv"; then
      awk -v k="$key=" -v kv="$kv" 'index($0, k) == 1 { print kv; next } { print }'         "$tmpenv" >"$tmpenv.n"
      mv "$tmpenv.n" "$tmpenv"
    else
      printf '%s
' "$kv" >>"$tmpenv"
    fi
    names+=("$key")
  done
  if cmp -s .env "$tmpenv"; then
    rm -f "$tmpenv"
    echo ">> .env không đổi (${names[*]})"
    return 1
  fi
  cp -p .env .env.truoc
  chmod 600 "$tmpenv"
  mv "$tmpenv" .env
  echo ">> Cập nhật .env: ${names[*]}"
  return 0
}

cmd="${SSH_ORIGINAL_COMMAND:-$*}"
action="" sha="" extra=""
read -r action sha extra <<<"$cmd" || true

cd "$DIR"

case "$action" in
  status)
    echo "tag hiện tại: $(cat .tag 2>/dev/null || echo '(chưa có)')"
    echo "LLM_MODE=$(grep -m1 '^LLM_MODE=' .env | cut -d= -f2-)"       "GEMINI_MODEL=$(grep -m1 '^GEMINI_MODEL=' .env | cut -d= -f2-)"       "GEMINI_API_KEY=$(grep -qE '^GEMINI_API_KEY=.+' .env && echo 'đã đặt' || echo 'trống')"
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

read_env_updates

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
up_flags=(-d --remove-orphans --wait --wait-timeout 180)
if apply_env_updates; then
  up_flags+=(--force-recreate) # đảm bảo container đọc lại .env mới
fi
docker compose -f "$COMPOSE" up "${up_flags[@]}"
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
