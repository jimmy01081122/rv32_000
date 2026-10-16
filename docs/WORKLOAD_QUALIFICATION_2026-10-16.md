# 工作負載初步資格檢查 — 2026-10-16

結論：完整 Embench 的首要阻礙是交叉工具鏈的函式庫相容性。
PolyBench 四項 FP32 候選的小資料集具備繼續移植的條件，但尚無 DUT 結果或
有效效能成績。本紀錄不凍結 ABI、工作負載或改善門檻。

## 範圍與環境

- 專案基準：文件清理提交 `4fa3a589da5a162229544a3422740e9b033eaedc`；
  診斷腳本隨本紀錄加入，沒有 CPU 功能修改。
- 映像：`rv32ooo-sim:g1`，ID
  `sha256:0d80d39df2f24dc60a77387242f781edc1cc67f53865719981e01b5b5a989d26`。
- 交叉 GCC：16.1.0；主機 GCC：Ubuntu 11.4.0。
- Embench：`0466a18e4f6b47e19598d7c6ba72916d54b68f65`，上游原始碼未改動。
- 原始命令、錯誤與主機結果位於忽略版本控制的 `build/qualification/`。
  下列命令可重建診斷，不需要修改既有 benchmark runner。

## Embench 缺少的五項

[診斷腳本](../scripts/qualify_embench_candidates.py)使用 `-O3`、
`CPU_MHZ=1`、`WARMUP_HEAT=1`；主機版本使用上游 native board 和原本的
`main`／`verify_benchmark`。交叉建置使用專案的啟動碼、1 MiB linker script
及 board support，測試三種設定：

1. `legacy-im`：`rv32im_zicsr / ilp32`，與既有 runner 相同的 `-lgcc`。
2. `imf-ilp32f`：`rv32imf_zicsr / ilp32f`，`-lgcc`。
3. `imf-ilp32f-libm`：相同 F 設定，另外以連結群組加入 `libm/libc/libgcc`。

| 項目 | 主機上游自我檢查 | IM 連結 | IMF 連結 | IMF 加函式庫連結 |
| --- | --- | --- | --- | --- |
| cubic | PASS | FAIL | FAIL | FAIL |
| minver | PASS | FAIL | FAIL | FAIL |
| nbody | PASS | FAIL | FAIL | FAIL |
| st | PASS | FAIL | FAIL | FAIL |
| wikisort | PASS | FAIL | FAIL | FAIL |

這是 5 次主機建置／執行成功、15 次目標連結失敗；未執行這五項的 Spike 或 DUT。
主機 PASS 是可用的來源檢查，不代表 RV32 數值行為已驗證。

實際阻礙：

- `gcc -print-multi-lib` 只有 `.;`，預設為 `rv32imafdc... / ilp32d`。
  `libm.a` 的 RISC-V attributes 同樣含 A/D/C 等擴充。
- 連結時出現 `can't link double-float modules with single-float modules`，
  或與 soft-float modules 的衝突；另缺少 `__adddf3`、`__muldf3` 等支援函式。
- 即使主要使用 float 的 `minver`，驗證部分仍需要 `__extendsfdf2`、
  `__ltdf2`、`__adddf3`、`__truncdfsf2`。不能因核心支援 F 就假設不需軟體 double。
- 既有整數程式可以因未拉入不相容的 archive 成員而成功；這不足以證明
  目前預建工具鏈適用完整 Embench。

從 repo 根目錄重現：

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$(pwd):/workspace" -w /workspace rv32ooo-sim:g1 \
  -c 'python3 scripts/qualify_embench_candidates.py'
```

本次腳本預期退出碼為 **1**，表示仍有失敗的診斷項目；詳細命令與結果在
`build/qualification/embench/summary.json`。腳本不把失敗項目移出集合，
也不產生部分通過的效能總分。這些 profile 是探測設定，尚未選定正式 ABI。

## PolyBench/C FP32 候選

來源為[官方 4.2.1-beta 封存檔](https://sourceforge.net/projects/polybench/files/polybench-c-4.2.1-beta.tar.gz/download)，
SHA-256：`426519ee8443a5f2175de6a3e9328cda8917a5e33053d0e8f59855ab56d689a4`。
只下載至 `build/qualification/`；尚未加入 vendor dependency。
封存檔保留其 `LICENSE.txt` 與來源標頭。

四項均支援 `DATA_TYPE_IS_FLOAT`。本次使用 `-O3 -ffp-contract=off`、
`POLYBENCH_DUMP_ARRAYS`，各自測試 `MINI_DATASET` 與 `SMALL_DATASET`。
此處關閉乘加融合是探測條件，正式融合規則仍待討論。

| 核心 | MINI 尺寸 | SMALL 尺寸 | MINI / SMALL 陣列尖峰位元組 |
| --- | --- | --- | --- |
| gemm | NI/NJ/NK = 20/25/30 | 60/70/80 | 7,400 / 58,400 |
| bicg | M/N = 38/42 | 116/124 | 7,024 / 59,456 |
| jacobi-2d | N=30，TSTEPS=20 | N=90，TSTEPS=40 | 7,200 / 64,800 |
| cholesky | N=40 | N=120 | 12,800 / 115,200 |

數字依 FP32 陣列宣告計算；cholesky 包含初始化的第二個矩陣。
不含 ELF、stack、配置器對齊與函式庫。SMALL 的陣列容量適合繼續評估現有
1 MiB RAM；MEDIUM cholesky 的兩個矩陣已需 1,280,000 bytes，超過此容量。

本次證據：

- 8 個主機版本均建置／退出成功，產生預期數量的輸出值且未見 NaN/Inf。
  **尚未與獨立數值參考比較**，不能列為正確性驗收。
- 8 個 RV32IMF/ilp32f 來源 object 均編譯成功；尚未連結成裸機 ELF。
  檢查 MINI 反組譯可見單精度運算；cholesky 有 `fsqrt.s`、`fdiv.s`，
  並有 `frflags/fsflags` 與 `sqrtf` 依賴。
- 輸出目前只保留小數兩位，不能直接當 FP32 容差檢查的 golden data。
  `fprintf` 的 float 提升還帶入 `__extendsfdf2`；裸機輸出需另做完整精度檢查。
- 上游 harness 使用 `posix_memalign`、stdio，計時選項含 `gettimeofday` 或
  x86 `RDTSC`。啟用預設計時準備還會沖刷 32,770 KiB cache，超過目標 RAM。
  本次只開啟 dump，未啟用該計時流程。裸機 port 必須明訂配置器、ROI 與快取條件。

主機建置範例，在上述映像內從 repo 根目錄執行：

```bash
pb=build/qualification/polybench-c-4.2.1-beta
src=$pb/linear-algebra/blas/gemm
gcc -O3 -ffp-contract=off -DDATA_TYPE_IS_FLOAT -DMINI_DATASET \
  -DPOLYBENCH_DUMP_ARRAYS -I"$pb/utilities" -I"$src" \
  "$pb/utilities/polybench.c" "$src/gemm.c" -lm \
  -o build/qualification/gemm-mini
build/qualification/gemm-mini
```

其他來源目錄為 `linear-algebra/kernels/bicg`、`stencils/jacobi-2d`、
`linear-algebra/solvers/cholesky`。更換核心名稱或改為 `SMALL_DATASET`
可重建其餘探測。交叉 object 探測改用 `riscv32-unknown-elf-gcc`、
`-march=rv32imf_zicsr -mabi=ilp32f`，只以 `-c` 編譯核心來源；不連結 harness。

## 下一步建議

1. 建立並固定符合 RV32IMF／選定 ABI 的 libc/libm/libgcc，保留可重現來源與版本；
   檢查支援軟體 double/long double，避免輸出 A/C/D 指令。
2. 在相容工具鏈下重做完整 Embench 建置，完成 Spike／DUT 結果與成本檢查。
3. 為四個 PolyBench 核心加入可審閱的裸機 harness、完整精度輸出、數值參考與 ROI；
   MINI 供日常回歸、SMALL 供固定驗收是目前可行的候選。
4. 共同檢視代表性與量測契約，再凍結雙集合及數字目標；此之前不依據舊 AP5A
   成績選定 CPU 結構優化。
