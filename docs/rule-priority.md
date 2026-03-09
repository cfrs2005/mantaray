# 规则优先级

理解规则优先级是排障的基础。

## 命中顺序

规则按配置文件中的 **书写顺序从上到下** 匹配，**先命中者生效**。

Mantaray 默认顺序：

```
① RULE-SET: lan_direct.list        → DIRECT
② RULE-SET: sensitive_services.list → PROXY
③ RULE-SET: direct_cn.list         → DIRECT
④ RULE-SET: proxy_global.list      → PROXY
⑤ RULE-SET: custom.list            → DIRECT
⑥ GEOIP,CN                        → DIRECT
⑦ FINAL                           → PROXY
```

## 为什么是这个顺序

### 1. LAN 最先

局域网请求永远不应该走代理。放在最前面避免任何意外。

### 2. 敏感服务紧随其后

高风控服务的出口一致性是本项目核心目标。放在 CN 规则之前，确保即使域名被误判为国内，也会走代理。

### 3. CN 域名在海外规则之前

先匹配国内直连，再匹配海外代理。这样 `baidu.com` 不会意外走代理。

### 4. GeoIP 作为兜底

域名规则覆盖不到的 IP，由 GeoIP 数据库判断。中国 IP 直连。

### 5. FINAL 兜底一切

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
| 所有请求都走代理 | `direct_cn.list` 可能加载失败，检查 URL 是否可达 |
