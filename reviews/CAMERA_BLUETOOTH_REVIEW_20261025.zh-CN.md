# 相机与蓝牙补丁的启用边界

日期：2026-10-25。复核固定版本的最终源码、原始提交和本机已有构建属性；
未读取手机、未改活动源码、未重新构建。不是新增硬件实测或完整相机安全审计。

## 人脸相机客户端可与拍照 JPEG_R 分离

原 frameworks/av 上游基点为 `b6b36c1fdb3c6ffced822a054fbf035b544f0de2`，
当前 HEAD 为 `e5e04617427d644cb65f3c8c8e5980c68c443aa1`。
本轮使用临时索引和独立对象目录，只读借用源仓库对象，验证两组候选：

| 候选 | 原始提交 | 结果 |
| --- | --- | --- |
| face-only | 275e22afe79f2a293982b4f94e1aaf09771fe050、e5e04617427d644cb65f3c8c8e5980c68c443aa1 | 从基点直接应用成功；仅 camera/ndk 下 20 个文件有差异，该目录与当前 HEAD 完全一致 |
| face-and-map-error | 上述两条，另加 dbda2f3461f1a4d7dba793eb916731b5fada4462 | 应用成功；另保留 Camera3StreamInterface.h 的映射错误传播修复，共 21 个文件 |

构造期望 tree 的方式是“上游基点 + 当前 HEAD 指定路径的最终差异”，再独立应用
原始提交补丁比较整棵 tree；不能仅凭补丁能打上就认为结果相同。
两组在指定路径之外均与上游相同，没有 JPEG_R 代码或测试/构建规则的差异。
输出 mbox 保留原作者、正文、Change-Id；没有创建替代作者的提交。

工具为 `tools/verify-camera-feature-split.py`，报告在
`snapshots/20261025/camera-feature-split-replay.json`。
候选 mbox 仅存于 `out/source-prep/20261025/camera-feature-split/`，未应用到任何活动分支。
临时 tree 对象会随临时目录清理；报告中的 tree 散列是校验值，不是可公开获取的提交。

### 客户端选择和影响范围

- `libcamera2ndk_vendor_rothko` 是单独模块，安装 stem 为
  `libcamera2ndk_vendor-rothko`；device.mk 显式选择它，face HAL 的依赖修补映射指向此文件。
  stock 旧客户端已不在当前提取选择内。
- 只有此私有模块设置 `ROTHKO_LEGACY_CAMERA_WINDOW_HANDLE`。
  相关类型分支同时检查 vendor/VNDK 条件；默认别名仍为 ANativeWindow。
  这是源码意图和构建选择隔离，不能代替普通模块 ABI 和回归验证。
- 私有模块使用 `android.hardware.camera.common-helper_nogralloc`；原默认 vendor
  模块仍使用原 helper。hardware/interfaces 的两条辅助库提交需配套，不能漏交付。
  该辅助库未包含 HandleImporter，也未声明默认 helper 的 libui/libgralloctypes 依赖；
  这只说明该 helper 的直接依赖，不声称整个进程没有间接图形依赖。
- 宏关闭时公共源码仍有别名和辅助函数重构，故不能把私有变体的存在说成公共源码零改动。
  native_handle 生命周期、异常回调、标准客户端和 provider 的完整回归仍需后续检查。
- `Camera3StreamInterface.h` 的映射修复去掉了内层遮蔽 res 的声明，使 lockAsync 失败
  能返回给调用者。这是全局错误传播修复候选，不属于机型专用 window token 兼容。

人脸整体还依赖其他平台和设备配置。两条 av 提交能分离不表示只给这两条就能做人脸，
也不表示移除其他 av 提交后的 ROM 已通过编译和录入/认证实测。

## 暂缓的 JPEG_R 仍有显式启用配置

此前 DEVICE_AUDIT 已登记该问题；本轮进一步核对实际构建输出及调用点：

```properties
ro.camera.compositeJpegRIds=0,1
ro.camera.compositeJpegRRotateIds=0,1
```

以上值同时出现在活动设备源码、独立整理副本和当前输出 system/build.prop。
因此“暂缓修复”不能表述为“设备已经关闭此路径”。

`JpegRCompositeUtils::isEnabled()` 从对应属性读取相机 ID；AIDL provider 还会检查
framework JPEG_R 总开关、原 composite 状态及 metadata 推导是否成功，才更改能力。
属性存在只是显式 opt-in，不证明任意一次拍照已走到该路径。
两条 system/sepolicy 提交只添加这两个属性的标签，不会自行打开 JPEG_R。

### 并非所有改动都受相机 ID 限制

`JpegRCompositeStream` 中的输入帧首次观测记录和五秒不完整帧超时路径没有检查
mRequireInternalJpeg；进入该 composite 类的非 opt-in 设备也会受影响。
这不影响所有普通 JPEG 拍摄，但不能称为仅影响 rothko 或默认全无行为变化。
此外，成功编码后的 GraphicBufferLocker 释放时序调整同样处于公共路径。

这些逻辑可能有通用修复价值，尚不能仅由本轮阅读断言存在运行故障；但必须单独说明
动机、适用范围和回归证据，不能借设备 opt-in 掩盖其全局影响。

后续整理应先决定：保留为明确标注的未验收开发功能，还是在新的整理候选中关闭设备
选择并进一步拆出代码。仅清空两个属性不会清除全局超时/锁时序差异，也不等于禁用
HAL 原生 Ultra HDR。不得混同“显示 HDR 提亮已验证”和“拍照 Ultra HDR 已验证”。
本轮没有改属性、删除相机功能、移除标签或修改当前候选。

## 蓝牙：软件编码默认与音频 HAL 选择是两层配置

当前源码及构建输出均设置：

```properties
persist.bluetooth.a2dp_offload.disabled=true
```

这延续用户已确认连续出声的软件 A2DP 默认方案。持久属性在旧 userdata 上可能保留旧值，
不能只读取 build.prop 就宣称手机运行值或迁移行为正确；本轮未读手机。

另一个独立构建选择为 `audio_bluetooth_hw.use_stock_hal=true`，在 device.mk 和本机
Soong VendorVars 中均已确认。对应 Bluetooth 补丁只使此选项开启时禁用 A16 源码
audio.bluetooth.default 模块；未选择该变量的设备仍 enabled=true。
这不是停用整个蓝牙 AIDL 服务，也不等于重新开启硬件卸载。

rothko 明确安装 `audio.bluetooth.default.rothko`：

- 使用 stock 音频 HAL，安装到 vendor/lib64/hw/audio.bluetooth.default.so；
- 模块 overrides 原默认模块，避免同安装名冲突；
- 配套私有 legacy session bridge，并共同依赖 stock `_mtk` session 库；
- 不把通用 A16 session 库改名覆盖为 stock 版本。

这是当前软件音频链的实际交付依赖，不能因“已经使用软解”就省掉 stock HAL/桥接库或
Bluetooth 构建选择补丁。hardware offload 继续搁置；本轮没有验证 SCO/HFP、耳机麦克风、
所有编解码器或其他设备，不能扩大此前媒体播放验收范围。

## 证据与待验收项

`snapshots/20261025/camera-bluetooth-semantic-evidence.json` 固定已读源文件散列、
关键行号和已有产品/Soong 设置散列，避免把不同候选的结论混用。
该报告记录的是实际读取的活动文件；device 整理副本中的对应选择也已核对。

下一阶段需要把已验证的人脸客户端与未验收的 JPEG_R 默认整理成明确候选，再做干净
构建和实机回归。当前独立分离验证不改变发布批准状态，不替代源码分发条件审查。
