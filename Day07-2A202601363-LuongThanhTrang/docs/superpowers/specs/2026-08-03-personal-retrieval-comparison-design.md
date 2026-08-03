# Thiết kế so sánh chiến lược truy xuất cá nhân

## Phạm vi

Chỉ hoàn thiện `report/REPORT_CANHAN.md`; không sửa `report/REPORT_NHOM.md`. Thí nghiệm dùng năm query và gold answer trong `data/vnu_university/benchmark_queries.json` trên cùng corpus ĐHQGHN.

## Embedding và chiến lược

Dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. So sánh ba cấu hình:

- `FixedSizeChunker(chunk_size=700, overlap=100)`;
- `SentenceChunker(max_sentences_per_chunk=5)`;
- `RecursiveChunker(chunk_size=700)`.

Query 1 và 4 dùng `metadata_filter={"audience": "student"}` như yêu cầu K3. Các query còn lại dùng filter đã khai báo trong file benchmark.

## Đánh giá

Với mỗi chiến lược và query, kiểm tra thủ công top-3 so với gold answer. Một kết quả chỉ được tính đúng khi chunk chứa thông tin đủ để trả lời, không chỉ vì `doc_id` trùng tài liệu kỳ vọng.

Chiến lược cá nhân được chọn theo thứ tự:

1. số query có chunk liên quan trong top-3;
2. số query có chunk liên quan ở top-1;
3. tính mạch lạc và đầy đủ của chunk khi hai chỉ số trên hòa nhau.

## Đầu ra

`REPORT_CANHAN.md` ghi cấu hình, backend, top-1, score, đánh giá liên quan, kết quả top-3, failure case và giới hạn. Không dùng kết quả mock để kết luận chất lượng semantic retrieval.

## Xác minh

- Model local được tải và trả vector đúng kích thước.
- Mỗi chiến lược chạy đủ năm query.
- Metadata filter trả đúng `audience: student` ở query 1 và 4.
- Toàn bộ 42 unit test vẫn vượt qua.
