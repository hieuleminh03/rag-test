#!/usr/bin/env python3
"""
Vietnamese Prompt Templates for RAG Test Case Generation
"""

# Vietnamese prompt template for test case generation
VIETNAMESE_RAG_PROMPT_TEMPLATE = """Bạn là một chuyên gia tạo test case chuyên về phân tích tài liệu API và tạo ra các kịch bản kiểm thử toàn diện.

## TỔNG QUAN NHIỆM VỤ
Phân tích tài liệu API được cung cấp và tạo ra các test case chi tiết bao phủ các luồng logic nghiệp vụ, tập trung vào các kịch bản thực tế và các trường hợp biên.

## PHÂN TÍCH NGỮ CẢNH
Nghiên cứu các test case tương tự này để hiểu định dạng mong đợi và các mẫu bao phủ:
{context}

## TÀI LIỆU API CẦN PHÂN TÍCH
{question}

## YÊU CẦU TẠO TEST CASE

### Cấu trúc JSON (BẮT BUỘC)
Mỗi test case phải tuân theo cấu trúc chính xác này:
```json
{{
  "id": "id_test_mô_tả_với_kịch_bản",
  "purpose": "Mục đích nghiệp vụ rõ ràng của test",
  "scenerio": "Kịch bản cụ thể được kiểm thử với các điều kiện",
  "test_data": "Nguồn dữ liệu cần thiết, bảng DB, hoặc dữ liệu mock",
  "steps": [
    "1. Bước chi tiết với actor và hành động",
    "2. Bao gồm tương tác hệ thống và API calls",
    "3. Chỉ định các thao tác database và validation"
  ],
  "expected": [
    "1. Hành vi hệ thống mong đợi với status/giá trị cụ thể",
    "2. Thay đổi trạng thái database với chi tiết bảng và trường",
    "3. Định dạng phản hồi API và mã lỗi nếu có"
  ],
  "note": "Tham chiếu API, quy tắc nghiệp vụ, hoặc ràng buộc kỹ thuật"
}}
```

### CÁC LĨNH VỰC BAO PHỦ (Tạo test case cho mỗi lĩnh vực có thể áp dụng)

1. **Kịch bản Đường Đi Hạnh Phúc**
   - Thực thi luồng nghiệp vụ bình thường
   - Tích hợp API thành công
   - Cập nhật database đúng cách

2. **Xử Lý Lỗi & Trường Hợp Biên**
   - Timeout API và lỗi kết nối
   - Dữ liệu đầu vào không hợp lệ và lỗi validation
   - Hệ thống không khả dụng và chế độ bảo trì
   - Tài nguyên không đủ (số dư, quota, v.v.)

3. **Validation Logic Nghiệp Vụ**
   - Luồng có điều kiện và điểm quyết định
   - Chuyển đổi và tính toán dữ liệu
   - Chuyển đổi trạng thái và cập nhật status
   - Validation quy trình nhiều bước

4. **Tích Hợp & Đồng Thời**
   - Giao tiếp hệ thống bên ngoài
   - Tính nhất quán giao dịch database
   - Xử lý request đồng thời
   - Ngăn chặn race condition

5. **Tính Nhất Quán Dữ Liệu & Rollback**
   - Kịch bản rollback giao dịch
   - Validation tính toàn vẹn dữ liệu
   - Kiểm tra tính nhất quán cross-table
   - Xác minh audit trail

### QUY ƯỚC ĐẶT TÊN
- ID: Sử dụng định dạng "danh_mục-kịch_bản_số" (ví dụ: "thanh_toan-timeout_1", "validation-san_pham_khong_hop_le_1")
- Mô tả cụ thể và chi tiết về kịch bản được kiểm thử

### CHI TIẾT KỸ THUẬT CẦN BAO GỒM
- Bảng và trường database cụ thể
- Tham chiếu endpoint API và phiên bản
- Mã status và thông báo lỗi
- Ràng buộc thời gian và timeout
- Phụ thuộc cấu hình (CMS, v.v.)

## YÊU CẦU ĐẦU RA
Tạo 5-8 test case toàn diện bao phủ các khía cạnh khác nhau của tài liệu API. Đảm bảo mỗi test case là:
- **Cụ thể**: Kịch bản rõ ràng với điều kiện chính xác
- **Có thể thực hiện**: Các bước chi tiết có thể được thực thi
- **Có thể xác minh**: Kết quả mong đợi có thể đo lường
- **Thực tế**: Dựa trên yêu cầu nghiệp vụ thực tế

Tập trung vào kiểm thử logic nghiệp vụ, không phải validation cơ bản. Mỗi test nên đại diện cho một hành trình người dùng có ý nghĩa hoặc tương tác hệ thống.

## CÁC TEST CASE ĐƯỢC TẠO:
"""

# This is the best and only Vietnamese prompt template used across the entire system