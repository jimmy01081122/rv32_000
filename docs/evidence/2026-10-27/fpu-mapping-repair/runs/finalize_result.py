from pathlib import Path
import json,hashlib,datetime,re
root=Path.cwd();b=root/'build/experiments/fpu-mapping-v1'
def read(n):return json.loads((b/n).read_text())
q=read('gate-sim-v9/qualification.json')
assert q['state']=='finished' and q['passed'] and q['compile_returncode']==q['test_returncode']==0 and q['input_identities_unchanged']
g=q['test_result'];assert g['passed'] and g['cycles']==116737 and g['comparisons']==233474 and g['opcode_rounding_pairs']==2048 and g['negative_result_bit_control']
for n in ('repeat-comparison.json','unit-readback-review.json','shared-linked-v1/link-manifest.json','link-replay-review.json','state-cut-review.json','review-controls-v2/summary.json','shared-readback-v1/connectivity-review.json','preservation-review.json','old-archives-review.json','native-review.json'):
 assert read(n)['passed'],n
cec=read('mapping-cec-v2/result.json');assert all(r['returncode']==0 for r in cec) and cec[-1]['equivalent']
assert 'Networks are equivalent' in (b/'mapping-cec-v2/cec.log').read_text()
assert 'Networks are NOT EQUIVALENT' in (b/'mapping-cec-v2/negative-cec.log').read_text()
assert read('state-cut-negative-review.json')['passed'] is False
full=read('equivalence-shared-v1/proof-result.json');assert full['returncode']==2 and not full['pass_marker'] and 'timeout' in (b/'equivalence-shared-v1/prove.log').read_text()
rows=read('shared-readback-v1/connectivity-review.json')['records'];assert sum(r['readback_cells'] for r in rows)==525189
r=dict(status='MAPPING_REPAIR_VERIFIED; full RTL formal equivalence and physical qualification open',
 completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_parent='0798c75',
 source_scope='hash-identified experimental helpers; no clean-source CPU workload or PPA claim',
 rtl_changed=False,baseline_replaced=False,new_physical_qualification=False,
 mapping=dict(cells=25855,dffs=100,independent_standalone_runs=2,graph_sha256=read('repeat-comparison.json')['fingerprints'][0],linked_variants=['baseline','A','B']),
 native_completion_log_reviews=9,retained_cells_checked=525189,
 removed_unobservable_cells={x['variant']:len(x['missing']) for x in rows},
 abc_transition_equivalence=dict(passed=True,state_bits=100,negative_control_rejected=True,state_cut_review=True),
 gate_regression=g,review_negative_controls=4,state_cut_negative_rejected=True,
 full_rtl_formal=dict(status='UNPROVEN_TIMEOUT',strategy_limit_seconds=900,native_returncode=2),
 fp_zero_wire_ss_data_ps={},preserved_archive_indexed_files=read('old-archives-review.json')['indexed_files'],
 limitations=['No independent IEEE-754 or full ISA proof','No new global-route PPA or qualified CPU clock','Original B FF hold failure remains','No baseline replacement or performance-target achievement'])
for n in ('baseline','A','B'):
 text=(b/f'shared-readback-v1/{n}/fp_max.rpt').read_text()
 r['fp_zero_wire_ss_data_ps'][n]=float(re.search(r'^\s*([0-9.]+)\s+data arrival time$',text,re.M)[1])
(b/'result.json').write_text(json.dumps(r,indent=2)+'\n')
p=root/'docs/FPU_MAPPING_REPAIR.md';s=p.read_text();needle='| 完整 RTL → mapped 形式證明 |'
row=f"| RTL／閘級逐週期回歸 | {g['cycles']:,} cycles、{g['comparisons']:,} 次完整輸出比較通過；結果 bit 錯誤注入被拒絕 |\n"
assert needle in s and row not in s;s=s.replace(needle,row+needle)
needle='## 時序診斷\n'
paragraph=f'''閘級回歸採原 canonical RTL 與 Liberty function model 比較，包含 32,768 組
opcode／rounding 編碼與特殊運算元輸入、65,536 組隨機封包，另加入 stall、
flush、reset；共 {g['settled_phases']:,} 次固定 clock 下的輸出穩定性檢查。
所有 155 個 completion bits、valid、ready 均比對。編碼掃描含保留／非法值，
不把 2,048 組編碼當成 2,048 種合法 ISA 行為；NaN／Inf／subnormal 等輸入
也不代表已獨立驗證 IEEE-754 正確性。

早期測試曾在暫存器 commit 後、組合輸出尚未傳播時取樣而失敗，已修正
測試程式並保留原紀錄。最終建置停用 CXXRTL 強制內聯以縮短主機編譯時間，
只在生成模型的 eval 函式加上主機 O0 註記，輔助函式採 O2；移除此註記可
逐 byte 還原原生模型。runtime headers 不變，編譯選項、來源及執行檔 hashes 均封存。

'''
s=s.replace(needle,paragraph+needle);p.write_text(s)
print(json.dumps(r))
