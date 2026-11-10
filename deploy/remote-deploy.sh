#!/usr/bin/env bash
# Chạy TRÊN SERVER, là forced command của deploy key GitHub Actions (xem deploy/README.md).
# Key đó chỉ gọi được script này, không mở shell, không forward cổng.
#
# Lệnh nhận qua SSH_ORIGINAL_COMMAND:
#   deploy <commit-sha-40-ký-tự>   kéo compose của đúng commit đó từ GitHub, pull image sha-<7 ký tự>, up --wait
#   status                         in trạng thái container, tag đang chạy và cấu hình LLM
#
# Kèm `deploy`, stdin có thể chứa vài dòng KEY=VALUE (GitHub Secret/Variable) để ghi vào .env.
# Chỉ nhận các biến trong ENV_RULES, kiểm tra định dạng từng giá trị; log chỉ in tên biến,
# không in giá trị. Gửi qua stdin để bí mật không nằm trên dòng lệnh. Trước khi áp dụng,
# cấu hình mới được kiểm bằng chính image sắp chạy; sai thì khôi phục .env cũ và dừng.
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
  # Bí mật (GitHub Secret)
  [GEMINI_API_KEY]='^[A-Za-z0-9_-]{20,200}$'
  [MODEL_SERVER_TOKEN]='^[A-Za-z0-9._~+/=-]{16,200}$'
  # Cấu hình (GitHub Variable)
  [GEMINI_MODEL]='^[a-z0-9][a-z0-9.-]{1,63}$'
  [LLM_MODE]='^(mock|local|remote|gemini)$'
  [EMOTION_MODE]='^(mock|local|remote)$'
  [SPEECH_MODE]='^(mock|local|remote)$'
  [SAFETY_MODE]='^(mock|local)$'
  [MUSIC_MODE]='^(mock|local)$'
  [MODEL_SERVER_URL]='^https://[A-Za-z0-9.-]+(:[0-9]{2,5})?(/[A-Za-z0-9._~/-]*)?$'
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
      awk -v k="$key=" -v kv="$kv" 'index($0, k) == 1 { print kv; next } { print }' \
        "$tmpenv" >"$tmpenv.n"
      mv "$tmpenv.n" "$tmpenv"
    else
      printf '%s\n' "$kv" >>"$tmpenv"
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
    # Biến cấu hình in giá trị; bí mật chỉ in "đã đặt"/"trống".
    for name in "${!ENV_RULES[@]}"; do
      value="$(grep -m1 "^${name}=" .env | cut -d= -f2- || true)"
      case "$name" in
        GEMINI_API_KEY | MODEL_SERVER_TOKEN) value="$([[ -n "$value" ]] && echo 'đã đặt' || echo 'trống')" ;;
      esac
      echo "  $name=$value"
    done | sort
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
  # Kiểm cấu hình mới bằng chính image sắp chạy (mode hợp lệ, remote có URL, gemini có khoá...).
  # Sai thì khôi phục .env cũ để container đang chạy không bị thay bằng bản hỏng.
  if ! docker run --rm --env-file .env "ghcr.io/nguyentathien/emotion-chatbot-api:${tag}" \
    python -c "from app.config import get_settings; get_settings().validate_remote()" \
    >/dev/null 2>"$DIR/.env-check.log"; then
    echo "Cấu hình mới không hợp lệ, giữ nguyên .env cũ. Lỗi:" >&2
    grep -E "Error|không hợp lệ|trống|không được hỗ trợ" "$DIR/.env-check.log" | tail -3 >&2 || true
    mv .env.truoc .env
    rm -f "$DIR/.env-check.log"
    exit 1
  fi
  rm -f "$DIR/.env-check.log"
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
