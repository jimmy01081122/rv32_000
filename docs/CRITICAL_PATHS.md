# 目前已驗證的 critical paths

2026-11-13（Asia/Taipei）。下表是**完成實體資格的 A+B 父版本**，CPU 來源 `3f079c1`、
原生實體來源 `f66e12b`、封存 `49122fb`。新的 LSU 仲裁實驗已獲核准，尚不能沿用這些數字
宣稱新 RTL 的時序。採 ASAP7、TT 建置、共用 FPU／hold40／ready guard、global-route 寄生估算。

## Setup：SS、9.4 ns

| 排序 | 起點 | 終點 | 類型 | Slack |
| --- | --- | --- | --- | ---: |
| 1 | `int_ex0_req_q[65]` | `dmem_req_addr[2]` | reg → output | **+8.20 ps** |
| 2 | 同上 | `dmem_req_addr[9]` | reg → output | +8.36 ps |
| 3 | 同上 | `dmem_req_addr[13]` | reg → output | +8.76 ps |
| 4 | 同上 | `dmem_req_addr[4]` | reg → output | +9.69 ps |
| 5 | 同上 | `dmem_req_addr[6]` | reg → output | +10.48 ps |
| 6 | `fp_ex0_req_q[62]` | `u_fp_execute/cmp_data[107]` | reg → reg | **+59.46 ps** |
| 7 | 同上 | `u_fp_execute/cmp_data[101]` | reg → reg | +82.12 ps |
| 8 | 同上 | `u_fp_execute/cmp_data[111]` | reg → reg | +83.10 ps |

第一組經過 INT EX0／LSU 到資料埠位址輸出；第二組是 FPU 算術到已註冊 completion。
表中省略 mapped flop 型別後綴，原始報告保留完整名稱。每個 path group 各抽樣五條，
表格是這些抽樣的排序，不宣稱列出全設計任意前八條，也未將匿名 gates 全部對回 RTL 算式。
這些 slack 包含實際 constraints、clock tree 與 I/O budget，不能直接視為純組合延遲。

| SS 各類最緊路徑（9.4 ns） | 起點 → 終點 | Slack |
| --- | --- | ---: |
| reg → output | INT EX0 → `dmem_req_addr[2]` | +8.20 ps |
| reg → reg | FP EX0 → FPU completion | +59.46 ps |
| input → output | `dmem_rsp_error` → `dmem_req_wdata[20]` | +4,430.70 ps |
| input → reg | `dmem_rsp_error` → `u_rob.entries[9][110]` | +5,317.92 ps |

## Corner 與 hold

| Corner | 9.4 ns 最小 setup | 最小 hold |
| --- | ---: | ---: |
| TT | +2,719.23 ps | +39.98 ps |
| SS | +8.20 ps | +71.31 ps |
| FF | +4,225.69 ps | **+17.58 ps** |

FF 最緊 hold 是 `u_rob.event_counter[26] → u_rob.commit_trace[304]`（reg → reg），
另一個較緊 I/O hold 是 `dmem_rsp_error → u_lsu.rsp_buf_error`，**+24.67 ps**。
Hold 的約束須獨立維持，不能只追 setup 或 MHz。

9.3 ns 已實測在 SS setup **−91.80 ps** 失敗；9.4 ns 是 100 ps 試驗網格中的最短合格點。
100 MHz／10 ns 的 SS setup 為 **+608.20 ps**。固定 10 ns 記憶體下，已測全集合以
100 MHz 較快，故新仲裁先在此比較週期數；這不免除候選的重新實體資格。

## 與 LSU 仲裁的關係

新實驗先給安全 load 一次 head-store 首次 marking 的機會，再恢復 store 優先；
回壓期間保留已選 load。它加入選擇邏輯的位置接近上述最緊 LSU 輸出路徑，
因此要同時看 PID／完整兩集合的週期結果與後續路徑變化，不能用父版本的餘裕替新 RTL 保證時序。

[A+B 完整報告](LSU_AB_REVIEW.md) · [既有原始證據](evidence/2026-11-13/lsu-ab-complete/README.md) ·
[新仲裁契約](../experiments/lsu-load-arb-v1/README.md)。
`report_parent_timing.py` 逐一核對封存與 collector hashes，重新整理三個 corner、兩個週期、
setup／hold 共 240 條抽樣路徑，並與獨立 closure 的最小 slack 對照。
