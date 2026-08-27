# 排障手册

出口异常时，按以下顺序排查。

## 第零步：跑门禁

先排除配置本身写错的可能 —— 大部分「规则没生效」是静默失效，不是玄学：

```bash
python3 scripts/verify.py          # 静态断言
python3 scripts/verify.py --live   # 追加 RULE-SET 可达性 + 实测解析
```

有 FAIL 先修 FAIL。WARN 是「出口不确定」，不一定是错，但值得看一眼。

## 第一步：确认当前模式

- 确认使用的是 **配置模式**，不是场景模式
- 确认加载的配置文件是 Mantaray 的（daily / strict / debug）
- 参考 [配置 vs 场景](config-vs-scene.md)

## 第二步：检查规则命中

1. 打开客户端最近请求列表
2. 找到异常请求
3. 查看命中规则名称和策略（DIRECT / PROXY）
4. 对照 [规则优先级](rule-priority.md) 确认是否符合预期

## 第三步：检查 DNS 解析

常见问题：DNS 解析结果导致 GeoIP 误判。

- 某海外域名被国内 DNS 解析到国内 CDN IP → GeoIP 判为 CN → 走了直连
- 解决：将该域名加入 `proxy_global.list` 或 `sensitive_services.list`（域名规则优先于 GeoIP）

更隐蔽的一类：**出口和解析源脱耦**。域名走 DIRECT 但被海外 DNS 解析，
或走 PROXY 却被本地 DNS 解析。这类问题靠 `nslookup` 看不出来，要看
`[Host]` 绑定和 `[Rule]` 出口是否配对 —— 见 [DNS 出口绑定](dns-pinning.md)。

`[Host]` 段有三个静默失效的坑（域名后多空格 / 通配不匹配裸域 / 顺序被抢先），
`verify.py` 全都有断言。

验证方法：
```bash
# 查看域名解析结果
nslookup example.com
dig example.com
```

## 第四步：检查出口 IP

验证当前出口是否符合预期：

- 直连出口检查：访问 `https://myip.ipip.net`
- 代理出口检查：访问 `https://api.ip.sb/ip` 或 `https://ifconfig.me`

如果两个地址返回的 IP 地理位置不一致，说明分流生效。如果都是同一个 IP，检查是否全走了代理或全走了直连。

## 第五步：检查 RULE-SET 是否加载成功

远程规则文件可能因网络问题加载失败：

1. 尝试在浏览器中直接访问规则 raw URL
2. 如果无法访问，可能是 `raw.githubusercontent.com` 被干扰
3. 临时方案：将规则文件内容复制到本地

## 第六步：检查节点状态

- 节点是否在线
- 节点是否切换了（自动选择 / 回退策略可能导致出口变化）
- 严格模式下建议使用固定单一节点

## 常见问题速查

| 问题 | 检查项 |
|------|--------|
| 国内站打不开 | DNS 解析是否正常；`direct_cn.list` 是否覆盖该域名 |
| 海外站打不开 | 节点是否可用；域名是否被 GeoIP 误判为 CN |
| 速度突然变慢 | 节点负载；DNS 解析延迟；是否切换了网络环境 |
| 某服务触发风控 | 检查出口 IP 是否变化；是否用了自动选择节点；参考[风控指南](risk-control-guidelines.md) |
| 规则好像没生效 | 确认是配置模式；确认 RULE-SET URL 可达；重新加载配置 |
| `[Host]` 改了没反应 | 域名和 `=` 之间有空格；被前面的通配抢先；跑 `verify.py` |
| 内网域名连不上 | 公网 DNS 是否还返回内网 IP；考虑上静态 Host（L0）|
| 更新配置后绑定丢了 | 改了 `configs/*.conf` 而不是 `dns/pinning.conf`，被 sync 覆盖 |

## 调试模式

如需更详细的排查，切换到 `configs/debug.conf`：

- 开启 IPv6（排查双栈问题）
- 开启 DNS fallback（对比系统 DNS）
- 保留全量规则集
