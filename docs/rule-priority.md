# 规则优先级

理解规则优先级是排障的基础。

## 命中顺序

规则按配置文件中的 **书写顺序从上到下** 匹配，**先命中者生效**。

Mantaray 默认顺序：

```
① RULE-SET: lan_direct.list         → DIRECT
② 私有域出口绑定（内联）              → DIRECT / PROXY
③ RULE-SET: sensitive_services.list → PROXY
④ RULE-SET: direct_cn.list          → DIRECT
⑤ RULE-SET: proxy_global.list       → PROXY
⑥ RULE-SET: custom.list             → DIRECT
⑦ GEOIP,CN                         → DIRECT
⑧ FINAL                            → PROXY
```

②是 `MANTARAY-PINNING-RULE` 标记区块，由 `scripts/sync.py` 从 `dns/pinning.conf` 注入。
它和 `[Host]` 段的 DNS 绑定一一对应 —— 一个域名的出口和解析源必须一起声明，
否则会出现「国内 IP 走海外出口」这类脱耦。见 [DNS 出口绑定](dns-pinning.md)。

## 为什么是这个顺序

### 1. LAN 最先

局域网请求永远不应该走代理。放在最前面避免任何意外。

### 2. 私有域绑定在公共规则之前

私有域是你掌握最确切信息的部分（哪个子域在哪个区域、内网 IP 是多少）。
公共清单是通用猜测。确切的知识应该先命中。

同一顶级域下子域出口分裂时（例如 `bot-eu.gs-robot.com` 在 Azure 欧洲、
其余在阿里云上海），**更具体的子域必须写在通配之前**，否则被通配抢先。

### 3. 敏感服务紧随其后

高风控服务的出口一致性是本项目核心目标。放在 CN 规则之前，确保即使域名被误判为国内，也会走代理。

### 4. CN 域名在海外规则之前

先匹配国内直连，再匹配海外代理。这样 `baidu.com` 不会意外走代理。

### 5. GeoIP 作为兜底

域名规则覆盖不到的 IP，由 GeoIP 数据库判断。中国 IP 直连。

### 6. FINAL 兜底一切

未命中任何规则的请求，默认走代理。这是「白名单直连」思路的体现。

## 规则类型优先级

在同一 RULE-SET 内部，规则类型的匹配逻辑：

| 类型 | 匹配对象 | 示例 |
|------|----------|------|
| `DOMAIN` | 精确域名 | `DOMAIN,www.google.com` |
| `DOMAIN-SUFFIX` | 域名后缀 | `DOMAIN-SUFFIX,google.com` |
| `DOMAIN-KEYWORD` | 域名关键词 | `DOMAIN-KEYWORD,google` |
| `IP-CIDR` | IP 段 | `IP-CIDR,10.0.0.0/8,no-resolve` |
| `GEOIP` | IP 地理位置 | `GEOIP,CN` |
| `FINAL` | 兜底 | `FINAL,PROXY` |

## 判断某个请求命中了哪条规则

1. 打开客户端的请求日志/最近请求
2. 找到目标请求
3. 查看其命中规则和策略
4. 对照上述顺序确认是否符合预期

## 常见意外场景

| 现象 | 可能原因 |
|------|----------|
| 国内站走了代理 | 该域名在 `proxy_global.list` 且优先于 `direct_cn.list` |
| 海外站走了直连 | 该域名 DNS 解析到了国内 IP，被 GeoIP 匹配 |
| 敏感服务走了直连 | 域名不在 `sensitive_services.list` 中，需手动添加 |
| 某子域和同域其他子域出口相同（本该不同）| 具体子域规则写在了通配之后，被抢先；跑 `scripts/verify.py` |
| 绑了 DoH 的域名还是走代理 | 只绑了解析源没给出口规则，落到 GEOIP 兜底；`verify.py` 会 WARN |
| 所有请求都走代理 | `direct_cn.list` 可能加载失败，检查 URL 是否可达 |
