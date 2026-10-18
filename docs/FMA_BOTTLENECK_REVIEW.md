# FMA 指令減少與 FIR／BiCG 等待分析

2026-10-18。使用者已核准 FP32 主設定採 `-ffp-contract=fast -fno-fast-math`；
`qualify_fp_balanced.py` 預設為 fast，off 留作敏感度對照。正式資料規模、容差、
計時／記憶體與實體契約仍待審查。本輪只增加主機端觀測，沒有更改 RTL。

## 指令究竟少在哪裡

對同一組八項工作負載重新做 off／fast 資格檢查，並針對 FIR、BiCG 分類
ROI 實際退休的指令。兩項的 load、store、分支與其他指令數均未改變；
減少量完全來自每組 `FMUL.S + FADD.S` 合併為一條 FMA。

| 核心／條件 | FMUL.S | FADD.S | FMA | 其他指令 | 總退休指令 |
| --- | ---: | ---: | ---: | ---: | ---: |
| FIR off | 8,192 | 8,192 | 0 | 52,945 | 69,329 |
| FIR fast | 0 | 0 | 8,192 | 52,945 | 61,137 |
| BiCG off | 3,192 | 3,192 | 0 | 13,316 | 19,700 |
| BiCG fast | 0 | 0 | 3,192 | 13,316 | 16,508 |

FIR 的 ROI 為 256 個樣本 × 32 taps＝8,192 次乘加。
BiCG 為 42×38 個內迴圈，每次各更新 `s[j]` 與 `q[i]`，共 3,192 次乘加。
這些是動態退休計數，沒有把錯誤路徑執行或靜態 opcode 數當成工作量。
固定 fixture、編譯命令、原始輸出與依 PC 的反組譯核對見
[封存](evidence/2026-10-18/fma-bottleneck/README.md)。

## 為何少指令卻只省少量週期

核心最多每週期退休一條指令，但並非每個週期都有指令可退休。
以兩個 `rdcycle` 的退休事件界定觀測區間，包含結束標記、排除開始標記。
這四次執行的觀測區間長度均與程式讀得的 CSR 週期差完全相同：

`ROI cycles = body 退休週期 + 1 個結束標記週期 + 未退休週期`

| 核心 | 少退休指令 | 新增未退休週期 | 淨省週期 | off／fast 加速比 |
| --- | ---: | ---: | ---: | ---: |
| FIR | 8,192 | 7,177 | 1,015 | 1.014× |
| BiCG | 3,192 | 3,066 | 126 | 1.005× |

這是同條件執行的完整週期對帳，不是把每條被刪除指令假定為一個可省週期。

### FIR：暴露 AP5B 載入回應級的等待

| 互斥的未退休分類 | off | fast | fast−off |
| --- | ---: | ---: | ---: |
| ROB 頭端浮點 load 尚未完成 | 1,797 | 9,481 | +7,684 |
| ROB 頭端 FADD 尚未完成 | 511 | 0 | −511 |
| 其他未退休週期 | 3,688 | 3,692 | +4 |
| 合計 | 5,996 | 13,173 | +7,177 |

再細分所有頭端 load 等待：

| load 所在階段 | off | fast | 差值 |
| --- | ---: | ---: | ---: |
| 尚未成為自身外部請求／forward 回應 | 516 | 518 | +2 |
| 自身外部交易仍在 flight | 515 | 516 | +1 |
| 自身資料已在 AP5B response buffer | 772 | 8,453 | +7,681 |

上表包含少量整數 load；其頭端等待總數兩組均為 6，新增量仍來自浮點 load。
`rsp_buf_valid` 時，`ld_cmp` 由暫存資料形成，ROB 的 `completed` 在下一個
上升緣才更新。因此「資料已在回應暫存」與「ROB 現在可退休」是不同狀態。
融合移除運算後，更多這類週期暴露在退休端；不能將它們直接解讀為外部 RAM 多花時間。
退休的 FP load 都是 16,671 條；實際外部請求含投機執行，不能假定兩組所有
匯流排交易都相同。FIR 的外部讀請求從 17,188 降為 16,933。

### BiCG：暴露 store 退休握手與資料路徑佔用

| 互斥的未退休分類 | off | fast | fast−off |
| --- | ---: | ---: | ---: |
| 已完成的 ROB 頭端 store 等待 `sq_retire_ack` | 3,394 | 6,460 | +3,066 |
| 其他未退休週期 | 958 | 958 | 0 |
| 合計 | 4,352 | 7,418 | +3,066 |

新增未退休週期全部落在 store ack 等待。細分這段握手：

| store 等待階段（互斥分類） | off | fast | 差值 |
| --- | ---: | ---: | ---: |
| 等待 SQ 的 retired 標記更新 | 1,676 | 1,676 | 0 |
| 請求已可送出、當拍被接受 | 1,676 | 1,676 | 0 |
| 仍有既有外部交易在 flight | 0 | 1,554 | +1,554 |
| 載入 response buffer 尚未清空 | 42 | 1,554 | +1,512 |

現行 [LSU](../rtl/lsu/rv32_ooo_lsu.sv)只能有一筆外部交易，且 `can_issue_store` 要求
`!in_flight_valid && !rsp_buf_valid`。ROB 頭端 store 完成後，先更新 SQ 的
`retired`，再送請求，直到回應到達才取得 ack。融合後 store 更早到達這個
握手位置，更多既有交易／回應級的等待暴露出來。
增加的 3,066 個週期全部在內迴圈更新 `s[j]` 的同一條 FSW 上；
該 FSW 的頭端等待從 3,234 增為 6,300。兩組外部讀／寫請求數均為
4,914／1,676，沒有增加記憶體操作量。

## 可以排除與尚不能推論的事

四個執行的 heavy FP 接受背壓、FP EX0 背壓及 heavy completion 背壓均為零。
FIR 的 FMA 第三來源單獨未就緒 entry-cycles 為零；BiCG 有第三來源等待，
但沒有造成 ROB 頭端 FMA 未完成的未退休週期。現有證據不支持將這兩項的
主要損失歸因於 FMA 單元吞吐不足。

FP IQ 缺來源、rename 阻塞、記憶體活動等是可同時發生的事件；
報告將其放在 `overlapping_events`，不能加到上述互斥週期表，也不能僅憑
一次佔用計數就宣稱擴大 queue 能取得多少加速。頭端分類是已觀察到的等待位置，
對特定結構改動的因果收益仍須做受控候選實驗。

## 證據與驗證邊界

來源 `5065e7f`，執行起迄工作樹乾淨。所有 RTL 與前輪 `581ee86` 一致。
[觀測器](../sim/tb/core_roi_profile.h)讀取固定 Verilator 4.038 模型的既有內部訊號，不驅動任何設計訊號。
它在上升緣前取樣，與上升緣後已註冊的 commit PC／指令／退休事件交叉核對；
FP IQ entry 的有效數、ready mask 與 ROB 所有權／PC／指令也逐週期核對。
四次觀測的 trace／packed-layout mismatch 均為零。

每次都用相同 ELF 做觀測開／關與加入觀測器前的舊模擬器重跑，
完整 stdout（包含全部輸出值、checksum、ROI／總週期及退休數）一致；
觀測開時僅多出既有 `FP ROI` 一行。加入核心觀測後的 stdout 也與同版本的
標準 paired qualification 逐 byte 相同。

新的完整 off／fast 各 8/8 主機、Spike、DUT 通過；預設 fast 的獨立日常入口
另有 8/8 通過，確認不傳 `--fp-contract` 時確實採用核准政策。
18 項 Python 控制測試、兩個 C++ profiler 檢查、3,400 個有限 FMA 精確案例、
定向與 Spike commit 比對各 18/18 通過。前輪完整 Embench 19/19 證據仍適用於
相同 RTL 的功能覆蓋範圍；本輪沒有重新執行完整 Embench。
這些不是新的 CPU 架構改善或 PPA 成績，尚無新面積、頻率或能耗數字。

## 下一項 CPU 方案的討論建議

將 **LSU 載入回應到完成／喚醒，以及 store 退休握手的重疊能力** 列為首輪設計
審查候選。AP5B response register 原先是為了切斷時序路徑，任何縮短等待的
方案都須同時檢查實體時序、標準元件面積、精確例外、順序與 flush／ownership。
本輪不更改該硬體或直接移除暫存級。

使用者核准後的[LSU 審查稿](LSU_OPTIMIZATION_REVIEW.md)已補上四個 Embench
代表與 FIR／BiCG 的三種延遲觀測，正常研究 18/18 通過；同時保留獨立 ready／store
error 探針的失敗。A／B／C 已列出具體範圍，須先關閉正確性缺口，再共同選實驗。
兩類各 ≥1.20×、面積 ≤1.10× 的目標與正式 AP5B 基線仍須在相同契約下驗收。

重跑：

```bash
make fetch-fp-sources
python3 -m unittest discover -s scripts -p 'test_fp*.py'
make profile-fp-bottlenecks JOBS=4  # 重跑 paired qualification 後觀測 FIR／BiCG
make qualify-fp-balanced-dut JOBS=4  # 已核准的 fast 預設入口
make test diff-test JOBS=4
python3 scripts/audit_fp_bottleneck_artifacts.py
```
