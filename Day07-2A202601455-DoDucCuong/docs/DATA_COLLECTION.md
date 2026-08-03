# Hướng Dẫn Thu Thập (Crawl) và Chuẩn Hóa Dữ Liệu

Chủ đề Giai đoạn 2 **cố định theo lớp** (K3: dịch vụ / quy định đại học — xem `K3_VARIANT.md`). Nhóm thu thập dữ liệu **trong phạm vi chủ đề của lớp**. Mục tiêu là có một bộ tài liệu nhỏ, đáng tin cậy để so sánh retrieval — không phải crawl càng nhiều càng tốt.

## 1. Phạm vi dữ liệu cần nộp

- Bám chủ đề cố định của lớp và khoanh phạm vi rõ ràng (ví dụ K3: quy định đăng ký học phần, hướng dẫn thư viện, chính sách học bổng).
- Thu thập **5–10 tài liệu công khai** liên quan trực tiếp đến chủ đề; ưu tiên nguồn chính thức, có cấu trúc và ngày cập nhật.
- Mỗi tài liệu là một file `.md` hoặc `.txt` trong `data/<ten-chu-de>/`; ghi nguồn trong `data/<ten-chu-de>/sources.csv`.
- Không dùng dữ liệu cá nhân, thông tin đăng nhập, tài liệu nội bộ/không được phép chia sẻ, nội dung sau đăng nhập, hoặc nội dung có quyền sử dụng không rõ ràng.

## 2. Cách crawl/thu thập

1. Lập trước danh sách 5–10 URL và kiểm tra mỗi trang thực sự thuộc chủ đề đã chọn.
2. Đọc điều khoản sử dụng và `robots.txt`. Nếu website không cho crawl, đổi nguồn hoặc chỉ chép tay phần công khai được phép dùng.
3. Chỉ lấy nội dung công khai cần thiết; không đăng nhập, vượt CAPTCHA, né giới hạn truy cập, hay gọi API riêng tư.
4. Nếu dùng script: crawl chậm (ít nhất khoảng 1 giây giữa các request), đặt `User-Agent`, và không crawl toàn website. Với quy mô lab, copy/clean thủ công 5–10 trang là đủ.
5. Lưu URL gốc, ngày lấy dữ liệu và ngày hiệu lực/phiên bản (nếu có). Loại bỏ menu, quảng cáo, footer lặp lại và thông tin nhạy cảm trước khi lưu.
6. Đọc lại nội dung đã làm sạch; không tự thêm thông tin không có trong nguồn.

> Không bắt buộc nộp scraper. Chỉ nộp script nếu không làm lộ API key hay dữ liệu không được phép chia sẻ.

### Dùng crawler mẫu (tùy chọn)

Repo có sẵn `scripts/fetch_public_pages.py`. Sao chép `scripts/urls.example.csv`, điền các URL được phép dùng, rồi chạy:

```bash
cp scripts/urls.example.csv data/urls.csv
python3 scripts/fetch_public_pages.py data/urls.csv --output-dir data/<ten-chu-de>
```

Script chỉ lấy trang HTML/text công khai, kiểm tra `robots.txt`, chờ tối thiểu 1 giây giữa các request và tạo file `.md` cùng `sources.csv`. Không dùng nó cho nội dung cần đăng nhập, CAPTCHA, trang JavaScript động hoặc PDF; khi đó hãy chọn nguồn khác hay chuyển/clean thủ công.

## 3. Cấu trúc thư mục

```text
data/
└── <ten-chu-de>/
    ├── <tai-lieu-01>.md
    ├── <tai-lieu-02>.md
    └── sources.csv
```

Dùng tên file chữ thường, không dấu, nối bằng dấu gạch ngang; một file chỉ chứa một văn bản nguồn. Dùng UTF-8 và ưu tiên Markdown để giữ tiêu đề, danh sách, bảng. Không đưa PDF/HTML thô vào `data/`.

## 4. Format từng tài liệu `.md`

Mỗi file bắt đầu bằng YAML front matter, sau đó là nội dung đã làm sạch. Với K3, `doc_id`, `title`, `source_url`, `retrieved_at`, `document_version`, `audience` là bắt buộc.

```md
---
doc_id: library-renewal-policy
title: Quy định gia hạn tài liệu thư viện
source_url: https://example.edu/library/renewal
retrieved_at: 2026-08-02
document_version: "2026-08-01" # dùng "not-stated" nếu nguồn không nêu
audience: student               # student | faculty | staff | all
department: library
category: borrowing-policy
language: vi
---

# Quy định gia hạn tài liệu thư viện

Nội dung đã làm sạch từ nguồn. Giữ lại các điều kiện, ngoại lệ và thời hạn
cần thiết để trả lời benchmark query.
```

- `doc_id` duy nhất, ổn định, không dấu; nên trùng tên file.
- `source_url` là URL trang/văn bản gốc, không phải link tìm kiếm.
- `retrieved_at` dùng định dạng `YYYY-MM-DD`; `document_version` là phiên bản/ngày hiệu lực, hoặc `not-stated`.
- Ngoài `audience`, thêm ít nhất một trường hữu ích cho lọc như `department`, `category`, `language`, `semester`.
- Khi nạp vào `Document`, parse front matter vào `metadata` và chỉ dùng phần bên dưới làm `content`.

> **Đã cung cấp sẵn:** `build_knowledge_base()` trong `ingest.py` tự làm các bước này — parse front matter → `metadata`, chia chunk, gắn `doc_id` + metadata lên từng chunk, rồi nạp vào `EmbeddingStore`. Bạn chỉ cần tạo file `.md` đúng định dạng ở trên và chọn chunker.

## 5. File kiểm kê `sources.csv`

Mỗi file có đúng một dòng, dùng header sau:

```csv
doc_id,file_path,title,source_url,retrieved_at,document_version,license_or_permission
library-renewal-policy,data/chinh-sach-thu-vien/gia-han-the.md,Quy định gia hạn tài liệu thư viện,https://example.edu/library/renewal,2026-08-02,2026-08-01,public-page
```

`license_or_permission` ghi căn cứ sử dụng, ví dụ `public-page`, `CC-BY-4.0`, hoặc `team-owned`.

## 6. Checklist trước benchmark

- [ ] Có 5–10 file cùng một chủ đề, `doc_id` không trùng.
- [ ] Mỗi file có đủ metadata bắt buộc; `sources.csv` khớp một-một với file.
- [ ] URL là nguồn gốc, truy cập được, và dữ liệu không nhạy cảm.
- [ ] Có metadata đủ để dùng `search_with_filter()`.
- [ ] Cả 5 benchmark queries đều kiểm chứng được từ corpus.
