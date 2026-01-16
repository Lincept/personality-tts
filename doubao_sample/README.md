# RealtimeDialog

实时语音对话程序，支持语音输入/输出、文本交互与可选记忆存储。

## 配置要点（config.py）

- 接口鉴权：通过环境变量注入（App ID / Access Key），避免明文写入仓库
- 角色与风格：`start_session_req.dialog`（`bot_name`、`system_role`、`speaking_style`）
- ASR/TTS：`start_session_req.asr`、`start_session_req.tts`（`speaker`、采样率）
- 音频采集/播放：`input_audio_config`、`output_audio_config`
- 记忆库：`VIKINGDB_*`（仅在 `--memory` 开启时使用）

## 配置指导（简要）

1) 必填鉴权

- 必填环境变量：
   - `DOUBAO_APP_ID`
   - `DOUBAO_ACCESS_KEY`

示例：

```bash
export DOUBAO_APP_ID=your_app_id
export DOUBAO_ACCESS_KEY=your_access_key
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
- 开启方式：配置 `VIKINGDB_*` 环境变量后运行 `python main.py --memory`。
- 建议环境变量：
   - `VIKINGDB_AK` / `VIKINGDB_SK`
   - `VIKINGDB_COLLECTION`
   - `VIKINGDB_USER_ID` / `VIKINGDB_ASSISTANT_ID`

示例：

```bash
export VIKINGDB_AK=your_ak
export VIKINGDB_SK=your_sk
export VIKINGDB_COLLECTION=test1
export VIKINGDB_USER_ID=1
export VIKINGDB_ASSISTANT_ID=111
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