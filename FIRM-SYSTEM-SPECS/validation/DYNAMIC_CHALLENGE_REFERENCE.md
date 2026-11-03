# 动态挑战生命周期参考

版本：1.0 / 2026-11-02。状态：软件参考已测试，产品未集成。负责系统：服务器认证、安全器件接口。依赖：auth_transcript、proof_signature、cryptography50.0.0；验证标准：51项Python全回归通过，原RTL不变。

## 可执行接口

`ChallengeStore.issue(TrustedContext, trusted_eligible=True)` 使用 secrets.token_bytes 生成16B challenge ID与32B nonce，返回已校验的123B canonical transcript字段。TTL默认60秒，限制1..120秒，容量默认1024。UID始终保留10位前导零。TrustedContext必须由已验证Steam票据/所有权、账号与卡绑定及可信公钥注册表构造，不能从客户端任意布尔字段构造。binding_version每次解绑/换卡/重新绑定递增，即使其他字段相同也使旧挑战失效。

CARD/Reader未来仅传递服务器transcript及安全器件返回的64B低S P-256签名，不能自行替换nonce/expiry/account；服务器从存储恢复原transcript，以注册表公钥验签。外部安全器件须具有不可导出逐卡P-256密钥、可信公钥登记和锁定个性化流程；本模块无器件驱动、无私钥存储、无物理器件模型。不能将现有公开XOR/Rotate接入此验签作为登录证明。

`consume` 原子取出并销毁挑战后重新核对当前trusted context/eligibility/expiry，再验签。任何尝试消耗一次挑战，失败必须重新请求，限制爆破重试。16并发请求最多1个成功。恰在expires_at拒绝；时钟回拨清空全部挑战并拒绝。返回True只表示此参考验证成立，不签发会话、不断言Steam所有权已实际检查。

## 证据与残余风险

新增9项测试，合计51项通过；证据deliverables/challenge-store-tests.log。覆盖每个绑定字段、nonce轮换、跨挑战旧签名、吊销、错key、失败消耗、容量、碰撞、过期边界、时钟回拨与并发重放。签名使用临时软件密钥，绝非安全器件验证。

生产必须用跨worker共享持久化挑战存储和数据库原子状态转换，并在同一事务/锁顺序下复核绑定版本与吊销状态；本地锁无法防多个进程或数据库绑定更新并发。还需限流、审计、可信时间、重启语义、设备超时/断连与协议frame集成。未找到后端主仓库，不声称FastAPI/MySQL或Steam集成完成。物理测试DEFERRED_BY_USER；安全器件选型与驱动仍待实现。失败消耗策略存在认证请求DoS权衡，需认证会话绑定与限流弥补。
