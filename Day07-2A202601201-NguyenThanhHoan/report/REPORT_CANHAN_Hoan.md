# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thanh Hoàn - 2A202601201

**Lớp/biến thể:** K3 — Dịch vụ đại học

**Nhóm:** T029

**Ngày:** 2026-08-03

> Phạm vi hiện tại chỉ gồm phần cá nhân. Mục 5 được giữ ở trạng thái chờ vì rubric bắt buộc dùng đúng 5 câu hỏi benchmark do nhóm thống nhất.

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Bài tập 1.1)

**Độ tương tự cosine cao nghĩa là gì?**

Hai embedding có cosine cao khi chúng hướng gần giống nhau trong không gian vector. Với văn bản, điều này thường cho biết hai đoạn gần nhau về chủ đề hoặc ý nghĩa, dù không nhất thiết dùng cùng từ.

**Ví dụ có độ tương tự CAO:**

- Câu A: “Sinh viên đăng ký học phần trên cổng học vụ theo lịch từng học kỳ.”
- Câu B: “Mỗi học kỳ, người học chọn môn trên hệ thống đăng ký theo thời gian được công bố.”
- Tại sao tương đồng: Hai câu cùng mô tả việc đăng ký môn trên hệ thống theo lịch học kỳ; khác cách diễn đạt nhưng giữ cùng ý chính.

**Ví dụ có độ tương tự THẤP:**

- Câu A: “Thư viện cung cấp không gian học tập cho sinh viên.”
- Câu B: “Dự báo thời tiết cho biết ngày mai có mưa lớn.”
- Tại sao khác: Hai câu thuộc hai chủ đề và mục đích hoàn toàn khác nhau: dịch vụ thư viện và thời tiết.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**

Cosine tập trung vào hướng của vector, tức mẫu phân bố đặc trưng biểu diễn ý nghĩa, và ít bị ảnh hưởng bởi độ lớn vector. Euclidean distance chịu tác động mạnh hơn từ độ lớn; hai vector cùng hướng nhưng khác scale vẫn có thể bị xem là xa nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10.000 ký tự, `chunk_size=500`, `overlap=50`:**

```text
ceil((10.000 - 50) / (500 - 50))
= ceil(9.950 / 450)
= ceil(22,111...)
= 23 chunks
```

**Nếu `overlap` tăng lên 100:**

```text
ceil((10.000 - 100) / (500 - 100))
= ceil(9.900 / 400)
= ceil(24,75)
= 25 chunks
```

Số chunk tăng từ 23 lên 25 vì bước trượt giảm từ 450 xuống 400 ký tự. Overlap lớn hơn giúp giữ ngữ cảnh nằm sát ranh giới chunk, nhưng tăng dung lượng lưu trữ, thời gian embedding và số ứng viên truy xuất.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ

**`SentenceChunker.chunk`:**

Dùng regex `(?<=[.!?])(?:[ \t]+|\r?\n+)` để tách sau dấu kết thúc câu khi có khoảng trắng hoặc xuống dòng; dấu câu vẫn thuộc câu đứng trước. Hàm loại phần rỗng, chuẩn hóa khoảng trắng, trả `[]` cho chuỗi rỗng và gom tối đa `max_sentences_per_chunk` câu vào mỗi chunk.

**`RecursiveChunker.chunk` / `_split`:**

Thuật toán thử separator theo thứ tự `\n\n`, `\n`, `. `, khoảng trắng, rồi hard split. Nếu đoạn đã không dài hơn `chunk_size`, đó là base case; nếu không còn separator hữu ích, hàm cắt cứng theo kích thước để luôn kết thúc. Các separator được gắn lại trước khi gom đoạn nhỏ nhằm tránh làm mất ranh giới cấu trúc gốc.

### Lớp `EmbeddingStore`

**`add_documents` + `search`:**

Mỗi `Document` được chuẩn hóa thành bản ghi gồm ID gốc, ID lưu trữ duy nhất, nội dung, bản sao metadata và embedding. Store giữ bản in-memory làm nguồn dữ liệu chính, đồng thời mirror sang collection ChromaDB biệt lập nếu Chroma khả dụng; tìm kiếm nhúng query, tính dot product với mọi ứng viên, sắp giảm dần và lấy `top_k`. Với E5, store gọi `embed_document()` để thêm prefix `passage:` và `embed_query()` để thêm prefix `query:`; với embedding đã normalize, dot product tương đương cosine similarity.

**`search_with_filter` + `delete_document`:**

Metadata được lọc trước bằng phép khớp chính xác mọi cặp khóa–giá trị, rồi mới tính similarity, tránh để tài liệu sai đối tượng chiếm top-k. Xóa dựa trên `metadata['doc_id']`, nên một lần gọi loại bỏ toàn bộ chunk thuộc tài liệu cha; hàm trả `True` chỉ khi thực sự có bản ghi bị xóa.

### Tác tử `KnowledgeBaseAgent`

**`answer`:**

Agent lấy top-k chunk, đánh số từng đoạn và chèn chúng vào vùng `NGỮ CẢNH` tách biệt với `CÂU HỎI`. Prompt yêu cầu LLM chỉ dùng bằng chứng được truy xuất, nói rõ khi thiếu thông tin và không suy đoán; sau đó chuyển prompt hoàn chỉnh cho `llm_fn`.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Đã hoàn thiện toàn bộ TODO trong:

- `src/chunking.py`: `SentenceChunker`, `RecursiveChunker`, `compute_similarity`, `ChunkingStrategyComparator`.
- `src/store.py`: khởi tạo store, thêm, tìm kiếm, đếm, lọc metadata và xóa tài liệu.
- `src/agent.py`: khởi tạo agent và pipeline retrieve–prompt–generate.

### Kết quả kiểm thử

Lệnh chạy: `python -m pytest tests -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.10.9, pytest-9.1.1
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 1.03s ==============================
```

**Số lượng bài test vượt qua:** **42 / 42**

> Ghi chú môi trường: máy hiện có Python 3.10.9 và 3.9; chưa có Python 3.11 như chuẩn lab. Toàn bộ test đã pass trên Python 3.10.9, nhưng nên chạy lại một lần bằng Python 3.11 trước khi nộp nếu môi trường lớp cung cấp interpreter này.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Các dự đoán được ghi trước khi chạy. Điểm thực tế dùng model **`intfloat/multilingual-e5-large`** đã tải sẵn trên máy, chạy offline, embedding 1.024 chiều và normalize vector. Theo quy ước E5, câu A dùng prefix `query:` và câu B dùng prefix `passage:`; điểm được tính bằng chính `compute_similarity()`.

| Cặp | Câu A | Câu B | Dự đoán trước khi chạy | Điểm thực tế | Đúng? |
|---:|---|---|---|---:|---|
| 1 | Sinh viên đăng ký học phần trên cổng học vụ theo lịch từng học kỳ. | Mỗi học kỳ, người học chọn môn trên hệ thống đăng ký theo thời gian được công bố. | Cao | 0,8547 | Có |
| 2 | Người dùng cần mang thẻ định danh hợp lệ khi mượn tài liệu thư viện. | Sinh viên phải xuất trình thẻ còn hiệu lực để sử dụng dịch vụ mượn sách. | Cao | 0,8255 | Có, nhưng thấp hơn dự kiến tương đối |
| 3 | Sinh viên cần kiểm tra học phần tiên quyết trước khi xác nhận đăng ký. | Thời hạn đóng học phí được thông báo vào đầu học kỳ. | Thấp | 0,8329 | Không |
| 4 | Thư viện cung cấp không gian học tập cho sinh viên. | Dự báo thời tiết cho biết ngày mai có mưa lớn. | Thấp nhất | 0,8033 | Có |
| 5 | Sinh viên được phép gia hạn tài liệu trực tuyến. | Sinh viên không được phép gia hạn tài liệu trực tuyến. | Cao về chủ đề dù nghĩa phủ định đối lập | 0,8555 | Có |

**Kết quả bất ngờ nhất và phản ngẫm:**

Cặp 5 có điểm cao nhất dù hai câu khẳng định hai quy định trái ngược nhau. E5 nhận ra chúng gần như trùng chủ đề và từ vựng, nhưng cosine similarity không phải phép kiểm tra suy luận hay mâu thuẫn. Cặp 3 cũng cao hơn dự đoán vì hai câu cùng nằm trong bối cảnh học vụ, sinh viên và học kỳ; điều này cho thấy nên đánh giá theo thứ hạng trong cùng tập ứng viên, không dùng một ngưỡng “cao/thấp” tuyệt đối thiếu hiệu chỉnh.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

### Corpus và cấu hình đánh giá

Crawler đã tải 5 trang công khai trong `scripts/urls.csv`, sau đó `scripts/clean_corpus.py` loại footer/thông báo ngoài bài và đồng bộ `sources.csv`. Corpus dùng đúng 5 tài liệu sau:

1. [Giới thiệu chung về công tác đào tạo ĐHQGHN](https://vnu.edu.vn/dao-tao/gioi-thieu-chung)
2. [Quy định về quản lý và sử dụng học bổng tại ĐHQGHN](https://vnu.edu.vn/quy-dinh-ve-quan-ly-va-su-dung-hoc-bong-tai-dai-hoc-quoc-gia-ha-noi-post10552.html)
3. [Đào tạo hệ THCS và THPT](https://vnu.edu.vn/dao-tao/dao-tao-he-thcs-va-thpt)
4. [Hỗ trợ sinh viên vay vốn](https://vnu.edu.vn/sinh-vien/ho-tro-sinh-vien/vay-von)
5. [Tư vấn hỗ trợ việc làm](https://vnu.edu.vn/sinh-vien/ho-tro-sinh-vien/tu-van-ho-tro-viec-lam)

Cấu hình cuối: `intfloat/multilingual-e5-large` chạy offline, vector 1.024 chiều, `RecursiveChunker(chunk_size=800)`, 108 chunk. Câu 4 dùng `metadata_filter={"audience": "student"}`. `llm_fn` là bộ chọn bằng chứng extractive cục bộ, xác định và không gọi API sinh văn bản. Kết quả máy đọc đầy đủ nằm tại `report/individual_evaluation.json`.

### Năm câu hỏi, gold answers và kết quả

| # | Câu hỏi / Gold answer | Top-1 chunk truy xuất | Score | Bằng chứng trong top-3? | Câu trả lời Agent (tóm tắt) |
|---:|---|---|---:|---|---|
| 1 | **Hỏi:** ĐHQGHN đang triển khai bao nhiêu chương trình đại học, thạc sĩ và tiến sĩ? **Gold:** 190, 198 và 118 chương trình. | `vnu-training-overview`, chunk 0; chứa đủ ba số liệu. | 0,901904 | Có, rank 1 | 190 chương trình đại học, 198 thạc sĩ và 118 tiến sĩ. |
| 2 | **Hỏi:** Theo tài liệu được đánh dấu hết hiệu lực, quỹ học bổng tối thiểu bằng bao nhiêu phần trăm tổng thu học phí? **Gold:** 15%. | `vnu-scholarship-management-regulation`, chunk 14; nói về phân bổ học bổng, còn bằng chứng “15%” ở rank 3. | 0,856830 | Có, rank 3 | Tối thiểu 15% tổng thu học phí từ sinh viên đại học hệ chính quy. |
| 3 | **Hỏi:** ĐHQGHN có 01 trường THCS và 04 trường THPT nào? **Gold:** 01 THCS và 04 THPT. | `vnu-secondary-and-high-school-education`, chunk 0; nêu đủ tên năm trường. | 0,908812 | Có, rank 1 | 01 trường THCS Ngoại ngữ và 04 trường THPT được liệt kê trong nguồn. |
| 4 | **Hỏi:** Quỹ UOB cho vay tối đa bao nhiêu, lãi suất và lịch trả nợ thế nào? **Gold:** 10 triệu đồng, 0%, bắt đầu sau tốt nghiệp 6 tháng và trả trong 30 tháng/30 kỳ. | `vnu-student-loans`, chunk 0; chứa hạn mức và lãi suất. Chunk 1 ở rank 3 chứa lịch trả nợ. | 0,910694 | Có, hợp rank 1 + rank 3 | Tối đa 10.000.000 đồng, lãi suất 0%; trả sau 6 tháng kể từ tốt nghiệp, dần trong 30 tháng theo 30 kỳ. |
| 5 | **Hỏi:** Sinh viên nào được tham dự Ngày hội việc làm Samsung? **Gold:** năm 3 và năm cuối thuộc hai nhóm ngành được nêu. | `vnu-career-support`, chunk 0; chứa đúng đối tượng và nhóm ngành. | 0,900890 | Có, rank 1 | Sinh viên năm 3 và năm cuối thuộc Kinh tế–Luật–Ngoại ngữ hoặc Khoa học–Kỹ thuật–Công nghệ. |

**Bao nhiêu câu hỏi trả về đủ bằng chứng liên quan trong top-3?** **5 / 5**.

### Quan sát và giới hạn

- Với `chunk_size=500`, câu UOB bị cắt khiến top-3 chưa giữ đủ hạn mức, lãi suất và lịch trả nợ. Tăng lên 800 giúp rank 1 và rank 3 cùng cung cấp trọn bộ bằng chứng; đây là ví dụ retrieval cần tổng hợp nhiều chunk thay vì chỉ đọc top-1.
- Câu học bổng có tài liệu ghi rõ **“Hết hiệu lực”**; kết quả chỉ phản ánh nội dung lịch sử, không được dùng như chính sách hiện hành.
- Trang vay vốn và việc làm chứa thông tin chương trình từ năm 2010–2011; metadata `document_version=not-stated`. Hệ thống truy xuất đúng nguồn nhưng độ mới của nguồn vẫn là rủi ro dữ liệu.
- Chưa có demo với thành viên khác. Bài học cá nhân hiện tại: kiểm tra bằng chứng thật trong top-3 quan trọng hơn chỉ kiểm tra đúng `doc_id`; phần học từ nhóm sẽ bổ sung khi làm Giai đoạn 2.

---

## Tự đánh giá phần cá nhân

| Tiêu chí | Điểm tự đánh giá |
|---|---:|
| Khởi động | 5 / 5 |
| Hướng tiếp cận của tôi | 10 / 10 |
| Hoàn thiện code | 30 / 30 |
| Dự đoán độ tương tự | 5 / 5 |
| Kết quả truy xuất của tôi | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
