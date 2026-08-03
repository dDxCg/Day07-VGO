# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Tên nhóm]
**Thành viên:** Kiệt, Hoàn, Cường, Trang
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Phạm vi bộ tài liệu (Scope)

**Chủ đề (cố định theo lớp K3):** Dịch vụ / quy định đại học (đăng ký môn, học phí, học bổng, thư viện, ký túc xá…).

**Phạm vi cụ thể nhóm tập trung:** Thông tin đào tạo, học bổng và hỗ trợ sinh viên (tài chính + việc làm) tại Đại học Quốc gia Hà Nội (ĐHQGHN) — nguồn công khai từ `vnu.edu.vn`.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Giới thiệu chung về công tác đào tạo | vnu.edu.vn/dao-tao/gioi-thieu-chung | 2026-08-03 / 1.0 | 938 | audience=all, department=university-administration, category=general-information |
| 2 | Quy định về quản lý và sử dụng học bổng tại ĐHQGHN | vnu.edu.vn/quy-dinh-ve-quan-ly-va-su-dung-hoc-bong-tai-dai-hoc-quoc-gia-ha-noi-post10552.html | 2026-08-03 / 1.0 (⚠️ văn bản gốc đã hết hiệu lực, QĐ 597/CT-HSSV 2008) | 1257 | audience=all, department=university-administration, category=scholarships |
| 3 | Đào tạo hệ THCS và THPT | vnu.edu.vn/dao-tao/dao-tao-he-thcs-va-thpt | 2026-08-03 / 1.0 | 1415 | audience=all, department=university-administration, category=education |
| 4 | Hỗ trợ sinh viên vay vốn | vnu.edu.vn/sinh-vien/ho-tro-sinh-vien/vay-von | 2026-08-03 / 1.0 | 1172 | audience=all, department=university-administration, category=student-support |
| 5 | Tư vấn hỗ trợ việc làm | vnu.edu.vn/sinh-vien/ho-tro-sinh-vien/tu-van-ho-tro-viec-lam | 2026-08-03 / 1.0 | 1089 | audience=all, department=university-administration, category=student-support |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

> **Lưu ý quản trị:** tài liệu #2 (quy định học bổng) đã **hết hiệu lực** theo chính trang nguồn công bố — nhóm giữ lại vì vẫn hữu ích để minh họa retrieval, nhưng không dùng làm căn cứ chính sách hiện hành khi thuyết trình.
> Cả 5 tài liệu hiện có `audience: all` (do nguồn CSV nhóm thu thập ghi "Public") — chưa có tài liệu nào audience=student riêng biệt, nên câu hỏi benchmark #5 dùng `category` thay vì `audience` để minh họa metadata filtering (xem Phần 3).

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `audience` | string (enum) | `all` | Lọc theo đối tượng đọc (yêu cầu bắt buộc của K3), dù trong bộ dữ liệu hiện tại mọi doc đều là `all` |
| `department` | string | `university-administration` | Phân biệt đơn vị phụ trách nội dung |
| `category` | string | `scholarships`, `student-support`, `education`, `general-information` | Trường phân biệt tốt nhất trong bộ dữ liệu này — dùng làm `metadata_filter` để tách nhóm tài liệu theo chủ đề con |
| `source_url` / `retrieved_at` / `document_version` | string | xem bảng trên | Truy vết nguồn, kiểm tra độ mới/hiệu lực của thông tin (quan trọng với tài liệu #2 đã hết hiệu lực) |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=200)` trên tài liệu #2 (`vnu-quy-dinh-hoc-bong`, 1257 ký tự), dùng làm đại diện:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| vnu-quy-dinh-hoc-bong | FixedSizeChunker (`fixed_size`) | 9 | 184.1 | Không — cắt cứng theo ký tự, thường vỡ giữa câu/mục |
| vnu-quy-dinh-hoc-bong | SentenceChunker (`by_sentences`) | 6 | 208.0 | Có — chunk kết thúc trọn câu, nhưng danh sách đánh số (1., 2., 3.) có thể bị tách rời số thứ tự khỏi nội dung |
| vnu-quy-dinh-hoc-bong | RecursiveChunker (`recursive`) | 10 | 124.1 | Trung bình — ưu tiên tách theo đoạn/câu nhưng với văn bản ngắn, chunk_size=200 làm chunk quá nhỏ, vỡ vụn ngữ cảnh |

Hai tài liệu khác cùng chunk_size=200 để đối chiếu quy mô: `vnu-ho-tro-vay-von` (1172 ký tự) → fixed=8/avg 190.2, sentences=5/avg 232.8, recursive=10/avg 115.7. `vnu-dao-tao-thcs-thpt` (1415 ký tự) → fixed=10/avg 186.5, sentences=9/avg 156.0, recursive=12/avg 116.5.

**Nhận xét:** cả 5 tài liệu đều khá ngắn (938–1415 ký tự). Với `chunk_size=200`, `RecursiveChunker` tạo ra nhiều chunk nhỏ nhất (trung bình ~115-125 ký tự) — quá vụn cho văn bản ngắn, dễ mất ngữ cảnh câu mở đầu (tiêu đề, chủ ngữ). Đây chính là nguyên nhân của failure case ở Phần 4.

### Chiến lược đã thử nghiệm — theo từng thành viên

> Mỗi thành viên chạy một cấu hình trên cùng bộ tài liệu; dữ liệu dưới đây được đo bằng `EMBEDDING_PROVIDER=local` (`paraphrase-multilingual-MiniLM-L12-v2`) trên toàn bộ 5 câu hỏi benchmark ở Phần 3.

**Thành viên: Kiệt — Cấu hình A — RecursiveChunker(chunk_size=200)**
- **Mô tả & lý do chọn:** chunk_size mặc định gợi ý trong `exercises.md` (Bài tập 3.1). Với văn bản ngắn của bộ dữ liệu này, cho ra quá nhiều chunk nhỏ.
- **Kết quả:** 49 chunk tổng, 3/5 câu hỏi có chunk đúng trong top-3.

**Thành viên: Hoàn — Cấu hình B — RecursiveChunker(chunk_size=500)**
- **Mô tả & lý do chọn:** tăng chunk_size gần với độ dài trung bình cả tài liệu (~1200 ký tự → mỗi doc còn 2-4 chunk).
- **Kết quả:** 17 chunk tổng, 3/5 câu hỏi đúng — cải thiện với câu hỏi cụ thể-số-liệu (Q3, Q4) nhưng tài liệu dài nhất (`vnu-dao-tao-thcs-thpt`, nhiều số liệu) lấn át kết quả của câu hỏi khác.

**Thành viên: Cường — Cấu hình C — SentenceChunker(max_sentences_per_chunk=3)** ⭐ chiến lược được chọn
- **Mô tả & lý do chọn:** chia theo ranh giới câu, giữ trọn câu chứa số liệu/tên riêng — phù hợp với văn bản hành chính ngắn, nhiều câu chứa 1 sự kiện/con số độc lập.
- **Kết quả:** 24 chunk tổng, **4/5 câu hỏi đúng ngay ở top-1** (xem Phần 3).

**Thành viên: Trang — Cấu hình D — FixedSizeChunker(chunk_size=500, overlap=50)**
- **Mô tả & lý do chọn:** baseline đã có sẵn, dùng làm đối chứng.
- **Kết quả:** 15 chunk tổng, 3/5 câu hỏi đúng — cắt cứng theo ký tự làm mất câu mở đầu chứa số liệu tổng quan (Q1, Q2).

### So Sánh Giữa Các Thành Viên

| Thành viên | Cấu hình | Chiến lược (Strategy) | Điểm truy xuất (/5 câu) | Điểm mạnh | Điểm yếu |
|-----------|-----------|----------|----------------------|-----------|----------|
| Kiệt | A | Recursive, chunk_size=200 | 3/5 | Chunk nhỏ, chi tiết | Quá vụn với văn bản ngắn |
| Hoàn | B | Recursive, chunk_size=500 | 3/5 | Giữ được đoạn dài liền mạch | Tài liệu dài nhất lấn át câu hỏi khác |
| **Cường** | **C** | **Sentence, max=3** | **4/5** | **Giữ trọn câu chứa số liệu, cân bằng độ dài** | Danh sách đánh số có thể tách khỏi câu dẫn |
| Trang | D | FixedSize, chunk_size=500, overlap=50 | 3/5 | Đơn giản, có overlap chống mất ngữ cảnh biên | Cắt cứng theo ký tự, không theo ranh giới ngữ nghĩa |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> `SentenceChunker(max_sentences_per_chunk=3)` cho kết quả tốt nhất (4/5) vì các tài liệu nguồn là văn bản hành chính/thông tin ngắn, mỗi câu thường mang trọn 1 sự kiện hoặc con số (vd. "Hạn mức vay: tối đa 10 triệu đồng/sinh viên..."), nên chia theo câu tránh được việc cắt đứt một con số khỏi ngữ cảnh giải thích nó — điều mà `FixedSizeChunker`/`RecursiveChunker` với chunk_size cố định dễ mắc phải trên văn bản ngắn.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | ĐHQGHN hiện đang đào tạo bao nhiêu chương trình đại học, thạc sĩ và tiến sĩ? | 190 chương trình đại học, 198 chương trình thạc sĩ, 118 chương trình tiến sĩ | `vnu-gioi-thieu-chung` |
| 2 | Quỹ học bổng khuyến khích học tập được trích tối thiểu bao nhiêu % tổng thu học phí? | Tối thiểu 15% tổng thu học phí từ sinh viên | `vnu-quy-dinh-hoc-bong` |
| 3 | Sinh viên có thể vay tối đa bao nhiêu tiền từ chương trình vay vốn không lãi suất của Quỹ UOB? | Tối đa 10 triệu đồng/sinh viên, lãi suất 0%, trả nợ bắt đầu sau 6 tháng kể từ khi tốt nghiệp, hoàn tất trong 30 tháng | `vnu-ho-tro-vay-von` |
| 4 | Trường THPT chuyên Khoa học Tự nhiên có những chuyên ngành nào và tuyển bao nhiêu học sinh mỗi năm? | 5 chuyên ngành: Toán, Tin học, Vật lý, Hóa học, Sinh học; tuyển 540 học sinh/năm | `vnu-dao-tao-thcs-thpt` |
| 5 | *(metadata filter `category=student-support`)* ĐHQGHN có những chương trình hỗ trợ sinh viên nào về tài chính và việc làm? | Hỗ trợ tài chính qua vay vốn không lãi suất từ Quỹ UOB (tối đa 10 triệu đồng); hỗ trợ việc làm qua ngày hội tuyển dụng với Samsung, Toshiba, Lotte Group | `vnu-ho-tro-vay-von` + `vnu-tu-van-viec-lam` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).
> Kết quả đo với `EMBEDDING_PROVIDER=local`, chiến lược `SentenceChunker(max_sentences_per_chunk=3)` (Cường — Cấu hình C, tốt nhất, xem Phần 2).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Chương trình đào tạo | Sentence (max=3) | Có, top-1, score 0.658 | Đạt điểm 2/2 |
| 2 | % quỹ học bổng | Sentence (max=3) | Có, top-1/2/3 đều từ đúng doc, score 0.795 | Đạt điểm 2/2 |
| 3 | Hạn mức vay UOB | Sentence (max=3) | Có, top-1, score 0.752 | Đạt điểm 2/2 |
| 4 | Chuyên ngành THPT KHTN | Sentence (max=3) | Có, top-1, score 0.653 | Đạt điểm 2/2 |
| 5 | Hỗ trợ tài chính + việc làm (filter) | Sentence (max=3) + `metadata_filter={"category":"student-support"}` | Một phần — top-3 chỉ toàn chunk từ `vnu-ho-tro-vay-von`, chunk của `vnu-tu-van-viec-lam` (Samsung/Toshiba/Lotte) không lọt top-3 dù đã filter đúng category | 1/2 — đúng 1 trong 2 doc gold, thiếu vế "việc làm" |

**Điểm truy xuất tổng: 9/10 (Q1-4 đạt 2đ, Q5 đạt 1đ).**

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, ở câu 5: `search_with_filter(metadata_filter={"category": "student-support"})` loại bỏ đúng 3/5 tài liệu không liên quan (học bổng, giáo dục phổ thông, giới thiệu chung) trước khi tính similarity, giúp kết quả top-3 không còn lẫn tài liệu ngoài chủ đề "hỗ trợ sinh viên". Tuy nhiên trong 2 tài liệu còn lại sau filter, `vnu-ho-tro-vay-von` (nội dung số liệu cụ thể: 10 triệu, 0%, 30 tháng...) luôn thắng thế so với `vnu-tu-van-viec-lam` (nội dung tường thuật, ít số liệu) — cho thấy metadata filter thu hẹp đúng phạm vi nhưng không giải quyết được thiên lệch similarity giữa các chunk trong cùng phạm vi đó.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

### Phân tích lỗi (Failure Case)

**Câu hỏi thất bại lúc đầu:** Q1 ("ĐHQGHN hiện đang đào tạo bao nhiêu chương trình đại học, thạc sĩ và tiến sĩ?") ban đầu **thất bại ở cả 4 cấu hình chunking** khi nhóm gõ câu hỏi **không dấu** ("DHQGHN hien dang dao tao bao nhieu chuong trinh...") — top-1 luôn trả về sai tài liệu (`vnu-ho-tro-vay-von` hoặc `vnu-dao-tao-thcs-thpt`), tài liệu đúng (`vnu-gioi-thieu-chung`) thậm chí không lọt top-3 ở 2/4 cấu hình.

**Nguyên nhân:** model nhúng đa ngữ (`paraphrase-multilingual-MiniLM-L12-v2`) học biểu diễn tốt hơn nhiều với tiếng Việt có dấu; câu hỏi không dấu bị lệch embedding, khiến các chunk có nhiều số liệu/danh từ khác (ví dụ `vnu-dao-tao-thcs-thpt` với hàng loạt con số tuyển sinh) "trông giống" câu hỏi hơn tài liệu đúng.

**Khắc phục:** viết lại đúng 5 câu hỏi với dấu tiếng Việt đầy đủ — Q1 lập tức đạt top-1 đúng với score 0.658 (so với việc tài liệu đúng còn không vào nổi top-3 khi không dấu).

**Bài học:** không phải mọi lỗi retrieval đều do chunking/metadata — chất lượng và định dạng của chính câu truy vấn (không dấu, viết tắt, sai chính tả) có thể là nguyên nhân chính, và cần kiểm tra trước khi đổ lỗi cho chiến lược chunking.

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
- Với văn bản ngắn (~1000-1400 ký tự), `SentenceChunker` với `max_sentences_per_chunk` nhỏ (3) vượt trội hơn `FixedSizeChunker`/`RecursiveChunker` vì giữ trọn câu chứa số liệu — không cắt đứt "10 triệu đồng" khỏi câu giải thích nó.
- Tài liệu càng nhiều số liệu/danh từ riêng (`vnu-dao-tao-thcs-thpt`) càng dễ "lấn át" các câu hỏi không liên quan trong không gian embedding khi chunk quá lớn — nên theo dõi hiện tượng 1 tài liệu áp đảo top-k khi debug retrieval.
- Câu hỏi không dấu tiếng Việt làm giảm mạnh chất lượng truy xuất với embedder đa ngữ — cần chuẩn hoá input truy vấn (giữ dấu) trước khi coi retrieval là "thất bại".

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng 5 tài liệu nhưng 4 cấu hình chunking cho điểm retrieval khác nhau rõ rệt (3/5 → 4/5 câu đúng), và cùng 1 cấu hình chunking nhưng câu truy vấn có dấu/không dấu cũng tạo chênh lệch tương đương. Điều này cho thấy chất lượng RAG phụ thuộc đồng thời vào chiến lược chunking VÀ cách người dùng đặt câu hỏi — tối ưu một phía là chưa đủ.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Gán `audience` khác nhau cho từng tài liệu (hiện tất cả đều là `all`) để benchmark filter theo `audience` có ý nghĩa như K3_VARIANT gợi ý, thay vì phải dùng `category` để minh hoạ. Đồng thời bổ sung thêm 2-3 tài liệu về đăng ký học phần/học phí/thư viện (chủ đề gợi ý của K3) để bộ dữ liệu bao phủ đúng phạm vi dịch vụ đại học đầy đủ hơn, thay vì thiên về học bổng/hỗ trợ sinh viên như hiện tại.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
