# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Lương Thanh Trang

**Nhóm:** vgo

**Ngày thực hiện:** 2026-08-03

---

## 1. Khởi động (Warm-up) — Cá nhân

### Độ tương tự Cosine

Độ tương tự cosine cao nghĩa là hai vector văn bản có hướng gần nhau, thường cho thấy hai đoạn biểu diễn nội dung hoặc ý nghĩa gần nhau. Giá trị gần 1 là rất giống; gần 0 là ít liên quan; giá trị âm thể hiện hướng đối lập trong không gian vector.

**Ví dụ có độ tương tự cao**

- Câu A: “Sinh viên đăng ký học phần trước mỗi học kỳ.”
- Câu B: “Người học cần hoàn tất đăng ký môn trước khi học kỳ bắt đầu.”
- Hai câu cùng nói về thủ tục đăng ký học phần và thời điểm thực hiện.

**Ví dụ có độ tương tự thấp**

- Câu A: “Sinh viên được rút học phần trong hai tuần đầu học kỳ chính.”
- Câu B: “Dự báo thời tiết hôm nay có mưa lớn.”
- Hai câu thuộc hai chủ đề không liên quan.

Cosine similarity thường phù hợp với text embeddings hơn khoảng cách Euclid vì nó so sánh hướng của vector và ít bị chi phối bởi độ lớn. Nhờ đó hai văn bản khác độ dài nhưng cùng ý vẫn có thể được đánh giá gần nhau.

### Bài toán tính toán Chunking

Với `document_length=10,000`, `chunk_size=500`, `overlap=50`:

```text
ceil((10,000 - 50) / (500 - 50))
= ceil(9,950 / 450)
= 23 chunks
```

Khi tăng overlap lên 100:

```text
ceil((10,000 - 100) / (500 - 100))
= ceil(9,900 / 400)
= 25 chunks
```

Số chunk tăng từ 23 lên 25 vì bước trượt giảm. Overlap lớn hơn giúp giữ ngữ cảnh ở ranh giới chunk, nhưng tăng số vector, thời gian nhúng và dung lượng lưu trữ.

---

## 2. Hướng tiếp cận của tôi

### `SentenceChunker.chunk`

Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\r?\n+)` để tách sau dấu kết câu khi tiếp theo là khoảng trắng hoặc xuống dòng. Các đoạn rỗng được loại bỏ, sau đó câu được nhóm theo `max_sentences_per_chunk`; văn bản rỗng trả về danh sách rỗng.

### `RecursiveChunker.chunk` / `_split`

Thuật toán ưu tiên các ranh giới lớn theo thứ tự đoạn văn, dòng, câu, từ rồi mới cắt cứng. Nếu đoạn vẫn dài hơn `chunk_size`, hàm đệ quy dùng separator tiếp theo; base case là đoạn đã đủ ngắn hoặc đã hết separator. Các phần nhỏ được ghép lại đến sát giới hạn để giảm số chunk nhưng vẫn giữ cấu trúc.

### `EmbeddingStore.add_documents` + `search`

Mỗi chunk được lưu với ID duy nhất, nội dung, bản sao metadata và embedding. Khi tìm kiếm, query chỉ được embed một lần; store tính dot product với các vector đã chuẩn hóa, sắp xếp giảm dần và trả tối đa `top_k` kết quả.

### `search_with_filter` + `delete_document`

Metadata được lọc trước bằng phép khớp chính xác tất cả cặp khóa–giá trị, sau đó mới xếp hạng similarity. `delete_document` tìm mọi chunk có cùng `metadata.doc_id`, xóa toàn bộ chúng và trả `True` nếu thực sự có dữ liệu bị xóa.

### `KnowledgeBaseAgent.answer`

Agent lấy top-k chunk, ghi rõ nguồn và `doc_id`, rồi đưa chúng vào phần `NGỮ CẢNH` của prompt. Prompt yêu cầu chỉ trả lời từ ngữ cảnh và thừa nhận khi thiếu thông tin; sau đó gọi `llm_fn` đúng một lần.

### Chiến lược cá nhân đã sử dụng

Tôi dùng `RecursiveChunker(chunk_size=700)` cho corpus quy định đại học. Quy chế 3626 có cấu trúc chương–điều–khoản và nhiều đoạn dài; recursive chunking ưu tiên ranh giới đoạn/dòng trước khi cắt nhỏ nên phù hợp hơn cắt cứng. Cấu hình tạo 210 chunks từ 5 tài liệu; không chunk nào vượt 700 ký tự. Tài liệu Quy chế 3626 tạo 144 chunks với độ dài trung bình 656,7 ký tự.

---

## 3. Hoàn thiện code

### Kết quả kiểm thử

```text
..........................................                               [100%]
42 passed, 1 warning in 0.04s
```

Warning chỉ liên quan việc pytest không tạo được `.pytest_cache` do quyền thư mục trên Windows; không có test thất bại.

**Số lượng test vượt qua:** **42 / 42**

Các trường hợp biên đã kiểm tra gồm văn bản rỗng, vector zero, vector khác số chiều, `top_k <= 0`, metadata filter không khớp và xóa `doc_id` không tồn tại.

---

## 4. Dự đoán độ tương tự

Các dự đoán được ghi trước khi chạy. Điểm thực tế dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; quy ước kiểm tra trong thí nghiệm này là điểm trên 0,5 thuộc nhóm tương đồng cao và dưới 0,3 thuộc nhóm thấp.

| Cặp | Câu A                                                                     | Câu B                                                                        | Dự đoán | Điểm thực tế | Đúng? |
| ---- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------- | ---------------: | ------- |
| 1    | Sinh viên đăng ký học phần trước mỗi học kỳ.                    | Người học cần hoàn tất đăng ký môn trước khi học kỳ bắt đầu. | Cao        |         0.817287 | Có     |
| 2    | Điều kiện để sinh viên được xét tốt nghiệp là gì?            | Sinh viên cần tích lũy đủ tín chỉ và đạt chuẩn đầu ra.          | Cao        |         0.601920 | Có     |
| 3    | Sinh viên có thể rút học phần trong hai tuần đầu học kỳ chính. | Thư viện mở cửa từ thứ Hai đến thứ Sáu.                             | Thấp      |         0.188787 | Có     |
| 4    | Học bổng hỗ trợ sinh viên có thành tích học tập tốt.            | Chính sách học bổng dành cho người học xuất sắc.                    | Cao        |         0.873195 | Có     |
| 5    | Quy định cảnh báo học vụ dựa trên điểm tích lũy.               | Dự báo thời tiết hôm nay có mưa lớn.                                  | Thấp      |         0.068480 | Có     |

Cặp 2 thấp hơn các cặp gần nghĩa còn lại dù hai câu cùng nói về điều kiện tốt nghiệp. Nguyên nhân hợp lý là câu hỏi dùng khái niệm chung, còn câu trả lời nêu các điều kiện cụ thể như tín chỉ và chuẩn đầu ra. Kết quả cũng cho thấy mô hình phân biệt tốt hai cặp khác chủ đề, đặc biệt cặp 5 chỉ đạt 0,068480.

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

Kết quả bất ngờ nhất là truy vấn Q4 về điểm tích lũy tối thiểu để tốt nghiệp lại xếp chunk nói về xếp hạng tốt nghiệp ở vị trí đầu. Hai nội dung đều chứa các khái niệm “điểm trung bình tích lũy” và “tốt nghiệp”, nên embedding đánh giá chúng gần nhau dù mục đích khác nhau: một bên hỏi  điều kiện , bên kia nói về  phân loại .

Điều này cho thấy embeddings biểu diễn ý nghĩa theo mức độ liên hệ tổng thể và ngữ cảnh từ vựng, chứ không mã hóa chính xác quan hệ logic hay ý định chi tiết. Vì vậy, các đoạn cùng chủ đề có thể nằm rất gần nhau trong không gian vector dù không trực tiếp trả lời câu hỏi. Semantic search cần kết hợp thêm metadata filter, cấu trúc tài liệu hoặc reranking để phân biệt những trường hợp gần nghĩa nhưng sai mục tiêu.

---

## 5. Kết quả truy xuất cá nhân

File [benchmark_queries.json](../data/vnu_university/benchmark_queries.json) chứa đúng 5 query và gold answer. Query 1 và 4 dùng `metadata_filter={"audience": "student"}`. Backend là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; chiến lược là `RecursiveChunker(chunk_size=700)`; `top_k=3`.

Lệnh chạy chiến lược cá nhân:

```powershell
$env:EMBEDDING_PROVIDER='local'
python scripts/run_personal_benchmark.py --provider local --chunker recursive --chunk-size 700 --top-k 3 --output data/vnu_university/personal_benchmark_results.json
```

### Kết quả semantic retrieval

| # | Query                                           | Top-1 chunk              |    Score | Relevant?                             | Câu trả lời grounded từ top-3                                                                                                                                                |
| - | ----------------------------------------------- | ------------------------ | -------: | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Giới hạn tín chỉ đăng ký học kỳ chính | Quy chế 3626, chunk 48  | 0.830431 | Có                                   | Tối thiểu 2/3 và tối đa 3/2 khối lượng trung bình; không tính học kỳ cuối khóa.                                                                                   |
| 2 | Thời hạn rút học phần và hoàn học phí  | Quy chế 3626, chunk 58  | 0.798816 | Có                                   | Trong 2 tuần đầu học kỳ chính hoặc 1 tuần đầu học kỳ phụ thì được hoàn học phí; quá hạn không được hoàn và có thể nhận điểm F nếu không học. |
| 3 | Ngưỡng cảnh báo học vụ                    | Quy chế 3626, chunk 127 | 0.794549 | Có                                   | Dưới 1,20 ở năm nhất; 1,40 ở năm hai; 1,60 ở năm ba; 1,80 ở các năm tiếp theo và cuối khóa.                                                                      |
| 4 | Điểm tích lũy tối thiểu để tốt nghiệp | Quy chế 3626, chunk 135 | 0.776855 | Không                                | Top-3 không chứa Điều 46 với điều kiện hệ chuẩn 2,00 và chương trình tài năng/chất lượng cao 2,50; không đủ ngữ cảnh để trả lời chắc chắn.         |
| 5 | Mức vay và thời hạn trả UOB 2011–2012     | UOB, chunk 1             | 0.524671 | Một phần ở top-1; đủ trong top-2 | Chunk 0 cho mức tối đa 10.000.000 đồng; chunk 1 cho thời hạn bắt đầu sau 6 tháng từ khi tốt nghiệp và trả trong 30 tháng.                                       |

**Số query có chunk liên quan trong top-3:** **4 / 5**.

### Tác động của metadata filter

Filter `{"audience": "student"}` ở Q1 vẫn giữ đúng Quy chế 3626 và top-1 trả lời đầy đủ. Tuy nhiên, cùng filter ở Q4 còn quá rộng: tài liệu học bổng dành cho sinh viên chiếm rank 2 và 3. Kết quả này cho thấy nên kết hợp thêm `category: undergraduate-training-regulation` khi query yêu cầu một loại quy định cụ thể.

### Failure case

Q4 hỏi “điểm tối thiểu để xét tốt nghiệp”, nhưng top-1 là chunk về **hạng tốt nghiệp** (Xuất sắc/Giỏi/Khá/Trung bình), không phải **điều kiện tốt nghiệp**. Hai khái niệm dùng chung các từ “điểm trung bình tích lũy” và “tốt nghiệp” nên embedding đánh giá rất gần. Cải thiện đề xuất: thêm `category` vào filter, viết query rõ “theo Điều 46”, hoặc chia văn bản theo ranh giới `Điều N` để tiêu đề điều luôn đi cùng nội dung.

### Ghi chú chất lượng nguồn

Landing page YSIP hiển thị số `3636/QĐ-ĐHQGHN`, trong khi chính văn quyết định và quy chế đính kèm ghi `3626/QĐ-ĐHQGHN`. Corpus dùng số trong chính văn là `3626/QĐ-ĐHQGHN` và giữ URL landing page để truy vết.

---

## Tự đánh giá

| Tiêu chí                      | Điểm tự đánh giá |
| ------------------------------- | ---------------------: |
| Khởi động                    |                  5 / 5 |
| Hướng tiếp cận cá nhân    |                10 / 10 |
| Core implementation             |                30 / 30 |
| Dự đoán similarity           |                  5 / 5 |
| Kết quả truy xuất cá nhân  |                 8 / 10 |
| **Tổng phần cá nhân** |      **58 / 60** |
