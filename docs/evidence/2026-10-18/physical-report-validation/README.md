# Global-route 報告工具資格確認

2026-10-18。四個標準元件的小電路，**不是 CPU 效能、面積或時序閉合結果**。
固定的 OpenROAD binary、ASAP7 RVT libraries 與先前
[加法器模型核對](../asap7-library-validation/README.md) 相同；不修改 PDK。

[`summary.json`](summary.json) 記錄 49／49 控制通過：

- 一個 FA、一個 HA、兩個 DFF 完成 placement、global route，並儲存資料庫。
- TT／SS／FF 在各自的新 process 重新載入資料庫與 global-route 寄生。
  元件數 4、暫存器數 2、macro 數 0、幾何面積 0.91854 µm²；這只核對面積 API。
- 每個 corner 實際套用 2,300／5,500 ps；四類路徑皆有報告，單位明列 ps，
  JSON 與文字的 setup／hold 數值在報告小數精度內一致。
- TT 的 2,300 ps setup 與各 corner 的 hold 都報出負 slack；沒有把流程成功
  當成時序通過。這個小電路刻意不執行 timing repair。
- 實際移除 A 的 clock-specific input delay 後，約束檢查會報出缺口；
  實際將輸出負載改為 10,000 fF 後，slew／capacitance 檢查報出違例。
- 未繞線資料庫，以及沒有加法器模型核對旗標的分析均被拒絕。

`development-failed-control/` 保留第一版反例控制失敗的紀錄：原本沒有指定
`-clock core_clk`，未移除該 clock 的 input delay。修正控制命令後另開 v2
輸出，未覆寫失敗結果。這些失敗不計入 49 項通過數。

`placement-api.log` 顯示此 pinned binary 沒有 placement 的 `-random_seed`，
但支援 global routing 的 seed。正式 runner 的 Make argv 明確使用
`GPL_RANDOM_SEED=`，GRT 保留 seed 1；重跑一致性仍待全核心另行確認。

重跑：

```bash
python3 scripts/audit_physical_reports.py --container ID --out build/physical-report-audit-fresh
(cd docs/evidence/2026-10-18/physical-report-validation && sha256sum -c SHA256SUMS)
```

`summary.json` 另記錄原始輸出 hashes；
完整核心分析仍須獨立核對約束涵蓋、所有 corner、電氣限制與繞線狀態。
