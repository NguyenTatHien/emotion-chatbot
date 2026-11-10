# Triển khai lên realestate-vm

Hướng dẫn đưa Emotion Chatbot lên máy chủ `realestate-vm` (Ubuntu 24.04, 2 vCPU, 7,8 GB RAM, không GPU). Máy này đang chạy nhiều ứng dụng khác sau reverse proxy dùng chung `javis-proxy` (caddy-docker-proxy, mạng Docker `javis-web`), vì vậy **chỉ làm đúng các bước dưới đây và không đụng vào container khác**.

## Kiến trúc

```
Internet ──443──▶ javis-proxy (HTTPS tự động)
                      │  mạng javis-web, label caddy=emotion.hiennguyen.io.vn
                      ▼
                 web (Caddy: file tĩnh + proxy /api/*)      ─┐ mạng nội bộ
                      │                                       │ của project
                      ▼                                       │ emotion-chatbot
                 backend (FastAPI, :8000, không publish cổng) ─┘
                      └─ volume emotion-data → /app/data/runtime (feedback.jsonl)
```

- Chỉ container `web` tham gia mạng `javis-web`; `backend` chỉ ở mạng nội bộ.
- Image build sẵn ở GitHub Actions (`images.yml`), server chỉ `pull`:
  - `ghcr.io/nguyentathien/emotion-chatbot-api`
  - `ghcr.io/nguyentathien/emotion-chatbot-web`
  - Tag: `sha-<7 ký tự đầu của commit>` và `latest`.
- Giới hạn bộ nhớ: backend 512 MB, web 128 MB; `restart: unless-stopped`.
- Server không có GPU nên backend chạy mock hoặc `remote` (model server trên Colab), không chạy mô hình cục bộ.

## Điều kiện trước khi triển khai

1. **DNS**: thêm bản ghi `emotion.hiennguyen.io.vn` trỏ về IP của `realestate-vm` (bạn tự thêm ở nhà cung cấp DNS). `javis-proxy` cần DNS đúng để cấp HTTPS.
2. **Image đã có trên GHCR**: push lên `main` để `images.yml` chạy xong. GHCR package mới tạo mặc định là *private*. Chọn một trong hai:
   - Đặt hai package thành *public* (GitHub → Packages → từng package → Package settings → Change visibility). Image không chứa bí mật nên an toàn để public; hoặc
   - Trên server chạy `docker login ghcr.io` với Personal Access Token có quyền `read:packages`.
3. **Thư mục và `.env` trên server** (đã làm ngày 2026-11-10; `.env` đang ở chế độ mock): thư mục `/opt/emotion-chatbot` thuộc user `deploy` (nhóm docker), `.env` chế độ 600, tạo tay một lần theo `deploy/.env.server.example`, không bao giờ copy từ máy dev. Sửa `.env`:
   ```bash
   ssh realestate-vm
   sudo -u deploy nano /opt/emotion-chatbot/.env
   ```
   Sau khi sửa, chạy lại workflow Deploy (hoặc `deploy/deploy.sh`) để container đọc giá trị mới.
4. **SSH**: máy bạn có host `realestate-vm` trong `~/.ssh/config` (chỉ cần cho deploy tay).
5. Mạng `javis-web` đã tồn tại trên server (`docker network ls | grep javis-web`).

## Tự động triển khai (GitHub Actions)

Push lên `main` → workflow **Images** build và đẩy image `sha-<7 ký tự>` → workflow **Deploy** SSH vào server và chạy `remote-deploy.sh` → kiểm tra `https://emotion.hiennguyen.io.vn/api/health`.

Thiết lập (đã làm):

- Environment `production` trên GitHub, chỉ nhánh `main` được dùng, chứa secrets `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`, `DEPLOY_HOST`, `DEPLOY_PORT`, `DEPLOY_USER`.
- Key `github-actions-emotion-chatbot` trong `/home/deploy/.ssh/authorized_keys` có dạng `restrict,command="/opt/emotion-chatbot/remote-deploy.sh" ssh-ed25519 ...`: key này **chỉ** chạy được script deploy, không mở shell, không forward cổng.
- `remote-deploy.sh` (thuộc root, user `deploy` không sửa được) chỉ nhận `deploy <commit-sha-40-ký-tự>` hoặc `status`. File compose được tải từ GitHub đúng commit đó, nên dù lộ key cũng chỉ deploy lại được các commit đã có trong repo.
- Script lưu tag hiện tại vào `.tag`, tag trước vào `.tag-truoc`, và xoá image cũ của project (giữ 2 bản gần nhất).

### Cấu hình LLM từ GitHub (khoá Gemini)

Không cần SSH để đổi khoá: đặt ở GitHub → Settings → Environments → **production**:

| Loại | Tên | Ví dụ |
|---|---|---|
| Secret | `GEMINI_API_KEY` | khoá lấy ở <https://aistudio.google.com/apikey> |
| Variable | `LLM_MODE` | `gemini` (chỉ Gemini) hoặc `remote` (Colab, Gemini làm dự phòng) |
| Variable | `GEMINI_MODEL` | `gemini-3.5-flash-lite` |

Mỗi lần Deploy, workflow gửi các giá trị này qua **stdin của SSH** (không đặt trên dòng lệnh); `remote-deploy.sh` chỉ nhận đúng 3 tên trên, kiểm tra định dạng, ghi vào `.env` (bản cũ ở `.env.truoc`) và tạo lại container nếu `.env` đổi. Log chỉ in tên biến. Để trống một mục thì giá trị trên server được giữ nguyên. Sau khi sửa secret/variable, chạy lại **Actions → Deploy → Run workflow** để áp dụng.

**Không bao giờ** ghi khoá vào file trong repo: repo public, khoá sẽ bị quét và thu hồi ngay. Xem cấu hình đang chạy (không lộ khoá): `ssh realestate-vm 'runuser -u deploy -- env SSH_ORIGINAL_COMMAND=status /opt/emotion-chatbot/remote-deploy.sh'`.

Khi sửa `deploy/remote-deploy.sh` trong repo, cần cài lại bản trên server (server không tự cập nhật script này):

```bash
scp deploy/remote-deploy.sh realestate-vm:/tmp/emotion-remote-deploy.sh
ssh realestate-vm 'install -o root -g root -m 755 /tmp/emotion-remote-deploy.sh /opt/emotion-chatbot/remote-deploy.sh && rm /tmp/emotion-remote-deploy.sh'
```

Thu hồi quyền deploy của GitHub: xoá dòng có `github-actions-emotion-chatbot` trong `/home/deploy/.ssh/authorized_keys`.

## Triển khai tay

Bình thường không cần: push lên `main` là tự deploy. Khi cần deploy tay từ máy bạn (ví dụ GitHub Actions đang lỗi):

```bash
deploy/deploy.sh            # commit mới nhất của origin/main
deploy/deploy.sh 1a2b3c4    # hoặc một commit cụ thể
```

Script SSH bằng `realestate-vm` rồi chạy đúng `remote-deploy.sh` dưới user `deploy`, sau đó kiểm tra `/api/health` (thử lại tối đa 12 lần). Image của commit đó phải đã có trên GHCR.

## Rollback

- Trên GitHub: Actions → **Deploy** → Run workflow → nhập SHA đầy đủ (40 ký tự) của commit cũ.
- Hoặc từ máy bạn: `deploy/deploy.sh <commit cũ>`.

Tag đang chạy nằm ở `/opt/emotion-chatbot/.tag`, tag trước đó ở `.tag-truoc`. Dữ liệu đánh giá nằm trong volume `emotion-data` nên không mất khi đổi image.

## Vận hành

```bash
ssh realestate-vm
cd /opt/emotion-chatbot
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
docker stats --no-stream emotion-chatbot-backend-1 emotion-chatbot-web-1
```

Lấy file đánh giá (cần `ADMIN_TOKEN` trong `.env`):

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://emotion.hiennguyen.io.vn/api/feedback/export -o feedback.csv
```

## Gỡ bỏ

Chỉ gỡ project này (tên project `emotion-chatbot`), không đụng container khác:

```bash
cd /opt/emotion-chatbot
docker compose -f docker-compose.prod.yml down            # giữ lại dữ liệu
docker compose -f docker-compose.prod.yml down -v         # xóa cả volume emotion-data (mất đánh giá)
```

Sau đó xóa bản ghi DNS và thư mục `/opt/emotion-chatbot` nếu không dùng nữa.
