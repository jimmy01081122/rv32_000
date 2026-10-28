# B v1 時序診斷與下一階段選項

2026-10-21。**B 的 FP 時序退步在合成後、布局前已存在；FF hold 則暴露
目前 TT 修補裕量的限制。** 這次完成診斷，沒有修改 CPU、實體流程或驗收門檻。
[B v1](LSU_B_REVIEW.md)仍無完整合格操作點，基線 `58a4159` 與 A 分支均不變。

## 已確認的證據

使用原 pinned ORFS／OpenROAD／ASAP7，唯讀載入三份原 routed ODB。
9 組 TT／SS／FF 的 setup、hold 均重現原值，差異小於 0.000001 ps。
另完成 3 組原 synthesis ODB 的 SS、zero-wire／ideal-clock 診斷，共 12 次獨立程序。
工具／平台 204 檔案在前後核對；534,342 個 synthesis cells 的 master、instance、
逐 pin 連線全數與原映射網表一致，並核對原 Yosys cell 總數。

基線、A、B 的 `rv32_ooo_fp_execute.sv` 未變；sv2v 後整個 FPU module
也逐 byte 相同，SHA-256 為
`769b647361eb5bce78fd58923e646c3da2b47016042bbc69984983d6a17805bb`。
因此並非這次 LSU 修改直接加入新的 FPU RTL。

| SS 最差 FP 暫存器間路徑 | 基線 | A | B |
| --- | ---: | ---: | ---: |
| 原 routed FP setup slack，10 ns，ps | +321.026 | +465.906 | −2,282.992 |
| 原 routed 資料延遲，ns | 9.609165 | 9.480563 | 12.214929 |
| 組合元件數，包含 buffer | 117 | 119 | 155 |
| 其中 buffer | 12 | 13 | 18 |
| 非 buffer 元件 | 105 | 106 | 137 |
| synthesis zero-wire／ideal-clock 資料延遲，ns | 6.518351 | 6.651498 | 8.455249 |

表中 routed 資料延遲從 launch clock pin 後起算，包含 clock-to-Q、
組合 cell arc 與資料 wire delay，不包含 launch clock tree 延遲。
這是 FP 路徑組的比較；基線與 A 的**全核心**最差 SS setup 仍分別為
+30.871 ps、+150.687 ps，位於 LSU／外部地址輸出路徑。

B 的 routed 關鍵 FP 路徑為 `fp_ex0_req_q[89]` → `u_fp_execute.cmp_data[115]`，
137 個非 buffer 元件全都已存在於原 synthesis 網表。
在原 synthesis 網表中，同一 completion bit 115 的結構最長深度也從
基線 145、A 146 增為 B 187 個組合元件。結構最長深度按所有 fan-in 計算，
與 STA 選出的最長時間路徑不同，不可混用。

為排除「只因比較不同輸出 bit」的疑慮，同一 completion bit 115 的
zero-wire 資料延遲為基線 6.445652 ns、A 6.598766 ns、B 8.417514 ns；
B 比基線多 **1.971862 ns**。最差 FP 路徑比較則多 **1.936898 ns**。
兩者都在布局前出現差距。

原 routed 最差 FP 路徑的 cell arc 總和為基線 9.193979 ns、B 11.732453 ns，
資料 wire delay 為 0.276944 ns、0.351755 ns；B 的 clock skew 約 −14.523 ps，
基線約 −9.241 ps。這些數據不支持把整個退步歸因於 wire 或 clock skew。
但 cell arc 仍含實際負載與 slew 影響，不能把其差值全稱為純邏輯映射的因果貢獻；
也不能將不同視圖的最差路徑差值直接相減，當成布局的獨立貢獻。

目前流程對全核心 flatten、最佳化及 ABC mapping；LSU 修改後，未改 RTL 的
FPU 仍產生不同映射。證據已定位到**合成映射敏感性加上實體負載效應**，
尚未隔離是哪個最佳化 pass 或排序造成，也未做同來源重跑的變異研究。
不據此宣稱 ABC 功能錯誤、特定 FMA opcode 是唯一根因，或 B 架構必然慢 2.28 ns。

## FF hold 是另一個問題

相同 `dmem_req_ready` → `u_lsu.in_flight_is_store` 路徑：

| 原 routed corner，10 ns | Hold slack，ps |
| --- | ---: |
| SS | +146.679886 |
| TT | +52.584854 |
| FF | −0.332734 |

FF 共兩個違反端點：`in_flight_is_store` −0.332734 ps、`in_flight_sq_idx[1]`
−0.298511 ps。前者經過 23 個 buffer 與 1 個 AO32；實際資料到達
316.574860 ps，需求為 316.907593 ps。
TT 路徑有 52.585 ps 正裕量，仍不足以保障 FF。這說明目前 TT-only 建置、
50 ps hold 修補目標對這版 B 不夠保守；不是延長 clock period 就會消失的問題。
維持原三 corner 的零負 slack 門檻，不以四捨五入放行。
額外 buffer 或提高 TT 修補目標是否能完整解決，尚未實測。

## 建議的選擇

**建議先建立下一版可比實體流程，再選下一項 CPU 架構實驗。**
此為診斷當時的建議。使用者後續核准先進行 [FPU 映射修復](FPU_MAPPING_REPAIR.md)，
現已完成共同映射與映射層驗證；完整 RTL 形式證明、hold 校準及新流程實體資格
仍開放，沒有修改目前基線。

| 選項 | 具體工作與驗收 | 取捨 |
| --- | --- | --- |
| 先穩定實體比較流程（建議） | 隔離並核對未改 FPU 的映射邊界／連線與功能等價，評估同一 FPU 映射是否能一致套用；維持 TT-only 建置，以獨立 SS／FF 檢查校準較保守的 TT hold 修補裕量；新 flow 版本對基線、A、B 全部重建 | 先改善架構比較的可信度；需重新固定物理參考，原 v1 資料繼續保存，不能混合評分 |
| 先規劃 FP 算術架構實驗 | 保留 A 作參考，依完整工作負載等待／相依性挑選 FP 正規化、捨入或 pipeline 的單一改動；先共同決定 latency／吞吐／面積取捨，另立實驗契約 | 更直接對準 FP32 目標，但仍需處理映射敏感性，且 pipeline 對相依鏈可能有代價 |

單獨修 B 的 hold 仍留下 100 MHz 的 SS setup 缺口。
即使恢復 B 的 100 MHz 實體資格，目前同頻 cycle 資料也僅為
Embench 1.029459×／FP32 1.009599×，仍未達兩類各 1.20×。
因此不建議把「救回這版 B」當成目前唯一優先項目，也不直接將 A、B 收益相加。
任何新操作點仍須實測完整 27 項，維持記憶體固定 10 ns 及面積 ≤1.10×。

[原始診斷、重播與查核結果](evidence/2026-10-21/lsu-b-timing-diagnosis/README.md)
另行封存；原基線／A／B 五份 archive 的 2,060 個索引檔案重新驗證通過。
zero-wire／ideal-clock 的正 slack 只作診斷，不是可用頻率或新 PPA 成績。
