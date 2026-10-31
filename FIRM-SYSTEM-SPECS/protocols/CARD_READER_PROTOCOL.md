版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# CARD–READER v2 拟议协议
现有 v1：01→1 字节版本，02→8 字节固定 ID，10+8 字节挑战→8 字节测试响应。无 CRC、序号、请求超时恢复帧界定；未知命令静默。v2 尚未写入 RTL，不与 v1 自动混用；由版本/载板配置明确选择。
v2 帧：A5 5A | version:u8=2 | flags:u8 (0 请求/1 响应) | sequence:u16BE | command:u8 | payload_length:u16BE (0..128) | payload | CRC:u16BE。
CRC-16/CCITT-FALSE：poly=0x1021 init=FFFF refin=false refout=false xorout=0，覆盖 version 至 payload，不覆盖同步字；123456789→29B1。CRC 只防传输错误，不是认证。
命令：01 VERSION，02 IDENTITY（10 字节 ASCII UID + 器件公钥标识），10 PROVE（服务端挑战转交），11 PROOF_STATUS，20 STATUS，7F CANCEL。响应 payload 首字节状态：00 OK、01 VERSION、02 LENGTH、03 CRC、04 BUSY、05 TIMEOUT、06 NO_CARD、07 UNPROVISIONED、08 SECURE_DEVICE、09 UNSUPPORTED。后续字段长度必须在安全器件选型冻结后固定。
接收 FSM：SYNC→HEADER→BODY→CRC→DISPATCH→REPLY；长度超限或 CRC 错误不执行命令；帧间超时清缓冲并重新搜同步字。逐字节超时建议20ms，整帧100ms，安全操作500ms（须实测校准）。同序号同请求最多重试2次，缓存上一响应；同序号异请求拒绝；复位/拔卡清缓存。PROVE 重试不生成新服务器挑战。
参考 Python 编解码器及 stream_parser.py 已实现完整帧校验、逐字节解析、20ms字节超时和100ms整帧超时。RTL流式接收 FSM 仍未实现。联合 RTL 需补帧截断、CRC、重试、重复请求、拔卡和错误恢复测试。

## 0.2.1 接收恢复规则（Python参考已验证，RTL设计目标）
仅完整合法帧才输出给命令层。同步区允许连续A5后接5A；进入帧后同步字作为普通数据。版本、flags或长度非法时立即丢弃当前候选；CRC错误丢弃整个候选，不重放其内嵌帧。下一字节重新搜同步字。可能吞入后续合法帧的截断候选依靠超时和发送端重试恢复，不保证无间隔任意噪声流中的无损恢复。
时间使用单调毫秒，间隔或总时长达到阈值即超时；静默期间必须调用tick。拔卡/复位/UART framing error清缓冲；最大暂存138字节（最后CRC字节处理后立即清空），帧最大线上长度139字节。参考程序不包含认证、命令执行和重试去重缓存。
