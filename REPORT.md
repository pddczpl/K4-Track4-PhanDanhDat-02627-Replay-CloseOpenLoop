# REPORT — Lab Day 12

> Điền **bằng lời và số liệu của chính bạn** (lấy từ màn hình và từ `evidence/*.json`). Mỗi câu 4–8 dòng là đủ. Số không có trong bằng chứng của bạn sẽ bị trừ điểm. Báo cáo công khai trên GitHub; giảng viên đối chiếu với `evidence/` và với bài của các bạn khác.

| | |
|---|---|
| Họ và tên | `Phan Danh Đạt` |
| MSSV (đúng bằng `--student-id` bạn đã chạy) | `02627` |
| GitHub | `pddczpl` |
| Seed chia dữ liệu / seed mô hình (xem `evidence/closedloop.json`, mục `student`) | `split_seed: 3541 / model_seed: 9038` |
| Số seed huấn luyện bạn dùng (`--seeds`) | `5` |

## Kết quả cuối

Điền từ `evidence/closedloop.json`, `openloop.json`, `gate.json` (cho mỗi mô hình học, lấy **dải qua các seed**).

| Bộ điều khiển | L2 vòng hở (m) | Va chạm vòng kín trên log (%) | Quyết định cổng |
|---|---|---|---|
| constant-velocity | 1.280 | 21.89 | BLOCK |
| IDM | 1.561 | 0.03 | (baseline) |
| EgoMLP | 0.771 .. 0.777 | 19.91 .. 39.37 | BLOCK |
| PercMLP | 0.624 .. 0.635 | 0.80 .. 7.80 | BLOCK |
| PercMLP+ (sau khi sửa) | 0.796 .. 0.852 | 0.17 .. 0.28 | RELEASE |

## Câu 1 · Dữ liệu
Bước 0 bạn phát hiện những vấn đề gì ở dữ liệu? Vì sao không dùng cột `Acc_LV`, và bạn thay bằng gì? Bao nhiêu quỹ đạo bị loại vì trùng, và vì sao chia theo quỹ đạo?

Kiểm tra `data_audit.json` trên tập Argoverse 2 (992,679 dòng, 9,993 quỹ đạo thô), tôi phát hiện ba vấn đề nghiêm trọng:
1. Cột `Acc_LV` (gia tốc xe dẫn) có độ tương quan với đạo hàm vận tốc $dv/dt$ xấp xỉ bằng 0 (`acc_lead_column_corr_with_dv_dt` = 0.0454 ~ 0.05), hoàn toàn không khớp với thực tế vật lý; trong khi xe theo sau có tương quan chuẩn 0.9291. Do đó không thể dùng `Acc_LV` để nhận diện các pha phanh. Tôi thay thế bằng cách làm mượt vận tốc `Speed_LV` bằng bộ lọc trung bình trượt cửa sổ 5 bước rồi lấy vi phân trung tâm bằng `np.gradient` (`derive_lead`), tạo ra cột `a_lead` chuẩn xác.
2. Dữ liệu chứa 383 quỹ đạo trùng lặp hoàn toàn (`exact_duplicates_removed = 383`) ở các ID cách xa nhau, sau khi lọc còn 9,610 quỹ đạo sạch.
3. Nếu chia ngẫu nhiên theo khung hình (frame), các khung liên tiếp có tương quan chuỗi thời gian cực cao sẽ xuất hiện ở cả hai tập, dẫn đến rò rỉ dữ liệu (data leakage) nghiêm trọng. Việc chia theo quỹ đạo độc lập (disjoint trajectory split, train: 7,688 quỹ đạo ~ 167,370 cửa sổ; test: 2,883 quỹ đạo ~ 71,763 cửa sổ) bảo đảm mô hình được đánh giá khả năng tổng quát hóa trên các hành trình hoàn toàn mới.

## Câu 2 · Phát lại
Bản refactor float32 khác bit ở bao nhiêu đoạn, vượt dung sai ở bao nhiêu? Thay đổi AEB làm lệch bao nhiêu đoạn, và vì sao lệch ở đúng những khung đó (mở một đoạn ra xem)? Phát theo thời gian thật làm lộ ra điều gì mà phát nhanh nhất che đi?

Theo `replay.json` trên 600 đoạn phát lại:
- Bản refactor float32 khác bit ở toàn bộ 600/600 đoạn (`not_bit_identical = 600`), nhưng vượt dung sai ở đúng 0 đoạn (`differ_beyond_tol = 0`), độ lệch cực đại chỉ đạt 9.32e-05 m/s² (rất nhỏ so với `atol = 1e-3, rtol = 1e-3`). Điều này do phép cộng dấu phẩy động không có tính kết hợp (`(0.1+0.2)+0.3 = 0.6000000000000001` khác `0.1+(0.2+0.3) = 0.6`), tạo sai số làm tròn khi đổi thứ tự tính toán. Vì vậy, kiểm thử phát lại phải dùng dung sai kỹ thuật thay vì so sánh từng bit.
- Thay đổi quy tắc AEB (`aeb_ttc = 1.5`) làm lệch đúng 13/600 đoạn (các đoạn: 64, 168, 191, 225, 228, 230, 304, 317, 331, 398, 469, 494, 523, max diff = 1.98 m/s²). Mở các đoạn này thấy lệnh chỉ lệch ở các khung có cự ly gần và vận tốc áp sát cao khiến `TTC = gap / closing < 1.5 s`, khi đó AEB kích hoạt phanh khẩn cấp (`cmd = min(cmd, -6.0)`). Các khung còn lại có TTC an toàn thì lệnh hoàn toàn giữ nguyên như IDM gốc.
- Chế độ phát nhanh nhất (`fastest`) giả định xử lý tức thì nên che giấu toàn bộ vi phạm hạn định thời gian (0 trễ, 0 rớt trong 59,713 khung). Ngược lại, phát thời gian thực (`realtime`) bộc lộ 582 khung bị trễ hạn (late) và 575 khung bị rớt (dropped), làm 365/600 đoạn bị đổi lệnh với độ lệch lên tới 5.72 m/s² do hệ thống phải giữ lệnh cũ.

## Câu 3 · Kịch bản
Lưới của bạn (tốc độ cruise, giới hạn khoảng cách, số ô): bao nhiêu % ô **không ai tránh được**? Độ trễ phản ứng 0 → 0,6 s làm vùng đâm của IDM tăng bao nhiêu? Log có phủ vùng khó không? (dẫn giới hạn phanh mạnh nhất của người lái trong log, và phần lưới đòi hỏi hơn thế)

Từ `scenarios.json`:
- Lưới kịch bản cut-in của tôi có vận tốc cruise `v_ego = 14.0 m/s`, cự ly gap từ 2.76 m đến 59.31 m (60 mốc), chênh lệch vận tốc $dv$ từ 0.0 m/s đến 14.0 m/s (45 mốc), tổng cộng 2,700 ô kiểm thử.
- Vùng bất khả thi vật lý (`unavoidable`): Ở độ trễ 0.0 s, có 3.63% số ô (98/2,700 ô) là không thể tránh va chạm dù phanh tối đa $b_{max} = 9.0 m/s²$. Khi độ trễ phản ứng tăng lên 0.6 s, vùng bất khả thi tăng vọt lên 10.22% (276/2,700 ô), tức tăng thêm 6.59 điểm phần trăm (gấp gần 3 lần). Biên vật lý này cho thấy vùng va chạm của IDM tăng từ 3.63% lên 10.22% hoàn toàn do giới hạn vật lý và thời gian trễ, chứ diện tích quy trách nhiệm cho bộ điều khiển (`attributable_area`) của IDM luôn bằng 0.0%.
- Dữ liệu log không hề phủ các vùng khó: Người lái trong log phanh mạnh nhất (`human_brake_limit_p99.9`) chỉ là 3.62 m/s² (trung vị phanh là -2.53 m/s²), và chỉ có 614/9,610 quỹ đạo (6.39%) có sự kiện xe dẫn phanh. Trong khi đó, lưới kịch bản có tới 12.67% số ô đòi hỏi gia tốc phanh lớn hơn 3.62 m/s². Các dữ liệu log chỉ tập trung ở vùng $dv$ thấp và khoảng cách an toàn, hoàn toàn thiếu các tình huống cắt đầu hiểm hóc ở cự ly gần.

## Câu 4 · Vòng hở và vòng kín
Dán bảng L2 và tỷ lệ va chạm của bốn bộ điều khiển (kèm hạng ở mỗi cách chấm). Cặp nào đổi thứ tự? Vì sao IDM có L2 như vậy mà vẫn lái tốt? Vì sao EgoMLP có L2 tốt hơn constant-velocity mà vẫn đâm?

Bảng kết quả đối chiếu giữa vòng hở và vòng kín (từ `openloop.json` và `closedloop.json`):
| Bộ điều khiển | L2 vòng hở (m) | Hạng vòng hở | Tỷ lệ va chạm vòng kín (%) | Hạng vòng kín |
|---|---|---|---|---|
| PercMLP | 0.628 | 1 | 3.11% (worst seed: 7.80%) | 2 |
| EgoMLP | 0.773 | 2 | 30.60% (worst seed: 39.37%) | 4 |
| const-vel | 1.280 | 3 | 21.89% | 3 |
| IDM | 1.561 | 4 | 0.035% (1 / 2,883 quỹ đạo) | 1 |

Có 4 cặp bị đảo ngược thứ hạng: `(const-vel, IDM)`, `(const-vel, EgoMLP)`, `(IDM, EgoMLP)`, `(IDM, PercMLP)`.
- IDM có L2 vòng hở kém nhất (1.561 m) vì luật IDM không được tối ưu để khớp từng biến thiên vận tốc nhỏ của con người trong điều kiện bình thường. Nhưng trong vòng kín, IDM là bộ điều khiển phản hồi kín (closed-loop feedback) với thành phần $(s^*/gap)^2$ tăng cực mạnh khi cự ly thu hẹp, giúp xe luôn giữ khoảng cách an toàn (`median_min_gap = 9.23 m`) và chỉ va chạm đúng 1/2,883 quỹ đạo (0.035%).
- EgoMLP có L2 vòng hở tốt hơn const-vel (0.773 m so với 1.280 m) nhờ học được phân bố thay đổi vận tốc của chính mình. Tuy nhiên, EgoMLP hoàn toàn mù thông tin xe dẫn (không nhận `gap` và `v_lead`). Trong vòng hở, do xe dẫn trong log tự lái an toàn nên điểm số không bị lộ; nhưng khi tự lái vòng kín, hễ xe dẫn phanh gấp là EgoMLP không hề hay biết để giảm tốc, dẫn đến va chạm tới 30.60% (thậm chí lên tới 68.82% trên lát cắt phanh, tồi tệ hơn cả const-vel 21.89%).

## Câu 5 · Một lần chạy chưa đủ
EgoMLP dao động bao nhiêu giữa các seed? Khoảng tin cậy Wilson nói gì? Nếu bạn chỉ chạy đúng một seed thì có thể báo kết quả nào, và vì sao điều đó nguy hiểm?

Số liệu từ `closedloop.json` cho thấy:
- Tỷ lệ va chạm của EgoMLP dao động dữ dội qua 5 seed huấn luyện: [39.37%, 33.02%, 31.32%, 19.91%, 29.38%]. Độ chênh lệch giữa seed tốt nhất (19.91% ở seed 9041) và seed tồi nhất (39.37% ở seed 9038) lên tới 19.46 điểm phần trăm (gấp đôi nhau). Tương tự, PercMLP cũng dao động từ 0.80% (seed 9039) đến 7.80% (seed 9042), chênh nhau gần 10 lần (7.0 điểm phần trăm).
- Khoảng tin cậy Wilson 95% (n = 2,883) của EgoMLP:
  - Seed tốt nhất (9041): [18.49%, 21.41%].
  - Seed tồi nhất (9038): [37.60%, 41.17%].
  Hai khoảng tin cậy này hoàn toàn tách rời nhau (không hề chồng lấn, min của seed xấu nhất 37.60% lớn hơn nhiều max của seed tốt nhất 21.41%).
- Mức độ nguy hiểm: Nếu kỹ sư chỉ chạy đúng 1 seed duy nhất và tình cờ trúng seed 9041 của EgoMLP (19.91%) hay seed 9039 của PercMLP (0.80%), họ sẽ lầm tưởng rằng mô hình hoạt động ổn định và an toàn. Tuy nhiên, chỉ cần thay đổi seed ngẫu nhiên của trọng số khởi tạo, tỷ lệ đâm xe có thể vọt lên 39.37% hoặc 7.80%. Báo cáo kết quả dựa trên một lần chạy duy nhất là vô cùng nguy hiểm vì nó che đậy sự mất ổn định cố hữu (seed instability) của mô hình học sâu, tạo ra ảo tưởng an toàn giả tạo trước khi đưa ra thế giới thực.

## Câu 6 · Tác nhân phản ứng
Dán bảng "xe sau phát lại" và "xe sau phản ứng". `T` bạn hiệu chỉnh là bao nhiêu, xe sau chân thực đến mức nào so với xe không phản ứng? Vì sao IDM bị tính "va chạm giả" khi xe sau chỉ phát lại, và điều này làm đổi kết luận về bộ điều khiển ra sao?

Bảng so sánh tổng tỷ lệ va chạm trên lưới cut-in ở độ trễ phản ứng `t_react = 0.6 s` (từ `agents.json`):
| Bộ điều khiển | Xe sau phát lại (replay) | Xe sau phản ứng (reactive) | Tỷ lệ va chạm phía sau (replay / react) |
|---|---|---|---|
| const-vel | 80.63% | 80.63% | 0.0% / 0.0% |
| IDM | 80.85% | 10.22% | 70.63% / 0.0% |
| EgoMLP | 83.85% | 83.85% | 0.0% / 0.0% |
| PercMLP | 75.70% | 47.63% | 28.07% / 0.0% |

- Hiệu chỉnh xe sau: Thời khoảng cách tối ưu tìm được là `T = 1.4 s`, đạt khoảng cách Wasserstein-1 $W_1 = 0.3473$ so với phân bố thời khoảng cách của người lái thực tế (người lái có median headway 1.84 s). So với một tác nhân không bao giờ phản ứng ($W_1 = 0.8373$), xe sau IDM phản ứng chân thực hơn gấp 2.4 lần.
- Va chạm giả (fake rear collision): Khi xe sau chỉ phát lại vận tốc cố định trong log, nó hoàn toàn không biết xe thử nghiệm (ego) vừa phải phanh gấp để tránh xe cắt đầu. Vì IDM phản ứng phanh rất chuẩn xác phía trước, xe sau phát lại đã tông vào đuôi IDM trong 70.63% số kịch bản, làm tổng tỷ lệ va chạm của IDM bị đội lên 80.85% (ngang ngửa const-vel 80.63%). Khi thay bằng xe sau có phản ứng (`reactive`), va chạm đuôi triệt tiêu về 0.0%, và va chạm của IDM giảm xuống đúng 10.22% (bằng đúng ngưỡng bất khả thi vật lý phía trước).
- Thay đổi kết luận: Nếu không có tác nhân phản ứng, hệ thống kiểm thử sẽ tính "va chạm giả" và phạt oan những bộ điều khiển biết phanh an toàn phía trước, dẫn đến kết luận sai lầm rằng bộ điều khiển không biết phanh (const-vel) lại "an toàn phía sau" hơn IDM.

## Câu 7 · Cổng phát hành và sửa
Quy tắc nào chặn PercMLP và nguyên nhân gốc là gì (dẫn số)? Bạn sửa bằng gì và vì sao nó chữa đúng nguyên nhân? Sau khi qua cổng, PercMLP+ có **tốt hơn** IDM không? Nó có nên được phát hành không, và bạn đề xuất làm gì trước khi quyết định?

Từ `gate.json` và `fix.json`:
- PercMLP bị chặn bởi 5 quy tắc:
  1. `R2_closed_loop_logs`: va chạm worst seed 7.8% (upper 95%: 8.8%) vượt xa baseline IDM 0.0% + 1.0%.
  2. `R3_braking_slice`: va chạm trên lát cắt phanh 23.1% (upper 29.7%) vượt baseline IDM 0.0% + 5.0%.
  3. `R4_scenario_grid`: diện tích va chạm tránh được trên lưới cut-in là 37.4% vượt baseline 0.0% + 2.0%.
  4. `R5_seed_stability`: va chạm dao động 0.8% .. 7.8% qua 5 seed (chênh lệch 7.0 điểm, vượt ngưỡng 1.0 điểm).
  5. `R6_reactive_world`: va chạm trong môi trường phản ứng là 47.6% vượt baseline IDM 10.2% + 2.0%.
- Hai nguyên nhân gốc:
  - Sai số tích lũy / dịch chuyển phân bố (covariate shift): Khi tự lái vòng kín, sai số nhỏ tích tụ khiến xe rơi vào các trạng thái lạ mà tập huấn luyện hành vi con người chưa từng có, khiến mô hình không biết cách tự điều chỉnh về trạng thái an toàn (gây rớt R2, R3, R5).
  - Thiếu hụt kịch bản cắt đầu hiểm hóc (OOD scenarios): Log lái xe bình thường không có các tình huống xe khác cắt đầu sát nút ở tốc độ cao (gây rớt R4, R6).
- Phương pháp sửa: Thêm 20,000 kịch bản cut-in mô phỏng (`cutin_windows`) có nhãn từ IDM để bù đắp kịch bản OOD; kết hợp 2 vòng DAgger (`dagger_windows`) cho mô hình tự lái trên log huấn luyện, ghi nhận các trạng thái lệch và gán nhãn bằng dự báo 3 giây của IDM để dạy mô hình cách tự phục hồi sai số.
- Kết quả: PercMLP+ vượt qua TOÀN BỘ 7 quy tắc (RELEASE) với va chạm trên log chỉ còn 0.17%..0.28% (R2 pass, upper 0.5%), va chạm lát cắt phanh 0.5% (R3 pass, upper 3.0%), diện tích lưới cut-in giảm còn 0.2% (R4 pass), và ổn định giữa các seed ở mức 0.2%..0.3% (R5 pass).
- PercMLP+ có tốt hơn IDM không? KHÔNG thể nói PercMLP+ tốt hơn IDM. Bằng chứng chỉ chứng minh PercMLP+ "không kém hơn" (non-inferiority) IDM. PercMLP+ học hỏi từ chuyên gia IDM thông qua DAgger nên trần năng lực bị chặn bởi IDM. Đặc biệt ở tốc độ cruise mở rộng 20.0 m/s chưa từng huấn luyện, IDM đạt 0.0% va chạm tránh được trong khi PercMLP+ vẫn đâm 0.0..1.0%. Chưa nên phát hành thay thế IDM ngay; cần thử nghiệm thêm trong mô phỏng 3D đa làn có cảm biến nhiễu, chạy kiểm thử song song (shadow mode) trên xe thật hàng triệu km, và duy trì IDM làm bộ giám sát an toàn dự phòng (safety fallback).

## Câu 8 · Bài lab này không chứng minh được gì
Chọn **ít nhất ba** giới hạn quan trọng nhất đối với việc quyết định phát hành và giải thích vì sao mỗi cái làm kết luận của bạn kém chắc chắn. Điều gì cần làm tiếp để thu hẹp khoảng cách đến thế giới thật?

Để đánh giá tính an toàn thực tế trước quyết định phát hành, có ba giới hạn quan trọng nhất cần nhận thức rõ:
1. **Mô hình động học 1 chiều (1D dọc), bỏ qua động học ngang và chuyển làn (Lateral Dynamics & Steering):**
   Mô phỏng giả định thế giới chỉ có chuyển động dọc 1 chiều, coi xe như chất điểm với gia tốc bị cắt phẳng [-9.0, +3.0] m/s². Trong thực tế, xe di chuyển trong không gian 2D với động học lốp, góc lái, trượt ngang và tương tác chuyển làn. Việc vượt qua bài test 1D không bảo đảm xe sẽ an toàn khi vừa phải phanh vừa phải đánh lái tránh va chạm trên đường cong hoặc mặt đường trơn trượt có hệ số ma sát thấp.
2. **Thiếu hoàn toàn khối cảm biến và xử lý nhận thức thực tế (No Sensor & Perception Stack):**
   Mô hình trong lab nhận trực tiếp giá trị chân thực (ground truth khoảng cách và vận tốc) không có độ trễ nhận thức hay sai số cảm biến phức tạp. Trong thực tế, hệ thống Perception (Camera, LiDAR, Radar) luôn có độ trễ phát hiện (latency 50–100 ms), nhiễu đo khoảng cách, điểm mù, vật thể bị che khuất một phần (occlusion), và các hiện tượng nhận diện sai (false positive / ghost braking) do thời tiết xấu (mưa, sương mù, ngược sáng). Một mô hình hoạt động tốt với ground truth có thể bị mất ổn định nghiêm trọng trước dữ liệu cảm biến rung giật.
3. **Xe dẫn không tương tác và giả định môi trường mô phỏng đơn giản hóa (Non-interactive Lead & Synthetic Cut-in Assumptions):**
   Xe dẫn trong log và xe cắt đầu trong kịch bản mô phỏng chạy theo kịch bản dựng sẵn mà không hề có phản xạ tương tác lại với hành vi của xe thử nghiệm. Thế giới giao thông thực tế là một trò chơi tương tác đa tác nhân (multi-agent dynamic interaction), nơi các tài xế liên tục quan sát và điều chỉnh theo hành vi của nhau.
- Các bước tiếp theo để thu hẹp khoảng cách:
  - Tích hợp mô hình vào bộ mô phỏng 3D hoàn chỉnh (CARLA hoặc SVL) có mô phỏng động lực học xe nhiều bậc tự do và luồng cảm biến hình ảnh/point cloud thô.
  - Kiểm thử phần cứng trong vòng lặp (Hardware-in-the-Loop - HIL) trên ECU thực tế để kiểm tra khả năng đáp ứng hạn định thời gian thực.
  - Chạy thử nghiệm ngầm (Shadow Mode) trên đội xe thực tế để so sánh phản ứng của mạng nơ-ron với tài xế con người trong hàng triệu kilomet vận hành thực tế.
