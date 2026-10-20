# LSU A 驗證與審查結果

2026-10-20。審查基準為 `38107c819dd5b0324885b47755ef338619bea024`。
本輪未發現 A 新增的 RTL 錯誤；找到並修正兩項自動審查漏檢，補足交接測試，
再對兩個操作點重做證據審查。原始效能、面積與時序結果不變，兩類 1.20×
目標仍未達。依使用者要求先完成驗證與審查，B 尚未開始，凍結基線不變。

[原始記錄、來源與雜湊](evidence/2026-10-20/lsu-a-review/README.md)獨立封存；
前一輪[完整量測與實體證據](evidence/2026-10-20/lsu-a-physical/README.md)保留原樣。

## 發現與處置

| 編號 | 重要性 | 實際發現 | 修正與證明 |
| --- | --- | --- | --- |
| R1 | 高 | 舊 reviewer 未檢查量測的 `simulator_sha256`、`build_summary_sha256`、`wrapper_sha256` 與實際建置證據是否匹配。只改其中一項為不匹配值，原 27 項仍可被回報通過 | 現須明確提供 build／functional qualification summaries；核對 clean start/end、來源、工具版本、兩種 binary、生成檔與 assert 模式、建置／功能 logs、四個 suite、量測命令及原始檔案。三個實際負向案例由舊版接受轉為新版拒收 |
| R2 | 中 | 舊 reviewer 只比較退休指令分類，未強制執行前輪另做的逐 PC 工作量檢查。同類兩個 PC 的退休次數一減一增，分類總數不變，舊版仍接受 | 將 `(PC, instruction, kind) → retired count` 的完整比較納入正式 gate，拒收重複鍵及不匹配工作量。實際修改副本的第四個負向案例由舊版接受轉為新版拒收 |
| R3 | 覆蓋補強 | 原單元交接測試以 word load 為主；缺少 subword metadata 交接、交接後立刻 flush、新請求 fault 與 marked-store 背壓的明確案例 | 新增 12 個 byte／halfword offset 與 signed／unsigned 案例及三個控制案例。基線、A 各 35 項全通過；原 RTL 不能符合 A 節拍的負向控制仍有效 |

R1／R2 是審查工具的漏檢，並非本輪找到 CPU 計算錯誤。原數據另外保留了
實際 build proof、binary 及逐 PC profiles，補強後能通過完整重新核對。
刻意改動的負向副本不是新的 CPU 量測；原始 summary、profile 與 build 證據均未改動。

實作見 [資格綁定](../scripts/experiment_provenance.py)、
[正式 reviewer](../scripts/review_cpu_experiment.py)、
[負向控制](../scripts/test_experiment_provenance.py)與
[LSU 單元測試](../verification/unit/test_lsu_overlap.cpp)。

## RTL 與整合路徑審查

- `rsp_buf_ack` 取決於已註冊 buffer 與 flush 條件，不依賴 request-ready。
  新的請求資格沒有引入此路徑上的 ready 組合迴路。
- 舊 buffer 有效時 `dmem_rsp_ready=0`；交接 edge 只消耗舊 completion 並
  記錄新 request，response handler 不會在同一 edge 蓋掉新 in-flight 身分。
  新 metadata 於後續 edge 接收回應，外部 outstanding 仍最多一筆。
- `flush_valid`、非 RUN 狀態及 faulting buffer 均阻止重疊請求。
  flush 後已接受的交易仍保持追蹤，遲到的成功／錯誤回應會被排空並抑制 completion。
- SQ marking 的原註冊節拍未變；store 仍在成功 response 後才 ack retirement，
  store fault 仍透過已註冊 exception 送往 ROB。此處未加入 B 的 marking bypass。
- core 的 load completion PRF 寫入與 ROB completion snoop 使用原獨立通道；
  A 沒有修改其接收介面。新增測試確認舊 completion 與新 request 的地址、
  大小、extension、INT／FP domain 及 tag 不會互相污染。

這些結論適用於已審查的 A 差異及測試條件，不等於完整 RTL 形式證明。

## 本輪實際驗證

| 檢查 | 結果 | 適用範圍 |
| --- | --- | --- |
| 乾淨來源定向回歸 | 18/18 | 同一已核對 normal binary；來源前後為乾淨 38107c8 |
| Spike commit 比對 | 18/18 | 定向程式；不是完整 27-workload Spike 重跑 |
| assertion-enabled LSU interface | 48/48 | ready 節流、精確 load／store access fault、redirect／ordering |
| 固定時間 controls | 58/58 | normal／assert 同 CPU 對照、較快 core 與錯誤參數拒收 |
| 有限 FMA 值／旗標 | 3,400/3,400 | 原 finite oracle 與取消誤差案例 |
| 擴充 LSU 單元 | baseline 35/35、A 35/35，負向 1/1 | Verilator 4.038、`--assert`；含原 20 項及新增 15 項 |
| 契約／審查控制 | 30/30 | 原 21 項加九項 build／qualification／command／work admission tests |
| 真實資料副本的舊／新 reviewer 對照 | 4/4 正確拒收 | 三個 provenance 不匹配及一個逐 PC 工作量不匹配 |
| 原完整量測重新審查 | 兩個點各 27/27、FP32 各 3,629 筆 | 重驗原 ELF、數值、profile／audit、命令、工作量、功能與實體資格 |

單元測試使用本輪擴充的 harness 並保留測試來源雜湊；完整 core 定向回歸
使用原已驗證的 normal／assert 執行檔。全部候選 RTL、simulator inputs、
physical policy hashes 仍符合事前 A manifest，沒有重新生成 CPU 實作或變更模擬器。

前輪基線 214、A 功能 438、A 實體 369 個索引檔案也重新核對通過。
實體部分是重新審查既有 native route／三 corner 原始報告，沒有再跑一次 place-and-route；
兩組效能是重新檢查完整 raw evidence，沒有再執行一次 27-workload 計時。

## 數據與決策狀態

| 操作點 | Embench19 GM | FP32 GM | 面積／基線 |
| --- | ---: | ---: | ---: |
| 100 MHz | 1.045830× | 1.078255× | 1.003674× |
| 101.01 MHz | 0.726601× | 0.700275× | 1.003674× |

標準元件面積 22,162.24152 µm²；實際 9.8 ns SS setup 失敗，9.9／10 ns
三 corner 通過。固定 10 ns 記憶體在 9.9 ns core 下需兩拍、19.8 ns 才可取樣，
該點退步的原因與原先一致。面積通過 ≤1.10×，兩類效能各 ≥1.20× 仍未達。

建議以 100 MHz 作 A 的操作點審查；是否保留 A、何時恢復 B 的獨立實驗，
留待共同結果審查。凍結基線沒有被 A 取代，也沒有開始 A+B。
完整 ACT4、特殊 FP／所有 rounding、完整 trap cause／tval 比對、27 項有序
退休 trace、實體重跑變異及 detailed-route 仍依 [STATUS](STATUS.md) 分開追蹤。

## 現行重現入口

`make check-experiment-contract` 執行 30 項控制。
在 pinned Verilator 4.038 環境，以新的 `--out build/...` 執行
`scripts/check_lsu_overlap.py`，可重跑 baseline／A 各 35 項。

正式 reviewer 現必須明確提供建置與功能資格證據，例如：

```bash
python3 scripts/review_cpu_experiment.py \
  --experiment experiments/lsu-a-v1/manifest.json \
  --build-summary build/experiments/lsu-a-v1/build-clean-v1/summary.json \
  --qualification-summary build/experiments/lsu-a-v1/review-v1/qualification-clean-v1/summary.json \
  --measurement build/experiments/lsu-a-v1/measurement-10000ps-v1 \
  --analysis build/experiments/lsu-a-v1/physical-14000ps-eco-clean-v1/boundary-v1 \
  --comparison-point common-clock \
  --out build/experiments/lsu-a-v1/replay-review-10000ps.json
```

另一點改用 `measurement-9900ps-v1`、`--comparison-point fastest` 及新的輸出檔名。
重播需按前輪封存還原原 binary、生成檔、build／qualification raw files 及 route ODB。
歷史 reviewer 快照及舊結果保留原版本；現行工具不再接受省略 build／qualification 的呼叫。
