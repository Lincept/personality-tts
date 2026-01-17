# RealtimeDialog

实时语音对话程序，支持语音输入/输出、文本交互与可选记忆存储。

## 配置要点（config.py）

- 接口鉴权：通过环境变量注入（App ID / Access Key），避免明文写入仓库
- 角色与风格：`start_session_req.dialog`（`bot_name`、`system_role`、`speaking_style`）
- ASR/TTS：`start_session_req.asr`、`start_session_req.tts`（`speaker`、采样率）
- 音频采集/播放：`input_audio_config`、`output_audio_config`
- 记忆库：`VIKINGDB_*`（仅在 `--memory` 开启时使用）
- 日志落盘：通过 `.env` 控制是否将控制台输出写入 `log/` 目录

## 配置指导（简要）

1) 必填鉴权

-- 推荐方式：使用 doubao_sample 目录内的 `.env.example` 生成 `.env`，再填写变量。

```bash
cp .env.example .env
```

必填变量：

- `DOUBAO_APP_ID`
- `DOUBAO_ACCESS_KEY`

（可选）日志写入 `log/`：

```dotenv
DOUBAO_LOG_TO_FILE=true
DOUBAO_LOG_DIR=log
DOUBAO_LOG_FILE=console.log
```

2) 语音与角色

- 选发音人：`start_session_req.tts.speaker`
- 角色设定：`start_session_req.dialog.system_role`
- 风格语气：`start_session_req.dialog.speaking_style`

- 可用发音人：

   - `zh_female_vv_jupiter_bigtts`
   - `zh_female_xiaohe_jupiter_bigtts`
   - `zh_male_yunzhou_jupiter_bigtts`
   - `zh_male_xiaotian_jupiter_bigtts`

3) 音频参数

- 采样率：`start_session_req.tts.audio_config.sample_rate`
- 录音流：`input_audio_config.sample_rate` 与声道/分块大小

4) 记忆存储（可选，重要）

- 作用：在会话结束时把 ASR 文本（用户）与 TTS 文本（助手）写入 VikingDB，便于后续画像与事件检索。
- 开启方式：在 `.env` 中配置 `VIKINGDB_*` 后运行 `python main.py --memory`。
- 建议环境变量：
   - `VIKINGDB_AK` / `VIKINGDB_SK`
   - `VIKINGDB_COLLECTION`
   - `VIKINGDB_USER_ID` / `VIKINGDB_ASSISTANT_ID`

示例（写入 `.env`）：

```dotenv
VIKINGDB_AK=your_ak
VIKINGDB_SK=your_sk
VIKINGDB_COLLECTION=test1
VIKINGDB_USER_ID=1
VIKINGDB_ASSISTANT_ID=111
```

- 关键字段说明：
   - `VIKINGDB_COLLECTION`：记忆库集合名
   - `VIKINGDB_USER_ID` / `VIKINGDB_ASSISTANT_ID`：用于检索与隔离不同用户/助手之间的记忆
- 说明：若会话中没有产生有效文本（例如仅音频但无识别结果），将不会保存。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

麦克风：
   ```bash
   python main.py
   # python main.py --mod=audio
   ```
音频文件：
   ```bash
   python main.py --audio=data/whoareyou.wav
   ```
文本：
   ```bash
   python main.py --mod=text --recv_timeout=120
   ```
启用记忆存储：
   ```bash
   python main.py --memory
   ```
启用 AEC（回声消除）：
   ```bash
   python main.py --aec
   ```
组合使用（启用记忆存储和 AEC）：
   ```bash
   python main.py --memory --aec
   ```

### AEC（回声消除）功能说明

AEC（Acoustic Echo Cancellation，回声消除）功能可以消除语音助手播放声音时产生的回声，提高语音识别准确度。

**使用要求：**
- 目前仅支持 macOS 平台
- 需要 WebRTC 音频处理库（已包含在 `aec/` 目录中）
- 使用 16kHz 采样率的音频输入

**使用方法：**
```bash
# 启用 AEC
python main.py --aec

# 可与其他参数组合使用
python main.py --aec --memory
```

**原理说明：**
- AEC 处理器会接收两路信号：
  1. 参考信号（扬声器播放的声音）
  2. 麦克风采集的信号（包含用户语音 + 回声）
- 通过 WebRTC 算法消除麦克风信号中的回声部分
- 输出干净的用户语音信号

**配置要求：**
- 输入音频（麦克风）：16kHz, int16 格式
- 输出音频（扬声器）：支持 16k/24k/48kHz，支持 int16/float32 格式（会自动转换）

**注意事项：**
- 在非 macOS 平台上使用 `--aec` 参数会显示警告但不影响程序正常运行
- 如果 AEC 初始化失败，程序会自动回退到不使用 AEC 的模式
- AEC 处理会增加轻微的延迟（约 40ms）