版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# 审计证据
C0 main a6b79b461ca6d7393cf94d1c49c2527a2b5b13cd：test https://github.com/derrykervin/CardMCU_ASIC/actions/runs/37032191288 ，gds https://github.com/derrykervin/CardMCU_ASIC/actions/runs/37032191244 成功。
CARD main feaa55682afc13b8ef6917de1e913a06ffae8ec0：test https://github.com/derrykervin/FIRM_CARD_01_ASIC/actions/runs/40415324307 ，gds https://github.com/derrykervin/FIRM_CARD_01_ASIC/actions/runs/40415324245 成功。只属于该基线。
READER main 2e3a9cfb41424848e4da2e448f9378eef273d1d8：test https://github.com/derrykervin/FIRM_READER_01_ASIC/actions/runs/40415359419 成功；gds https://github.com/derrykervin/FIRM_READER_01_ASIC/actions/runs/40415359644 ：gds/GL/Precheck成功、viewer失败。viewer job 121898651286明确Pages HTTP404。
Pages修复需要仓库设置：Settings→Pages→Build and deployment→Source=GitHub Actions。当前工具没有Pages设置写入能力；未关闭Viewer。配置后重跑并核实部署；仅更改YAML不能证明404已解决。
本地没有iverilog/vvp/yosys，Docker socket拒绝、Git代理连接失败；新增RTL尚未仿真，不能用旧CI标记通过。

2026-10-30接续：本地Python参考测试17/17通过（日志/workspace/deliverables/python-tests.log），仅软件参考验证；远程HEAD未变，未新跑GitHub Actions或物理流程。

2026-10-31新增本地CVC补充RTL：40个正向场景通过，1个预期fatal控制识别；旧缺陷4类反向源码控制均失败。详见CVC_RTL_RESULTS.md。当前新增修复不能再统称“从未仿真”，但官方Icarus CI与新物理签核仍未执行。Python参考/运行器39项通过不替代物理流程。
