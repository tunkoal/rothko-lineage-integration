# AOD、抬起监听与色彩 UI 复核

日期：2026-10-25。未改活动平台/设备仓库，未启动 Android 构建或操作手机。
本轮移植了两套已有主机 fixture 的运行入口，运行生产 Java 的小型主机检查，
并阅读了色彩 UI 的请求/回读流程。没有宣称整轮候选通过实机验收。

## AOD 绘制租约

DozeSuspendDrawController 同时要求 SystemUI 的 doze_present_before_suspend=true 和
sdkDesiredPresentTime feature flag。默认资源为 false；rothko overlay 为 true。
本轮未实测设备当前 feature flag 值，不能只看到 overlay 就断言运行时已启用。

已读代码的生命周期：

1. DozeScreenState 先通知 host，再提交屏幕状态；只有目标 DOZE_SUSPEND 进入租约路径。
2. 使用原生 DRAW_WAKE_LOCK 等待 committed display state 为 DOZE，再将完成监听合并到
   AOD 窗口的真实下一帧，不用空 transaction 或 committed 回调冒充已经显示。
3. 等待 present fence 在后台 executor 进行，结果回主 handler；只有匹配当前 generation
   和最后 frame 的完成才释放锁，旧会话/旧帧不能释放新租约。
4. 离开目标状态、stopDozing、view detach、显示移除、失败及超时均有清理路径。
   成功立即释放；失败上限 3 秒，fence 等待 1 秒。失败后停止监听，避免反复续锁。
5. 自然时钟/通知更新会再申请租约；没有周期性强刷 AOD 或永不释放的常驻锁。

这处理的是“帧呈现与挂起顺序”，不是刷新率选择：它不能证明 AOD 已达到原厂 30 Hz。
主机检查也不证明 DRAW 锁在真实 HWC/驱动上的效果，不能推导功耗已经与原厂相同。

### 主机检查结果与边界

`tools/test-doze-draw-host.py` 直接编译当前生产 Controller，提供少量 Android fakes。
11 个场景通过：资源关闭、feature flag 关闭、就绪/完成、过期帧、旧会话完成、
超时失败后不循环续锁、无效 fence、detach/attach、非硬件窗口、未 signal fence、
自然更新重新申请并释放。

Flags 为 fixture 可控值，fence、Display committed state、handler 和 executor 都是 fake。
没有执行真实 JNI/图形调度、Dagger/资源链接；没有量测 panel frame、空闲功耗或物理 Hz。
当前 fixture 也不覆盖所有 view 替换、display 移除、线程拥塞及 transaction 拒绝路径。

## 原厂 special-trigger 抬起传感器

config_dozePickupSensorType 默认空，仍走原 TYPE_PICK_UP_GESTURE 选择；只有显式
配置的传感器同时是 wake-up、SPECIAL_TRIGGER 才启用新的 adapter。
rothko 配置为 xiaomi pick up sensor，没有改传感器 HAL 的 reporting mode。

adapter 只接受同一传感器首个数值恰为 1 的事件；0、2、NaN、空值不触发抬起。
事件数组先复制再投递；generation 使停用/重新注册前的排队事件与旧 listener 失效。
注册失败会恢复未监听状态，允许后续重试；回调用已有 WakeLock.wrap，停用会注销。
上层沿用 DOZE_PICK_UP_GESTURE、配置能力和请求/禁用条件，不把传感器存在等同用户已开启。
没有把 put-down 事件改成强制熄屏，也没有引入新的固定滤波时间。

`tools/test-pickup-host.py` 编译生产 DozePickupListener，8 组检查通过：幂等/过滤、
数据复制/投递、排队取消与锁平衡、旧 listener、其他传感器、注册失败重试、
模式/非 wake-up 拒绝、回调内重入停用。
这不覆盖 DozeSensors 整体装配、用户切换的全部上层路径、实际抬起亮屏或口袋场景。

## 色彩设置 UI

Settings 的 ColorModeUtils 在 LiveDisplay 配置开启、显示模式能力存在且 PartsList 有
对应入口时使用 LiveDisplay 路由。旧页候选/写入和搜索，以及新 ColorModeScreen 的
可用性都做相应排除，减少两个界面争用不同色彩接口。
这里存在对 SDK/设备声明/应用入口的跨仓库依赖，不能仅移走 Settings 补丁。

LineageParts ColorProfileFragment：

- 用单线程 executor 执行 setter 和模式/current/default 回读，主线程更新 UI；
  busy 或无可用状态时不接受新的模式点击。
- setter 即使失败也回读，因为实际模式可能已经变化、仅保存失败。
  当前勾选来自 currentMode；成功确认要求 current/default 都匹配请求 ID。
- onStop/onDestroyView 递增请求 generation 并移除本 handler 的回调；结果还检查
  started/isAdded，旧页面结果不直接更新新页面。
- onDestroy 执行 shutdownNow，但代码明确说明不能取消已进入 Binder 的调用。
- 不可用时保留旧选项但禁用，显示重试；加载状态清空 summary，不传资源 ID 0。
- 原色/生动/鲜艳有中文资源映射，不把后端原始名称直接视为最终本地化文案。

这确认了指定最终代码路径，不是完整 Fragment/旋转/搜索/UI 故障测试。
executor 不阻塞 UI 线程不等于它有调用期限；如果远端一直不返回，后续读写仍会排队。
本轮未添加取消 setter 的重放或超时后假定成功机制。

人脸 Settings 的 preview/sidecar 生命周期、权限与主题合成仍需下一阶段逐项审查；
不能把上述色彩 UI 检查扩展为整仓库通过。

## 可交付的运行入口

两份脚本从本项目原 tools 脚本整理而来，保留测试主体；不修改原脚本。
新增显式 --source-root/--output，拒绝覆盖已有输出或写入源码目录。
AOD fixture 另增加关闭 feature flag 的场景。需要源码树的 Linux x86 JDK21，
不声称支持任意 Windows/macOS 主机。

```sh
python3 source-release/tools/test-doze-draw-host.py \
  --source-root /path/to/LineageOS-23.2 --output /path/to/new-aod-host-test
python3 source-release/tools/test-pickup-host.py \
  --source-root /path/to/LineageOS-23.2 --output /path/to/new-pickup-host-test
```

两套入口对已有输出、源码内输出分别拒绝，4 项保护检查通过。
证据、生产文件和工具散列见 `snapshots/20261025/doze-pickup-host-review.json`。
这不是 lunch/Soong/ROM 构建，不改变发布批准，不替代当前统一候选的实机验证。
