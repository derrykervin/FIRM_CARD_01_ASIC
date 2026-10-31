版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# 流片检查表
截止目标 2026-11-30；SKY26d 官方截止本轮未取得独立平台证据。
两颗分别记录：RTL 冻结、功能和联合仿真、覆盖率、Lint、综合、40MHz STA、P&R、GDS/OAS、DRC/LVS/Precheck、GL、引脚/文档、必需 CI、平台项目、Revision、收录证据。
审计时旧版 CARD test/GDS 成功，旧版 READER test/GDS 子任务/GL/Precheck 成功但 Viewer 失败。没有本次修改签核；没有逐项 STA/DRC/LVS 报告解析。
FPGA 未执行：没有实体开发板、接线和实验访问；这是独立质量关卡。
SUBMITTED 仅凭官方项目/Revision/收录记录；仅技术检查通过为 VALIDATED_NOT_SUBMITTED。当前产品整体状态 AUDIT_IN_PROGRESS / NOT_PRODUCT_VALIDATED。

2026-10-31用户决定：FPGA和其它实物硬件测试暂缓，状态DEFERRED_BY_USER；不作为当前工作阻塞，也不标已验证。继续强化RTL联合/异常回归和软件安全验证。正式流片物理签核项目不随之免除；电气、机械、真实安全芯片抗攻击等风险仍保留。
