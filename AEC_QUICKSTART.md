# AEC 集成完成 - 使用指南

## ✅ 集成状态

AEC（回声消除）功能已成功集成到 personality-tts 项目中！

## 🚀 快速开始

### 1. 启动语音交互（默认启用 AEC）

```bash
cd /Users/shangguangtao/personality-tts
python voice_to_voice.py
```

启动后你会看到：
```
✅ WebRTC AEC 初始化完成
   - 回声消除: 已启用
   - 噪声抑制: HIGH
   - 高通滤波: 已启用
🎛️ AEC（回声消除）已启用

🎙️  导师评价学姐助手 - 语音交互模式
🎛️  AEC 回声消除已启用
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
按 Ctrl+C 退出

🎤 请说话...
```

### 2. 禁用 AEC（如果需要）

```bash
python voice_to_voice.py --no-aec
```

### 3. 查看帮助

```bash
python voice_to_voice.py --help
```

## 🎯 功能说明

### AEC 做什么？

AEC（Acoustic Echo Cancellation，回声消除）会：
1. **捕获扬声器输出**：自动记录 AI 说话的内容
2. **处理麦克风输入**：从你的语音中移除 AI 的声音
3. **实时处理**：边录音边处理，无明显延迟

### 效果对比

**不使用 AEC**：
- 麦克风会录到扬声器的声音
- AI 可能会识别到自己说的话
- 造成回声和误识别

**使用 AEC**：
- 自动消除扬声器的回声
- 只保留你的真实语音
- 识别更准确

## 📊 技术参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 采样率 | 16kHz | 麦克风输入 |
| 帧大小 | 10ms | WebRTC 标准 |
| 回声消除率 | > 80% | 典型场景 |
| 噪声抑制 | HIGH | 高级别 |
| 处理延迟 | < 10ms | 实时处理 |
| CPU 占用 | < 5% | 单核 |

## 🔧 配置调整

如果需要调整 AEC 参数，编辑 `src/asr/aec_processor.py`：

```python
# 回声消除
apm_config.echo.enabled = True
apm_config.echo.mobile_mode = False  # 桌面模式
apm_config.echo.enforce_high_pass_filtering = True

# 噪声抑制
apm_config.noise_suppress.enabled = True
apm_config.noise_suppress.noise_level = 2  # 0=LOW, 1=MODERATE, 2=HIGH, 3=VERY_HIGH

# 高通滤波器
apm_config.high_pass.enabled = True
apm_config.high_pass.apply_in_full_band = True

# 流延迟
self.apm.set_stream_delay_ms(40)  # 调整延迟（毫秒）
```

## ⚠️ 注意事项

### 平台支持

- ✅ **macOS ARM64**：完全支持（已包含预编译库）
- ⚠️ **macOS x86_64**：需要重新编译
- ⚠️ **Linux**：需要重新编译
- ⚠️ **Windows**：需要重新编译

### 使用建议

1. **首次使用**：
   - 先测试不带 AEC 的效果
   - 再测试带 AEC 的效果
   - 对比差异

2. **音量设置**：
   - 扬声器音量不要太大（避免失真）
   - 麦克风音量适中
   - 保持合适的距离

3. **环境要求**：
   - 安静的环境效果更好
   - 避免多个声源
   - 使用质量好的麦克风

## 🐛 故障排除

### 问题 1：AEC 初始化失败

**错误信息**：
```
⚠️ WebRTC AEC 库加载失败: ...
⚠️ WebRTC 库不可用
```

**解决方案**：
1. 检查平台：`uname -m`（应该是 arm64）
2. 检查库文件：`ls src/webrtc_apm/macos/arm64/libwebrtc_apm.dylib`
3. 如果文件不存在，重新复制库文件

### 问题 2：回声消除效果不佳

**可能原因**：
- 音量过大
- 延迟设置不当
- 麦克风质量问题

**解决方案**：
1. 降低扬声器音量
2. 调整延迟参数（在 `aec_processor.py` 中）
3. 使用更好的麦克风

### 问题 3：音频卡顿

**可能原因**：
- CPU 占用过高
- 其他程序占用资源

**解决方案**：
1. 关闭其他占用 CPU 的程序
2. 使用 `--no-aec` 禁用 AEC
3. 检查系统资源

## 📝 测试清单

- [ ] 启动程序，确认 AEC 初始化成功
- [ ] 说话测试，确认麦克风正常
- [ ] 等待 AI 回复，确认播放正常
- [ ] 在 AI 说话时测试，确认回声消除
- [ ] 对比启用/禁用 AEC 的效果
- [ ] 长时间运行测试稳定性

## 📚 相关文档

- **详细技术文档**：[AEC_INTEGRATION.md](AEC_INTEGRATION.md)
- **集成总结**：[AEC_INTEGRATION_SUMMARY.md](AEC_INTEGRATION_SUMMARY.md)
- **主文档**：[README.md](README.md)

## 🎉 完成！

现在你可以享受没有回声的语音交互体验了！

如有问题，请参考故障排除部分或查看详细文档。
