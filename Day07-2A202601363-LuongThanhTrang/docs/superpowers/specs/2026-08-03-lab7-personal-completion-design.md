# Thiết kế hoàn thiện phần cá nhân Lab 7

## Mục tiêu

Hoàn thiện phần cá nhân của Lab 7 theo `README.md`, `exercises.md` và rubric hiện có. Bài làm phải vượt qua bộ kiểm thử bắt buộc, giải thích được cách triển khai, và cung cấp kết quả thí nghiệm cá nhân có thể tái tạo mà không bịa dữ liệu hoặc kết quả của nhóm.

## Phạm vi

### Trong phạm vi

- Hoàn thiện các TODO trong `src/chunking.py`, `src/store.py` và `src/agent.py`.
- Giữ nguyên các API công khai mà `tests/test_solution.py` sử dụng.
- Xử lý hợp lý các trường hợp rỗng, vector có độ lớn bằng 0, `top_k` không dương, bộ lọc không khớp và xóa tài liệu không tồn tại.
- Chạy toàn bộ 42 bài kiểm thử bắt buộc và ghi kết quả thật vào báo cáo cá nhân.
- Hoàn thành các mục độc lập với corpus trong `report/REPORT_CANHAN.md`: thông tin sinh viên, warm-up, hướng tiếp cận, kết quả kiểm thử và dự đoán cosine similarity.
- Chuẩn bị một kịch bản benchmark có thể tái sử dụng sau khi người dùng bổ sung corpus và 5 câu hỏi của nhóm.
- Ghi rõ giới hạn môi trường nếu không thể chạy đúng Python 3.11 hoặc embedding đa ngữ tùy chọn.

### Ngoài phạm vi

- Không thu thập, crawl, dịch, tóm tắt hoặc tạo tài liệu nguồn VinUni.
- Không sửa hay thay thế hai tài liệu mẫu trong `data/k3_university/`.
- Không điền danh sách nguồn, gold answers hoặc kết quả retrieval khi chưa có corpus thật.
- Không bịa tên thành viên, chiến lược, điểm số hoặc kết luận so sánh nhóm.
- Không hoàn thiện các phần phụ thuộc dữ liệu thật trong `report/REPORT_NHOM.md`.

## Thiết kế mã nguồn

### Chunking và cosine similarity

`SentenceChunker` tách câu tại các dấu `.`, `!`, `?` khi theo sau là khoảng trắng hoặc xuống dòng, loại bỏ phần tử rỗng rồi nhóm tối đa theo `max_sentences_per_chunk`.

`RecursiveChunker` ưu tiên các dấu phân cách lớn trước. Đoạn còn vượt `chunk_size` được chuyển sang dấu phân cách kế tiếp; khi hết dấu phân cách hoặc gặp dấu phân cách rỗng, văn bản được cắt cứng theo `chunk_size`. Kết quả không chứa chunk rỗng và cố gắng giữ dấu phân cách để nội dung dễ đọc.

`compute_similarity` dùng cosine similarity, trả `0.0` nếu một vector có độ lớn bằng 0, và từ chối hai vector khác số chiều để tránh kết quả im lặng sai lệch.

`ChunkingStrategyComparator` chạy ba chiến lược có sẵn và trả `count`, `avg_length`, `chunks` cho từng chiến lược. Văn bản rỗng cho số lượng và độ dài trung bình bằng 0.

### EmbeddingStore

Store dùng backend trong bộ nhớ làm hành vi chuẩn, ổn định cho bài lab và unit test. Mỗi record chứa mã định danh lưu trữ duy nhất, nội dung, bản sao metadata và embedding. Metadata tự có `doc_id` lấy từ `Document.id` khi đầu vào chưa cung cấp.

Tìm kiếm nhúng query đúng một lần, tính dot product với các record ứng viên, sắp xếp giảm dần và trả tối đa `top_k`. Tìm kiếm có lọc thực hiện metadata pre-filter bằng phép so khớp chính xác tất cả cặp khóa–giá trị rồi mới xếp hạng. Xóa tài liệu loại bỏ mọi record có `metadata.doc_id` bằng mã được yêu cầu và trả về việc có bản ghi nào bị xóa hay không.

ChromaDB vẫn là tùy chọn, không phải điều kiện của phần bắt buộc. Việc thiếu ChromaDB không được làm hỏng store trong bộ nhớ.

### KnowledgeBaseAgent

Agent giữ tham chiếu tới store và hàm LLM được truyền vào. `answer()` truy xuất top-k chunk, dựng prompt phân tách rõ hướng dẫn, context và câu hỏi, yêu cầu chỉ trả lời từ context và thừa nhận khi không đủ thông tin, sau đó gọi `llm_fn` đúng một lần.

## Báo cáo và thí nghiệm cá nhân

`REPORT_CANHAN.md` sẽ ghi họ tên Lương Thanh Trang, chương trình AI Thực Chiến và ngày thực hiện. Phần warm-up trình bày phép tính chunking theo đúng công thức đề bài. Phần hướng tiếp cận mô tả đúng mã nguồn sau khi triển khai.

Thí nghiệm cosine dùng năm cặp câu do sinh viên tự chọn, ghi dự đoán trước và điểm thực tế từ một embedder có sẵn trong môi trường. Nếu chỉ có mock embedder, báo cáo phải ghi rõ điểm mock không có giá trị đánh giá ngữ nghĩa; không diễn giải nó như kết quả semantic.

Phần retrieval cá nhân giữ trạng thái chờ corpus và bộ query thật của nhóm. Không ghi điểm hay kết luận giả.

## Kịch bản benchmark chờ dữ liệu

Kịch bản hỗ trợ sẽ:

1. Nhận thư mục corpus từ biến môi trường hoặc tham số dòng lệnh.
2. Nạp dữ liệu qua `build_knowledge_base()` có sẵn.
3. Chạy các query được khai báo rõ ràng, trong đó hỗ trợ `metadata_filter={"audience": "student"}`.
4. In top-3 gồm score, `doc_id`, `chunk_index`, `title` và nội dung rút gọn để người dùng chép kết quả thật vào báo cáo.
5. Dừng với thông báo dễ hiểu nếu corpus hoặc cấu hình query chưa được cung cấp.

Kịch bản không chứa nguồn, gold answer hay kết quả dựng sẵn.

## Xử lý lỗi

- Tham số chunking không hợp lệ được phát hiện sớm bằng `ValueError`.
- Tìm kiếm trên store rỗng hoặc với `top_k <= 0` trả danh sách rỗng.
- Bộ lọc metadata không khớp trả danh sách rỗng.
- Agent vẫn tạo prompt có context rỗng để LLM có thể trả lời rằng không đủ thông tin.
- Lỗi của embedding function hoặc LLM được truyền lên cho caller; không che giấu lỗi cấu hình.

## Kiểm thử và tiêu chí hoàn tất

- `pytest tests/ -v` vượt toàn bộ 42 test hiện có.
- Bổ sung test tập trung cho các edge case mới nếu cần, nhưng không thay đổi test được cung cấp.
- `python ingest.py` vượt self-check.
- `python main.py` chạy được với dữ liệu mẫu và mock embedder.
- Kịch bản benchmark từ chối chạy có kiểm soát khi chưa có dữ liệu/query thật.
- Không còn TODO hoặc `NotImplementedError` trong ba module bắt buộc.
- Báo cáo cá nhân không còn placeholder ở các mục có thể hoàn thành độc lập; các mục phụ thuộc nhóm được đánh dấu chờ dữ liệu thật.

## Giới hạn môi trường

Repo yêu cầu Python 3.11 nhưng máy hiện chỉ phát hiện Python 3.12 và virtual environment hiện tại chưa có pytest. Việc triển khai sẽ ưu tiên chạy test bằng interpreter sẵn có; báo cáo sẽ ghi đúng phiên bản thực tế. Không tuyên bố đã kiểm thử trên Python 3.11 nếu interpreter đó không tồn tại.
