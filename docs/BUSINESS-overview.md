# Emotion Chatbot — Tài liệu Business Overview

> Dự án môn NLP501 (FSB, 2026). Tài liệu này trả lời: sản phẩm là gì, giải quyết bài toán gì, đã đạt gì, ranh giới của承诺 như thế nào. Số liệu: xem Evidence Appendix [B.x].

---

## 1. Sản phẩm là gì?

Một **chatbot cảm xúc bằng giọng nói tiếng Việt**: người dùng nói bất kỳ điều gì, hệ thống lắng nghe → nhận diện cảm xúc → phản hồi như một người bạn ấm áp, giúp người dùng vui lên / nhẹ nhõm.

- Người dùng dùng **giọng nói hoặc văn bản** — không cần chuẩn bị, không cần cú pháp lệnh.
- Phản hồi **ngắn, tự nhiên như nhắn tin**, phù hợp mục đích tâm sự.

## 2. Bài toán & giá trị

| Bài toán | Giải pháp của sản phẩm |
|---|---|
| Người cần người nghe, không phải người hướng dẫn | Chatbot phản hồi theo cảm xúc, không theo kịch bản |
| Cảm xúc không nói thẳng bằng từ | Nhận diện **cả nội dung lẫn tông giọng** (prosody: năng lượng, cao độ → "arousal") |
| An toàn tâm lý | Pipeline có tầng **safe-reply** — câu hỏi nhạy cảm được xử lý thất bại-thành-an-toàn (fail-safe), không rủi ro "sai lời nói ra ngoài" |

**Người dùng mục tiêu:** người trẻ cần kênh xả stress hàng ngày; bài toán dạy học của môn NLP501 (thực hành end-to-end ML: speech → emotion → LLM).

## 3. Cách nó hoạt động (góc nhìn người dùng)

1. Bạn nhấn **micro** và nói ("hôm nay mình thấy hơi buồn quá…")
2. Hệ thống ghi giọng → nhận diện từ → đo tông giọng
3. Phân loại cảm xúc (7 nhãn: Giận/Ai gét, Vui, Buồn, Sợ, Ngạc nhiên, Ghê tởm, Khác)
4. Sinh câu trả lời an ủi/động viên phù hợp cảm xúc vừa nhận diện
5. UI hiện lời phản hồi + biểu đồ cảm xúc (không phụ thuộc mô hình — có chế độ dự phòng khi mô hình off)

## 4. Chất lượng — kết quả đo được

| Chỉ số | Kết quả | Ý nghĩa business |
|---|---|---|
| Nhận diện cảm xúc — macro-F1 **0.6209** | đạt mục tiêu 0.627±0.007 (biên dưới) | Model chuyên biệt (CafeBERT) nhận diện tốt các nhãn cốt: Vui 0.766, Buồn 0.761 (2 kịch bản chính của sản phẩm) |
| LLM tổng quát zero-shot — macro-F1 **~0.45** | baseline so sánh | Chứng minh giá trị fine-tune cho domain tiếng Việt (+0.17) |
| E2E verified | `/health` 200 OK, ca "hôm nay mình thấy hơi buồn quá" → Sadness **96.2%**, trả lời an ủi tự nhiên | Sản phẩm chạy thật, không phải demo giả lập |

## 5. Đội ngũ & phân công

- **Quyên (ML):** 3 mô hình (emotion/speech/llm) + server Colab + thí nghiệm E3/E4 + báo cáo ML.
- **Hiển (FE/BE/infra):** React frontend, FastAPI backend, máy chủ deploy (`realestate-vm`, Docker + GitHub Actions), domain prod.

## 6. Ranh giới hiện tại (honest limits)

1. Model server Colab là **máy chủ tạm thời (ephemeral)** (~90 phút không hoạt động hoặc hết quota) — dùng demo/verify; backend có dự phòng tự động khi server biến mất.
2. Lớp thiểu số Anger F1 0.394 (40 mẫu) — nhãn hiếm chưa học tốt.
3. Zero-shot LLM chưa phải tối đa (n=150, khoảng ±0.05).

---

## Evidence Appendix — nguồn từng con số

| # | Claim | Nguồn |
|---|---|---|
| B1 | macro-F1 0.6209/acc 0.6681, F1 từng lớp | `colab/experiment_E3_E4_completed.ipynb` cell E3 (output đã lưu) |
| B2 | E4-v3 0.5133/0.4505, parse 150/150 | như trên, cell E4-v2 protocol v3 |
| B3 | Mục tiêu 0.627±0.007 | model card `BaoNhan/cafebert-UITVSMEC` (tham chiếu) |
| B4 | Sadness 96.2%, health 200 | curl test trực tiếp server (2026-11-11, session log) |
| B5 | CNN paper ~57.6%, ViSoBERT ~66% | paper PACLING-2019 / github dinhthienan33 (đã search verify) |
| B6 | Ephemeral Colab | giới hạn nền tảng Colab free; backend fallback đã cấu hình |

*Trạng thái verify prod end-to-end [CHƯA XÁC MINH] — đang chờ backend cắm bằng biến env handoff (docs/HANDOFF-model-server-Quyen.md) + test bằng chứng.*
