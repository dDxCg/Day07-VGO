# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Đỗ Đức Cường
**Nhóm:** VGO
**Ngày:** 3/8/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai đoạn văn bản có vector embedding trỏ gần cùng một hướng trong không gian nhiều chiều, tức là chúng mang ý nghĩa/ngữ nghĩa gần giống nhau, dù độ dài câu chữ có thể khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Sinh viên có thể vay vốn để đóng học phí."
- Câu B: "Học phí có thể được chi trả bằng khoản vay dành cho sinh viên."
- Tại sao tương đồng: cùng nói về vay vốn để đóng học phí, chỉ khác cách diễn đạt

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Sinh viên có thể vay vốn để đóng học phí."
- Câu B: "Thư viện mở cửa từ 7 giờ sáng đến 9 giờ tối."
- Tại sao khác: hai chủ đề hoàn toàn không liên quan (học bổng/vay vốn va giờ mở cửa thư viện).

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ quan tâm đến hướng của vector, không quan tâm độ lớn, nên không bị ảnh hưởng bởi độ dài văn bản hay độ "mạnh" của embedding; Euclidean lại nhạy với độ lớn vector, dễ đánh giá sai hai câu cùng ý nghĩa nhưng có độ dài/chuẩn hóa khác nhau là "khác xa nhau".

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* chunk_num = floor((10000 − 50) / (500 − 50)) = floor(9950 / 450) = floor(22.11) = 23
> *Đáp án:* 23 chunks

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> floor((10000 − 100) / (500 − 100)) = floor(9900 / 400) = floor(24.75) = 25 chunks — tăng từ 23 lên 25. Tăng overlap giúp giữ ngữ cảnh liên tục qua ranh giới chunk, giảm nguy cơ một câu/ý quan trọng bị cắt đứt giữa hai chunk, đánh đổi bằng việc lưu trữ nhiều dữ liệu trùng lặp hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"(?:[.!?] |\.\n)", text)` để tách câu tại dấu `.`/`!`/`?` theo sau bởi khoảng trắng hoặc xuống dòng, sau đó `strip()` từng câu và loại câu rỗng. Nhóm các câu liên tiếp thành cụm theo `max_sentences_per_chunk` bằng cách duyệt theo bước nhảy cố định. Edge case: văn bản rỗng trả về `[]`; văn bản không có dấu câu vẫn trả về nguyên văn như 1 "câu".

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Đệ quy thử tách theo từng separator trong danh sách ưu tiên (`\n\n`, `\n`, `. `, ` `, `""`); với mỗi phần tách ra, gộp dần vào chunk hiện tại miễn còn ≤ `chunk_size`, nếu vượt thì chốt chunk cũ và mở chunk mới. Nếu một phần vẫn quá dài sau khi tách bằng separator hiện tại, gọi đệ quy `_split` với separator tiếp theo trong danh sách. Base case: `len(current_text) <= chunk_size` (trả nguyên văn bản) hoặc hết separator (cắt cứng theo `chunk_size`).

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` gọi `embedding_fn` cho từng `doc.content` rồi lưu record `{id, content, metadata, embedding}` vào list `self._store` (in-memory) hoặc `collection.add(...)` (ChromaDB nếu import được). `search` nhúng câu truy vấn, tính dot product giữa vector truy vấn và từng embedding đã lưu (`_dot`), sắp xếp giảm dần theo score và trả về top_k.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc theo metadata **trước** (so khớp từng cặp key-value trong `metadata_filter` với `record["metadata"]`), sau đó mới chạy `_search_records` (dot product) trên tập đã lọc để không lãng phí tính điểm những chunk không thuộc phạm vi cần tìm. `delete_document` xóa mọi record có `record["id"] == doc_id` hoặc `metadata["doc_id"] == doc_id`, trả `True` nếu độ dài store thay đổi.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Gọi `store.search(question, top_k)` lấy các chunk liên quan, nối nội dung (`content`) của chúng lại bằng `\n\n` làm phần "Context", rồi ghép với câu hỏi vào một prompt có cấu trúc rõ ràng ("Context: ... Question: ... Answer using only the context above."), cuối cùng gọi `llm_fn(prompt)` và trả về kết quả.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
# Dán kết quả (output) của: pytest tests/ -v
```

**Số lượng bài test vượt qua (pass):** __ / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Sinh viên có thể vay vốn để đóng học phí." | "Học phí có thể được chi trả bằng khoản vay dành cho sinh viên." | cao | 0.9160 | Đúng |
| 2 | "Thư viện mở cửa từ 7 giờ sáng đến 9 giờ tối." | "Sinh viên có thể vay vốn để đóng học phí." | thấp | 0.1673 | Đúng |
| 3 | "Đại học Quốc gia Hà Nội thành lập lớp chuyên Toán từ năm 1965." | "Lớp chuyên Toán của ĐHQGHN ra đời năm 1965." | cao | 0.7418 | Đúng |
| 4 | "Chương trình đào tạo hệ THCS và THPT dành cho học sinh năng khiếu." | "Trung tâm tư vấn hỗ trợ việc làm giúp sinh viên tìm việc sau tốt nghiệp." | thấp | 0.5141 | Sai (cao hơn dự đoán) |
| 5 | "Hồ sơ đăng ký vay vốn sinh viên cần giấy xác nhận hộ nghèo." | "Thủ tục vay vốn cho sinh viên cần các giấy tờ chứng minh hoàn cảnh khó khăn." | cao | 0.7561 | Đúng |

> *Chạy bằng embedder thật:* `EMBEDDING_PROVIDER=local` (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`), độ tương tự tính bằng `compute_similarity()` trong `src/chunking.py`.

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 4 gây bất ngờ nhất: hai câu tưởng chừng khác chủ đề (đào tạo THCS/THPT vs. tư vấn việc làm) vẫn đạt 0.51 — cao hơn dự đoán "thấp". Cả hai đều nằm trong miền ngữ nghĩa chung "hoạt động hỗ trợ sinh viên/học sinh của trường đại học", nên embedding bắt được sự tương đồng về ngữ cảnh/domain dù nội dung cụ thể khác nhau, chứ không chỉ so khớp từ vựng trùng lặp.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | ĐHQGHN đang triển khai bao nhiêu chương trình đại học, thạc sĩ và tiến sĩ? | `gioi-thieu-chung.md` — nói về "2.400 thạc sỹ và 200 tiến sỹ" tốt nghiệp hàng năm, KHÔNG chứa câu "190/198/118 chương trình" (câu đó nằm ở chunk liền trước, không lọt top-3) | 0.8094 | **Không** — câu chứa số liệu đúng bị cắt sang chunk khác, không xuất hiện trong top-3 | Agent trả lời sai/thiếu vì context không có số liệu 190/198/118 |
| 2 | Theo tài liệu được đánh dấu hết hiệu lực, quỹ học bổng tối thiểu bằng bao nhiêu phần trăm tổng thu học phí? | `quy-dinh-ve-quan-ly-va-su-dung-hoc-bong...md` — "...tối thiểu bằng 15% tổng thu học phí từ sinh viên đại học hệ chính quy..." | 0.9356 | Có, rank 1 | 15% tổng thu học phí (ngành sư phạm cũng 15% từ nguồn cấp bù) |
| 3 | ĐHQGHN có 01 trường THCS và 04 trường THPT nào? | `dao-tao-he-thcs-va-thpt.md` — "Đại học Quốc gia Hà Nội có 01 trường Trung học..." kèm liệt kê Trường THCS Ngoại ngữ | 0.9119 | Có, rank 1 (danh sách đủ 5 trường nằm rải rác rank 1-2) | Liệt kê THCS Ngoại ngữ + các trường THPT chuyên trực thuộc ĐHQGHN |
| 4 | Quỹ UOB cho vay tối đa bao nhiêu, lãi suất và lịch trả nợ thế nào? | `vay-von.md` — "Mức cho vay tối đa: 10.000.000 đồng/SV...Lãi suất: 0%..." | 0.8231 | Có, rank 1 | Tối đa 10.000.000 đồng/SV, lãi suất 0%, thanh toán bằng đúng số học phí phải nộp |
| 5 | Sinh viên nào được tham dự Ngày hội việc làm Samsung? | `tu-van-ho-tro-viec-lam.md` — "'Ngày hội việc làm Samsung' hàng năm sẽ cung cấp cho các ứng viên..." | 0.8893 | Có, rank 1 | Sinh viên quan tâm tìm việc tại Samsung, tham khảo thông tin trên website Samsung |

*(Score = cosine similarity rescale [0,1] từ `EmbeddingStore.search` — 1.0 = liên quan cao nhất, 0.5 = trực giao/không liên quan; embedder thật `EMBEDDING_PROVIDER=local`, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, chạy trên `src/` cá nhân.)*

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 4 / 5 — câu 1 thất bại vì `FixedSizeChunker` cắt cứng theo ký tự, tách rời câu chứa số liệu (190/198/118) khỏi phần văn bản có ngữ nghĩa gần câu hỏi nhất, khiến chunk đúng không lọt top-3.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
