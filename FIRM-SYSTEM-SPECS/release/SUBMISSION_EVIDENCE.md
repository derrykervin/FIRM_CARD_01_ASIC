版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# 官方提交证据
C0：SUBMITTED（官方合并与当前项目收录已核实；不表示已制造/交付）。官方PR https://github.com/TinyTapeout/tinytapeout-sky-26d/pull/58 于2026-10-02T16:46:11Z合并，merge SHA55b75ab6e7d66eb99d1d36aaea9ee2d89520fbf0。项目 https://app.tinytapeout.com/projects/6057 。官方commit_id.json明确repo为derrykervin/CardMCU_ASIC、commit=a6b79b461ca6d7393cf94d1c49c2527a2b5b13cd、project_id=6057。当前官方HEAD 5b12186dac87496dfeaabcf9d9aa2460b399c58a 的projects/tt_um_derrykervin_cardmcu_c0目录包含OAS/LEF/网表和统计。只读归档，不重新上传C0。
CARD：项目ID、平台链接、Revision、官方收录记录未确认。NOT_SUBMITTED_VERIFIED（未取得提交证据，不推断一定未提交）。
READER：项目ID、平台链接、Revision、官方收录记录未确认。NOT_SUBMITTED_VERIFIED。
保留每次提交的官方URL、项目ID、时间、revision、commit、GDS/OAS SHA256、付款/授权状态及收录证据；只有官方证据齐全才标SUBMITTED。不得把GitHub提交等同平台提交。

2026-10-31检查官方未截断项目树，没有FIRM_CARD_01/FIRM_READER_01目录；公开PR搜索也未找到匹配记录。这只是当前可见范围内未取得证据，不排除私有/待处理平台项目。两颗正式设计状态保持“提交未确认”，不能借C0收录标记已交付。归档快照见C0_OFFICIAL_EVIDENCE.json及deliverables/c0-official/。
