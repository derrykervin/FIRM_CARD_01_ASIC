版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# FIRM 跨系统规格与接续入口
本目录位于 CARD 现有仓库内；没有新建远程规范仓库。0.2 是拟议产品协议，不表示原型已经升级。Python 参考实现已可运行，RTL 仍为 C1 v1 原型。
优先顺序：安全器件与接口冻结 → CARD/READER 功能闭环 → 联合回归 → 物理验收 → 平台 Revision。
运行：`python3 -m unittest discover -s FIRM-SYSTEM-SPECS/validation -p 'test_*.py' -v`。
CARD：`bash tools/check.sh`；READER：在其仓库执行 `bash tools/check.sh ../FIRM_CARD_01_ASIC`。
所有当前快照为 API 下载基线，本地 Git 历史不是 upstream 历史。补丁应用到指定 upstream SHA 的新分支，不要把本地快照分支直接推到 main。
