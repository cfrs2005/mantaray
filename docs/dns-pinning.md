# DNS 出口绑定

出口一致性有两条链，不是一条。这份文档讲第二条。

## 问题

Shadowrocket 里「走哪个出口」和「用哪个 DNS 解析」是两条独立决策：

- **出口**由 `[Rule]` 决定
- **解析源**由 `[General] dns-server`、`[Host]` 绑定、或代理落地节点决定

一个域名要正确，取决于这两者是否配对。四种组合里有两种是错的：

| 出口 | 解析源 | 结果 |
|------|--------|------|
| DIRECT | 本地国内 DNS | ✅ |
| DIRECT | 静态 `[Host]` IP | ✅ 零 DNS 依赖，最硬 |
| DIRECT | 海外 DNS | ❌ 海外 IP 走国内出口，慢 / 超时 / 跨境回源 |
| PROXY | 落地节点解析 | ✅ |
| PROXY | 本地 DNS | ❌ 国内 IP 走海外出口，绕地球，GSLB 可能判异常 |

只配 `dns-server` 解决不了这个问题 —— 全局 DNS 是一个值，而不同域名需要不同解析源。

## 铁律

> **只给 DIRECT 出口的域名做 DNS 绑定。**
> **走 PROXY 的域名一个字都不要写进 `[Host]`，也不要放进 `always-real-ip`。**

走 PROXY 时，Shadowrocket 把域名原样交给落地节点解析，天然拿到目标区域的 IP。
本地插一手只会把它拽回错误的区域。

这条规则消除了「按域名逐个判断该用哪个 DNS」的分支：出口策略一旦确定，解析源就唯一确定。
`scripts/verify.py` 用它作为 FAIL 级断言。

## 三层解析

对 DNS 的依赖从弱到强：

| 层 | 写法 | 用在哪 |
|----|------|--------|
| L0 静态 Host | `domain = 1.2.3.4` | 内网服务 / DNS 已被证明不可信 |
| L1 域名级绑定 | `domain = server:https://doh.pub/dns-query` | DIRECT 出口，但全局 DNS 不可信 |
| L2 全局 | `[General] dns-server` | 兜底 |
| L3 落地解析 | 什么都不写 | PROXY 域名走这条 |

L0 默认关闭。静态 IP 最硬也最脆，对端换 IP 就断。
只在「L1 已经证明不够用」时逐条打开，并在注释里记下实测日期和 IP 来源。

## `[Host]` 的三个坑

三条都会**静默失效** —— 不报错，只是不生效：

1. **域名与 `=` 之间不能有空格。** `*. example.com = ...` 整条作废。
2. **通配不匹配裸域。** `*.example.com` 不覆盖 `example.com`，两条都要写。
3. **按书写顺序匹配，先命中先生效。** 具体域名必须写在同域通配之前。

三条 `scripts/verify.py` 都有断言守着，不要靠记。

## 案例：同一顶级域的出口分裂

有些服务用独立子域区分国内和海外区域，而不是用 GeoDNS。此时一条顶级域通配规则兜不住。
例如，假设 `service.example.com` 需要直连，而 `eu.service.example.com` 和
`us.service.example.com` 需要代理：

```text
DOMAIN-SUFFIX,eu.service.example.com,PROXY
DOMAIN-SUFFIX,us.service.example.com,PROXY
DOMAIN-SUFFIX,service.example.com,DIRECT
```

更具体的海外子域必须写在通配规则前面。只有 DIRECT 的域名需要写进 `[Host]`；
PROXY 域名不做本地 DNS 绑定，交给代理落地节点解析。

## 豁免

anycast 域名（Cloudflare、Fastly 等）不受铁律约束 —— 从哪解析都是同一个 anycast IP，
绑 DoH 是为了**防污染**，不是为了选区域。这种情况在条目上方写一行：

```
# pin-exempt: Cloudflare anycast，解析结果与解析源无关，绑 DoH 只为防污染
example.com = server:https://doh.pub/dns-query
```

`verify.py` 见到 `pin-exempt` 就跳过该条的配对检查。豁免必须写明理由，否则等于关掉门禁。

## 工作流

`[Host]` 段不支持 RULE-SET 远程加载，只能内联进每个 conf。所以真源只有一份，
4 个 conf 是产物：

```bash
vim dns/pinning.conf        # 改这里
python3 scripts/sync.py     # 注入 configs/
python3 scripts/verify.py   # 门禁
```

不要直接改 `configs/*.conf` 里的 `MANTARAY-PINNING-*` 标记区块，下次 sync 会覆盖。
`verify.py` 有漂移断言守着。

## 三种分发

本仓库是公开的，而绑定只能内联进 conf。两件事一撞，就有了这条约束：

> **写进 `configs/*.conf` 的东西 = 公开发布。**

以下内容不该进公开层：机场 / 订阅域名、内网 IP 与网段、自建 VPS 裸 IP、未公开的内部服务域名。

| 方式 | 做法 | 代价 |
|------|------|------|
| 公开层 | 写 `dns/pinning.conf`，走 `update-url` 自动更新 | 内容公开 |
| 本地层 | 写 `dns/pinning.local.conf`（已 gitignore），sync 生成 `configs/local/`，手动导入 | 放弃自动更新 |
| 私有源 | 把 `configs/local/*.conf` 托管到私有 gist，`update-url` 指过去 | 需自己维护托管 |

`dns/pinning.local.example.conf` 是本地层的模板。

## 排障

| 现象 | 检查 |
|------|------|
| 某域名绑了 DoH 却还是走代理 | 有没有对应的 DIRECT 规则？`verify.py` 会 WARN |
| 改了 `[Host]` 完全没反应 | 域名和 `=` 之间有空格；或被前面的通配抢先 |
| 裸域正常、子域异常（或反过来） | 通配不匹配裸域，两条都要写 |
| 海外服务解析到国内 IP | 该域名被误绑了本地 DNS，从 `[Host]` 删掉 |
| 内网域名连不上 | 公网 DNS 是否还返回内网 IP；`private-ip-answer` 是否为 true；考虑上 L0 |
| 配置更新后绑定丢了 | 改了 conf 而不是 `dns/pinning.conf`，被 sync 覆盖 |
