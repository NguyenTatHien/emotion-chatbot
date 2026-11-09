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
3. **File `.env` trên server**, tạo tay một lần (không bao giờ copy từ máy dev):
   ```bash
   ssh realestate-vm
   sudo mkdir -p /opt/emotion-chatbot && sudo chown "$USER" /opt/emotion-chatbot
   cd /opt/emotion-chatbot
   nano .env          # dựa theo deploy/.env.server.example
   chmod 600 .env
   ```
4. **SSH**: máy bạn có host `realestate-vm` trong `~/.ssh/config`, và tài khoản trên server dùng được `docker`.
5. Mạng `javis-web` đã tồn tại trên server (`docker network ls | grep javis-web`).

## Thử trước bằng subdomain test

Nhãn caddy sai có thể làm `javis-proxy` từ chối cấu hình dùng chung và ảnh hưởng ứng dụng khác, nên **thử trước bằng một subdomain tạm**:

1. Thêm DNS `emotion-test.hiennguyen.io.vn` về cùng IP.
2. Trên server, sao chép `docker-compose.prod.yml` sang thư mục tạm, đổi nhãn `caddy: emotion-test.hiennguyen.io.vn` rồi `up -d`.
3. Xem log proxy ngay sau đó:
   ```bash
   docker logs --tail 50 -f javis-proxy
   ```
   Không được có dòng lỗi về cấu hình; chứng chỉ được cấp cho subdomain test.
4. Mở `https://emotion-test.hiennguyen.io.vn`, thử chat; xong thì `docker compose down` và xóa DNS test.

## Triển khai

Từ thư mục gốc repo, trên máy bạn:

```bash
deploy/deploy.sh              # dùng tag latest
deploy/deploy.sh sha-1a2b3c4  # hoặc một commit cụ thể (khuyến nghị)
```

Script sẽ: `scp` file compose lên `/opt/emotion-chatbot/` → `docker compose pull` → `up -d` → gọi `https://emotion.hiennguyen.io.vn/api/health` (thử lại tối đa 10 lần). Có thể đổi host/thư mục/domain bằng biến `DEPLOY_HOST`, `DEPLOY_DIR`, `DEPLOY_DOMAIN`.

Sau khi chạy, xem log proxy một lần nữa: `ssh realestate-vm 'docker logs --tail 50 javis-proxy'`.

## Rollback

Chạy lại script với tag của phiên bản trước đó:

```bash
deploy/deploy.sh sha-<commit cũ>
```

Danh sách tag có ở GitHub → Packages. Dữ liệu đánh giá nằm trong volume `emotion-data` nên không mất khi đổi image.

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
