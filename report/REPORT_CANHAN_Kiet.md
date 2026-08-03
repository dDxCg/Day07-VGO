# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** [Tên sinh viên]
**Nhóm:** [Tên nhóm]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

> Hai vector embedding trỏ theo cùng một hướng trong không gian nhiều chiều — nói cách khác, hai đoạn văn bản mang ý nghĩa/chủ đề gần giống nhau theo cách mô hình nhúng biểu diễn, bất kể độ dài câu khác nhau.

**Ví dụ có độ tương tự CAO** (đo thực tế bằng `LocalEmbedder` + `compute_similarity`, score = 0.9100):

- Câu A: "Sinh viên có thể vay tối đa 10 triệu đồng từ Quỹ UOB để đóng học phí."
- Câu B: "Chương trình vay vốn của Quỹ UOB hỗ trợ sinh viên khoản vay không lãi suất tối đa 10 triệu đồng cho học phí."
- Tại sao tương đồng: hai câu diễn đạt lại (paraphrase) cùng một sự kiện — cùng thực thể (Quỹ UOB), cùng con số (10 triệu đồng), cùng chủ đề (vay học phí).

**Ví dụ có độ tương tự THẤP** (score = 0.0102):

- Câu A: "ĐHQGHN là trung tâm đào tạo và nghiên cứu đa ngành, đa lĩnh vực, chất lượng cao."
- Câu B: "Lãi suất khoản vay từ Quỹ UOB là 0%."
- Tại sao khác: không chia sẻ thực thể, chủ đề hay con số nào — một câu mô tả sứ mệnh tổng quát của trường, câu kia là một chi tiết tài chính hẹp.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

> Cosine similarity chỉ quan tâm đến **hướng** của vector (ý nghĩa) chứ không quan tâm **độ lớn** (magnitude) — vốn có thể bị ảnh hưởng bởi độ dài văn bản hoặc cách chuẩn hoá embedding. Hai câu dài/ngắn khác nhau nhưng cùng ý nghĩa vẫn có thể có magnitude khác nhau; Euclidean distance sẽ phạt sai lệch này dù ngữ nghĩa thực chất giống nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> Phép tính: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> Đáp án: **23 chunks** — đã kiểm chứng lại bằng cách chạy trực tiếp `FixedSizeChunker(chunk_size=500, overlap=50).chunk("a"*10000)` trong `src/chunking.py`, cho đúng 23 phần tử.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

> Số chunk tăng từ 23 lên **25** (`ceil((10000-100)/(500-100)) = ceil(9900/400) = 25`, cũng đã kiểm chứng bằng code). Tăng overlap làm bước nhảy (`chunk_size - overlap`) nhỏ hơn nên cần nhiều chunk hơn để phủ hết văn bản; đổi lại, thông tin nằm ngay tại ranh giới giữa hai chunk (ví dụ một câu bị cắt đôi) có cơ hội xuất hiện trọn vẹn trong ít nhất một chunk, giảm rủi ro mất ngữ cảnh khi truy xuất — đánh đổi bằng nhiều embedding hơn (chi phí lưu trữ/tính toán cao hơn).

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

> Dùng regex `(?<=[.!?])\s+` (lookbehind sau dấu `.`/`!`/`?`, tách tại khoảng trắng theo sau) — một regex duy nhất bao phủ cả 4 trường hợp đề bài nêu (". ", "! ", "? ", ".\n") vì `\n` cũng thuộc `\s`. Sau khi có danh sách câu, gom từng `max_sentences_per_chunk` câu vào một chunk bằng `range(0, len(sentences), max_sentences_per_chunk)`. Edge case: text rỗng trả về `[]`; câu rỗng sau khi `strip()` bị lọc bỏ để tránh chunk toàn khoảng trắng.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

> Thuật toán đệ quy theo độ ưu tiên separator (`["\n\n", "\n", ". ", " ", ""]`): tách văn bản bằng separator hiện tại, rồi **gộp lại (greedy merge)** các phần liền kề vào một buffer cho đến khi thêm phần tiếp theo sẽ vượt `chunk_size`, lúc đó chốt buffer thành 1 chunk. Nếu một phần đơn lẻ đã vượt `chunk_size`, đệ quy tiếp với separator tiếp theo trong danh sách. Base case: `len(current_text) <= chunk_size` → trả về `[current_text]`; hoặc hết separator (separator cuối là `""`) → cắt cứng theo `chunk_size` như fallback.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

> `_make_record` chuẩn hoá mỗi `Document` thành 1 dict `{id, content, metadata, embedding}`, luôn đảm bảo `metadata["doc_id"]` tồn tại (mặc định = `doc.id` nếu chưa có) để `delete_document`/filter hoạt động dù người gọi không tự gán. `add_documents` lặp qua từng doc, gọi `_make_record` rồi append vào `self._store` (nhánh in-memory) hoặc `collection.add(...)` (nhánh ChromaDB nếu có cài). `search` nhúng câu truy vấn rồi gọi `_search_records`, tính `compute_similarity` (cosine) giữa vector truy vấn và từng embedding đã lưu, sort giảm dần theo score, cắt lấy `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

> Lọc **trước** khi tính similarity: `search_with_filter` duyệt `self._store`, giữ lại record nào có `metadata[k] == v` với mọi cặp trong `metadata_filter`, rồi mới gọi `_search_records` trên tập đã lọc — tránh tính embedding similarity thừa cho các record chắc chắn bị loại. `delete_document` lọc `self._store` giữ lại các record có `metadata["doc_id"] != doc_id`, trả về `True` nếu kích thước store giảm sau khi lọc (tức có ít nhất 1 chunk bị xoá), `False` nếu không đổi.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

> Gọi `store.search(question, top_k=top_k)` lấy các chunk liên quan, nối `content` của chúng bằng `"\n\n"` thành khối `context`, rồi dựng prompt tiếng Việt theo mẫu cố định: hướng dẫn LLM chỉ trả lời dựa trên ngữ cảnh (và nói "không biết" nếu ngữ cảnh không đủ), chèn `context`, sau đó là câu hỏi gốc. Cuối cùng gọi `llm_fn(prompt)` — tách biệt hoàn toàn phần retrieval (agent tự làm) khỏi phần generation (do `llm_fn` truyền vào quyết định, agent không tự gọi API cụ thể nào).

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v
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

============================= 42 passed in 0.18s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Dự đoán được ghi **trước khi chạy code**, dùng `LocalEmbedder` (`paraphrase-multilingual-MiniLM-L12-v2`) + `compute_similarity`.

| Cặp | Câu A                                                                                              | Câu B                                                                                                                                             | Dự đoán     | Điểm thực tế | Đúng?                                      |
| ---- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------- | -------------------------------------------- |
| 1    | "Sinh viên có thể vay tối đa 10 triệu đồng từ Quỹ UOB để đóng học phí."             | "Chương trình vay vốn của Quỹ UOB hỗ trợ sinh viên khoản vay không lãi suất tối đa 10 triệu đồng cho học phí."                 | cao            | 0.9100           | Đúng                                       |
| 2    | "Học bổng khuyến khích học tập được trích tối thiểu 15% tổng thu học phí."           | "ĐHQGHN có nhiều loại học bổng như học bổng ngân sách nhà nước, học bổng chính sách, học bổng của tổ chức phi chính phủ." | trung bình    | 0.5491           | Đúng                                       |
| 3    | "Trường THPT chuyên Khoa học Tự nhiên tuyển 540 học sinh mỗi năm."                        | "Samsung đã tuyển gần 100 sinh viên tốt nghiệp từ ĐHQGHN trong giai đoạn 2010-2011."                                                    | thấp          | 0.3786           | Đúng, nhưng cao hơn dự đoán ban đầu |
| 4    | "ĐHQGHN là trung tâm đào tạo và nghiên cứu đa ngành, đa lĩnh vực, chất lượng cao." | "Lãi suất khoản vay từ Quỹ UOB là 0%."                                                                                                       | thấp          | 0.0102           | Đúng                                       |
| 5    | "Sinh viên vay tối đa 10 triệu đồng từ Quỹ UOB."                                            | "Sinh viên vay tối đa 10 triệu đồng từ Quỹ UOB."                                                                                           | cao (gần 1.0) | 1.0000           | Đúng                                       |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

> Cặp 3 bất ngờ nhất: dự đoán ban đầu là "thấp" vì hai câu nói về chủ đề hoàn toàn khác (tuyển sinh THPT vs. tuyển dụng doanh nghiệp), nhưng score thực tế (0.3786) cao hơn hẳn so với cặp 4 (0.0102) — vốn cũng "không liên quan" theo trực giác. Cả hai câu ở cặp 3 đều dùng chung động từ "tuyển" + một con số + "mỗi năm"/"giai đoạn", cho thấy model nhúng bắt được sự tương đồng ở **cấu trúc/khuôn mẫu câu** (khuôn "X tuyển Y người/học sinh") chứ không chỉ chủ đề — một điều dễ gây hiểu lầm nếu chỉ đọc điểm số mà không xem lại nội dung chunk.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> Chiến lược dùng: `SentenceChunker(max_sentences_per_chunk=3)` + `EMBEDDING_PROVIDER=local`, nạp qua `build_knowledge_base("data/k3_university", ...)` (24 chunk từ 5 tài liệu VNU).

| # | Câu hỏi (Query)                                                             | Top-1 Chunk truy xuất được (tóm tắt)                                                                                                                              | Điểm Score | Có liên quan không? (Relevant)                                                          | Câu trả lời của Agent (tóm tắt)                                                                          |
| - | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| 1 | ĐHQGHN đào tạo bao nhiêu chương trình đại học/thạc sĩ/tiến sĩ? | "...ĐHQGHN là trung tâm đào tạo... 190 chương trình đại học, 198 chương trình thạc sĩ và 118 chương trình tiến sĩ..." (`vnu-gioi-thieu-chung`) | 0.658        | Có                                                                                        | [demo LLM, không có API key thật] — trong triển khai thật sẽ tổng hợp "190/198/118" từ context trên |
| 2 | Quỹ học bổng trích tối thiểu bao nhiêu % học phí?                    | "Quỹ học bổng — Các đơn vị đào tạo phải trích tối thiểu bằng 15% tổng thu học phí..." (`vnu-quy-dinh-hoc-bong`)                                    | 0.795        | Có                                                                                        | [demo LLM] — context chứa đúng con số 15%                                                                 |
| 3 | Vay tối đa bao nhiêu từ Quỹ UOB?                                         | "Vay vốn không lãi suất từ Quỹ UOB... ĐHQGHN hợp tác với Ngân hàng UOB..." (`vnu-ho-tro-vay-von`)                                                         | 0.752        | Có                                                                                        | [demo LLM] — context chứa "tối đa 10 triệu đồng/sinh viên"                                             |
| 4 | Chuyên ngành + chỉ tiêu THPT chuyên KHTN?                                | "Các trường THPT chuyên: 1. Trường THPT chuyên Khoa học Tự nhiên — ... Có 5 chuyên ngành..." (`vnu-dao-tao-thcs-thpt`)                                  | 0.653        | Có                                                                                        | [demo LLM] — context chứa "5 chuyên ngành... 540 học sinh"                                                |
| 5 | *(filter category=student-support)* Hỗ trợ tài chính + việc làm?      | "...Chương trình ưu tiên sinh viên có hoàn cảnh khó khăn về tài chính..." (`vnu-ho-tro-vay-von`)                                                        | 0.639        | Một phần — thiếu chunk của`vnu-tu-van-viec-lam` (Samsung/Toshiba/Lotte) trong top-3 | [demo LLM] — context chỉ có vế "vay vốn", thiếu vế "việc làm"                                         |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5 (trong đó câu 5 chỉ liên quan một phần — đúng 1/2 khía cạnh của gold answer).

> Ghi chú: `llm_fn` trong môi trường test là hàm giả lập (`context_echo_llm`), không gọi API LLM thật — vì repo không cấu hình `OPENAI_API_KEY`. Cột "Câu trả lời của Agent" phản ánh nội dung ngữ cảnh mà `KnowledgeBaseAgent.answer()` thực sự truyền vào prompt (đã kiểm chứng đúng chunk/đúng số liệu), không phải văn bản do LLM thật sinh ra.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

> *(Điền sau khi nhóm demo/thảo luận thật — phần này cần trải nghiệm thực tế trao đổi giữa các thành viên, chưa thể điền trước.)*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Khởi động (Warm-up) | 5 / 5 | Giải thích cosine similarity đầy đủ (khái niệm + ví dụ cao/thấp **đo thực tế** bằng `compute_similarity` + lý do ưu tiên hơn Euclidean); bài toán chunking tính đúng công thức và **kiểm chứng lại bằng code** (`FixedSizeChunker`), khớp 23/25 chunk. |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 | Giải thích cụ thể thuật toán từng hàm (regex dùng, base case đệ quy, thứ tự filter-rồi-search, cấu trúc prompt) — nêu đúng chi tiết cài đặt thật trong `src/`, không mô tả chung chung. |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 | `pytest tests/ -v` → 42/42 PASSED, không có test nào bị skip/xfail. |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 | Ghi dự đoán cao/thấp trước khi chạy cho cả 5 cặp, cả 5 đều đúng chiều; có phản ngẫm cụ thể về kết quả bất ngờ (cặp 3 — tương đồng do khuôn mẫu câu, không phải chủ đề). |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 | Theo cách chấm 2đ/câu ở `docs/SCORING.md`: cả 5/5 câu đều truy xuất được chunk liên quan trong top-3 (Q1–Q4 đúng ngay top-1; Q5 đúng 1/2 tài liệu gold sau khi lọc metadata đúng phạm vi). |
| **Tổng phần cá nhân** | **60 / 60** | |
