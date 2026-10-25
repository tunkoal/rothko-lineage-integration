# rothko LineageOS 23.2 公开协作入口

这是 Redmi K70 Ultra 的**非官方开发源码**，用于共同修复和审查，不是新的 ROM 发布，
也不表示已满足 LineageOS official 要求。框架为 Android 16，原厂 vendor 为 Android 14/API 34，
固定固件为 OS3.0.307.0.WNNCNXM。

四个配套仓库分别负责：

- `android_device_xiaomi_rothko`：设备配置、服务、overlay、策略和提取修补代码。
- `proprietary_vendor_xiaomi_rothko`：vendor/ODM 构建元数据、来源和散列；不包含专有载荷。
- `android_device_xiaomi_rothko-kernel`：原厂内核/模块的提取配方；不包含二进制或对应内核源码。
- `rothko-lineage-integration`：本仓库，提供完整固定 manifest、平台补丁、重建工具和协作说明。

**只拿设备树不能构建同样的系统。** 应使用 `baseline.json` 中的配套版本，以及
[BUILD.md](BUILD.md) 的同步、补丁应用和提取流程。公开仓库不代发原厂包，参与者需自行
准备对应固件并解包；脚本会校验 778 项设备载荷、2975 项 vendor/ODM 载荷及 581 项内核材料。
这些输出保持在本地并被 Git 忽略，不要强制加入提交。

设备最初 37 条社区提交及签名 SHA 保留；后续提交在独立副本中过滤载荷和本机路径，
保留作者、提交者和映射记录，原仓库未被改写，详见 [HISTORY.md](HISTORY.md)。
现有逐文件版权/许可继续有效；新集成工具和文档使用 Apache-2.0，不能据此重新许可原厂载荷。

先阅读 [KNOWN_ISSUES.md](KNOWN_ISSUES.md)、[VALIDATION.md](VALIDATION.md) 和
[CONTRIBUTING.md](CONTRIBUTING.md)。AOD/30 Hz、电信 IMS、相机质量等未决项保持登记；
蓝牙默认采用已验证的软件 A2DP；拍照 JPEG_R 仍是未验收开发路径。
原厂温控、亮度/HDR 的完整等价及全新 ROM 构建/实机回归尚不能宣称通过。

提取和补丁工具不刷手机、不切槽、不操作 LK/preloader。提问题时请提供版本和复现步骤，
不要公开 IMEI、序列号、NV/校准、指纹/人脸模板、私钥或含个人信息的原始日志。
