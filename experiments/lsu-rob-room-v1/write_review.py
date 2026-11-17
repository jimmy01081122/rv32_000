#!/usr/bin/env python3
"""Render the complete admitted comparison; never overwrite an existing report."""
import datetime,json
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
BASE=ROOT/'build/experiments/lsu-rob-room-v1'
def main():
 p=json.loads((BASE/'functional-pipeline.json').read_text());d=json.loads((BASE/'parent-comparison.json').read_text());assert p['complete'] and d['passed']
 c=d['reviews']['candidate'];ab=d['reviews']['AB'];arb=d['reviews']['arb_v1'];r=d['relative_to']
 date=datetime.datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
 finished=datetime.datetime.fromisoformat(p['finished_utc']).astimezone(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M')
 out=ROOT/'docs/LSU_ROB_ROOM_REVIEW.md';assert not out.exists()
 text=f'''# ROB 空間限制仲裁：完整功能與 27 項比較

{date} 整理；實測與審查於 {finished} 完成（均為 Asia/Taipei）。
乾淨來源 `{p['start']['commit'][:7]}`；建置、資格、量測與兩次審查
五階段實際 exit 0，開始／結束來源相同。**完整功能與固定週期量測通過；新 PPA 尚未量測，原基線不變。**

## 實作及驗證

使用者於 2026-11-16（UTC）選擇 ROB 空間限制。在仲裁 v1 上只新增一個條件：
ROB 至少兩格可用（registered count ≤14）才允許首次 head store 讓 load 先走。
ROB 經 core 接線輸出一個 Boolean，沒有新增狀態。回壓中已送出的 load 保持選擇，
不受後來的空間變動影響；無 store 競爭的 load 仍可進展。
首次機會用完後，既有 SQ marked 位恢復 store 優先。沒有加入序號距離或 FP／PC 篩選。

- 父版與候選各 **344 pin-driven 案例**，使用實際 ROB 配置／完成／退休跨越門檻。
  包含原 140 案例、192 個壓力競爭組合，以及壓力變動、同時配置／退休及復原。
- **六個實際 RTL 負向控制**全數拒絕：父版冒充新策略、兩個邊界偏移、
  壓力升高撤回 held load、無限制優先、取消 held 選擇。
- clean normal／assert 模型；**18 directed、18 Spike、48 介面、58 記憶體、3,400 有限 FMA**通過。
- 完整 **27 項、3,629 筆數值**，ELF、memory audit、逐 PC 退休工作量與來源均核對。
  三個版本的 81 份互斥 profile 完整對帳；四個契約、九個 provenance 控制通過。
- 第一次單元產生因 adapter 檔名與 module 名稱不符而被 lint 拒絕。改由 checker
  複製到同名路徑後全套重跑；沒有關閉 lint，也沒有為此改動 CPU RTL，失敗資料保留。

時脈固定 10,000 ps；I response／I interval／D response 仍各 10,000 ps。
標準元件面積與 TT／SS／FF 時序需要新候選實測；下列是名義 100 MHz 的模擬時間比。

## 兩類完整分數

| 版本 | Embench19／原基線 | 平衡 FP32 八項／原基線 |
| --- | ---: | ---: |
| A+B | {ab['embench_time_geomean_speedup']:.6f}× | {ab['fp32_time_geomean_speedup']:.6f}× |
| 仲裁 v1 | {arb['embench_time_geomean_speedup']:.6f}× | {arb['fp32_time_geomean_speedup']:.6f}× |
| ROB 空間限制 | **{c['embench_time_geomean_speedup']:.6f}×** | **{c['fp32_time_geomean_speedup']:.6f}×** |
| 新候選／A+B | **{r['AB']['embench']:.6f}×** | **{r['AB']['fp32']:.6f}×** |
| 新候選／仲裁 v1 | **{r['arb_v1']['embench']:.6f}×** | **{r['arb_v1']['fp32']:.6f}×** |

相對 A+B，{r['AB']['faster']} 項改善、{r['AB']['slower']} 項退步、{r['AB']['equal']} 項相同；
相對仲裁 v1，{r['arb_v1']['faster']} 項改善、{r['arb_v1']['slower']} 項退步、{r['arb_v1']['equal']} 項相同。
FP32 相對 A+B 的 DSP 子群為 {r['AB']['fp32_subgroups']['dsp']:.6f}×，矩陣／ML 為
{r['AB']['fp32_subgroups']['matrix_ml']:.6f}×，兩子群各占 50%。兩類 ≥1.20× 的規劃目標仍未達。

## 全 27 項與個別取捨

PID 維持仲裁 v1 的 7,238 拍（相對 A+B 時間 −12.33%）；FFT 從 v1 的
34,851 降到 33,029 拍，相對 A+B 已改善 1.863%。statemate 從 2,805,791
降到 2,628,051 拍，相對 A+B 的退步由 7.325% 收斂到 **0.526%**，仍未完全消除。

相對仲裁 v1 的三個退步為 UD **+0.752%**、GEMM **+0.161%**、QRduino **+0.072%**；
這三項仍各自優於 A+B。相對 A+B 的最大退步為 statemate，其次 SLRE **+0.232%**。

| 工作負載 | A+B cycles | 仲裁 v1 cycles | ROB 空間限制 cycles | 相對 A+B 時間變化 |
| --- | ---: | ---: | ---: | ---: |
'''
 for x in d['records']:
  v=x['cycles'];text+=f"| {x['name']} | {v['AB']:,} | {v['arb_v1']:,} | {v['candidate']:,} | {x['time_change_percent']['AB']:+.4f}% |\n"
 text+='''
這是新 RTL 的實際執行結果；先前對既有軌跡套門檻所得的涵蓋率沒有被當作效能預測。
個別週期差額及等待分類保留於公開 `parent-comparison.json`；等待分類不是獨立可刪除的時間。

FFT 相對仲裁 v1 的 store-ack 等待少 2,090 拍，FP load 頭端等待多 268 拍，
合計淨少 1,822 拍。statemate 相對 A+B 仍多 86,418 拍 store-ack 等待，
由 load 頭端等待少 56,956 拍、其餘分類少 15,700 拍抵銷，最後仍多 13,762 拍。
這些是完整 profile 的等待位置對帳，沒有宣稱完成新候選的逐指令取消讀取生命週期診斷。

## 下一步與證據

建議保留這版作下一輪實體資格候選：兩類完整分數均優於 A+B 及仲裁 v1，
PID 收益保留，FFT 與 statemate 的主要退步收斂；同時保留上述個別取捨供審查。
下一步沿用既定
ASAP7、shared FPU、hold40、uniform ready guard 與 global-route 流程，重新檢查
TT／SS／FF 及面積；新 ROB→LSU 控制線位於記憶體選擇路徑，父版的 slack 不能套用。
目前 [critical paths](CRITICAL_PATHS.md)仍屬 A+B：SS 9.4 ns 的 INT EX0→dmem address
+8.20 ps、FPU→completion +59.46 ps；最小 FF hold +17.58 ps。

尚未升格基線、改變記憶體服務、調整權重、排除案例或放寬數值要求。
完整 ISA／IEEE-754、詳細繞線及功耗仍是另外的資格範圍。

'''
 text+=f'[實驗契約與重現方式](../experiments/lsu-rob-room-v1/README.md) · [完整證據](evidence/{date}/lsu-rob-room-functional/README.md)。\n'
 out.write_text(text)
if __name__=='__main__':main()
