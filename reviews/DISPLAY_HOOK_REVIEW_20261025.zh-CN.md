# 显示色彩与亮度扩展边界复核

日期：2026-10-25。仅审查指定最终源码、已导出提交和已有 Soong 变量。
未操作手机、改活动源码、启动构建或做新的物理亮度验证。
本轮并非 frameworks/base 全部 28 条提交的完整语义审查。

## SurfaceFlinger 色彩扩展

默认 `DisplayColorExtension` 返回 disabled、空 policy，回调为空；未设置
display_color_lib 时链接此实现。rothko 在 BoardConfig 中显式选择
`librothko_display_color_provider`，当前生成的 Soong VendorVars 也确认了该值。
新增接口是平台私有编译接口，不是已有稳定 HAL ABI，也不是单靠 overlay 就能替代的接口。

`Output::pickColorProfile()` 仅在扩展启用且输出有物理 display ID 时读取 policy；
设备 provider 又只接管第一块内部屏，忽略其他屏。未启用扩展时 revision 为零，
原 dataspace/intent 选择路径仍可执行。这里是指定路径阅读结论，不能替代整个 SF 的
默认设备回归、ABI 或渲染性能检查。

设备侧的额外约束包括：

- 缓存 SDR intent 只有在 HDR dataspace 为 UNKNOWN 时才覆盖原选择；
  首个 HDR 帧不用等待异步控制器返回才解除 SDR 覆盖。
- 不支持的 intent 不把 UNKNOWN/NATIVE 的兜底当作应用成功，而会报告拒绝。
- HWC 的实际返回值与 SF 已选状态分开报告；同模式失败只有新 revision 才重试。
  这不是面板已执行 PQ 的确认，也不是应用请求已成功的保证。
- SF 路径使用原子缓存及 try-lock 更新；锁竞争/队列溢出清空覆盖并要求新状态。
  此处未直接执行 stock DisplayFeature Binder 调用；设备私有 IPC 在 worker 上。
- 连接 generation 和 request/revision 关联用于隔离过期回调；HDR、电源变化和
  部分状态未知时清空覆盖。状态丢失后需真实事件重建，不能凭空补成功回调。

### 服务故障覆盖仍有限

设备私有 AIDL 中 `reportState` 是 **oneway**，`setListener` 是同步调用。
不能把发送 reportState 成功当成对端已处理或已经执行原厂指令。

worker 仅在 mDirty 为 true 时发送 reportState；代码注释所称“周期报告”不等于
无状态变化时仍有独立心跳。死亡通知或可检测 IPC 错误会清空 policy 并重连；
没有可用死亡通知时，检测时刻也依赖后续发送。

`DisplayColorPolicy` 没有有效期字段，当前没有覆盖任意对端卡住场景的完整租约机制。
同步 setListener 不返回、对端存活但不处理消息，以及回调停止推进等场景尚待故障注入。
这是静态审查识别的验收缺口，不是已在手机上复现的新故障；也不能据此盲加超时、
轮询重试或改变原厂色彩时序。SF 关键路径隔离与控制器最终能恢复是两项验收。

## 亮度与温控钩子

`config_deviceSpecificBrightnessPolicy` 默认为空时 create() 返回 null；
modifier 只为默认 display 创建策略，外屏没有设备策略实例，apply() 在 null 时返回。
rothko 通过设备资源配置类名并打包独立 system-server jar。

所检查的约束路径：

- common cap 与 SDR cap 由同一 BrightnessCap 快照取得，SDR 只能进一步收紧，
  不能把 SDR 白点上限放大成 HDR 峰值。
- common cap 与已有 builder/聚合上限取更严格者；没有替代原 ThermalModifier，
  原其他 clamper 仍保留在列表中。
- 无效转换收紧到最小值；配置了类却加载失败时采用零 nits 限制，避免加载错误放开提亮。
  这会牺牲可见性，仍需实际打包错误/恢复路径验证，不能称为无条件无黑屏兜底。
- rothko 读数有 2500 ms 过期检查，失败时取 failure cap 和最近 cap 的更低值；
  默认 160 nits 来自固定原厂表的最低正上限，不是新的温度阈值。
- 正常 cap 为 thermal/content 的更小值；SDR 白点另受普通段限制。
  这是上限决策，不能推导手机一定激发对应物理 nits。

仅空资源不能概括所有亮度补丁的默认影响。以下两项没有机型 opt-in：

1. `436e2867`：hasSdrToHdrRatioSpline 同时检查现代 hdrBrightnessData 与旧 HBM 配置。
   其他使用现代 HDR map 的设备也会改变能力判断；应作为通用修复单独评审。
2. `dc729ae6`：HBM 时间窗口/上限/最小值均为零时不再安排每毫秒配额回调。
   影响满足该配置的其他设备；本项没有删除温度、光照等其他 HBM 判定。
   是否适用于其他设备和调度回归仍需验证，不能称为设备专用代码。

本轮没有确认完整原厂温控/亮度等价。设备 brightness/README 已明确保留原厂 Gallery
token 请求、37/35°C gate、最高 2.25 倍 boost 等独立未完成路径。
显示 HDR 可提亮的既有实测也不能替代强光、持续高温、数据过期、功耗和各内容路径验收。
保留 LineageOS 动画的既定选择不变；未引入额外时间常数滤波。

## 已放弃的充电控制：确认最终源码撤销干净

整棵 Git tree 比较结果：

- lineage-sdk 当前 `e988298b` 与充电候选前的 `8601644f` 完全相同。
- LineageParts 当前 `fc0e11c2` 与充电候选前的 `c86e9dc3` 完全相同。

所以这两个仓库的最终源码没有残留本轮已撤销的充电控制候选差异，色彩改动仍保留。
原提交和撤销历史都未删除。该比较不声称删除手机持久设置、不涵盖全部设备/vendor
充电文件，也不涉及仍保留的原厂充电驱动或协议。

## LiveDisplay 客户端恢复

lineage-sdk 的颜色模式服务从 waitForDeclaredService 改为 checkService；
缺服务不无限等待，也不把不存在的服务永久缓存。死亡回调/RemoteException 清除对应
旧实例，旧实例的迟到死亡不会踢掉替代实例。setter 失败不自动重放，避免远端已执行
但返回失败时重复写入。AIDL 的空 mode/name 会返回不可用结果。

这些方法仍是同步 Binder 方法；“查找不无限等待”不等于远端方法有调用超时。
这是共享 SDK 对所有相关 LiveDisplay HAL 的行为变化，需要其他实现的回归。
LineageParts 异步 UI 和控制器完整状态机尚未在本轮逐行审查。

## 证据与剩余工作

- `snapshots/20261025/display-hook-review-evidence.json`：10 个源文件散列、关键位置和
  当前 Soong provider 选择；不包含原厂二进制反编译结论。
- `snapshots/20261025/charging-withdrawal-tree-check.json`：上述两仓库精确 tree 对比。

后续应继续审查 AOD/抬起唤醒、Settings/LineageParts UI、frameworks/base 其他调用点，
并把控制器故障注入和非 rothko 默认回归写入验收范围。
本轮不把未运行的测试、未审查的路径标为通过，不调整发布批准状态。
