# RealtimeDialog

实时语音对话程序，支持语音输入/输出、文本交互与可选记忆存储。

## 配置要点（config.py）

- 接口鉴权：通过环境变量注入（App ID / Access Key），避免明文写入仓库
- 角色与风格：`start_session_req.dialog`（`bot_name`、`system_role`、`speaking_style`）
- ASR/TTS：`start_session_req.asr`、`start_session_req.tts`（`speaker`、采样率）
- 音频采集/播放：`input_audio_config`、`output_audio_config`
- 记忆库：通过 `--memory` 选择后端（`none` / `mem0` / `viking`），对应环境变量见下方
- 日志系统：基于 Python logging 模块，支持日志等级控制和自动按日期分类的文件输出

## 配置指导（简要）

1) 必填鉴权

-- 推荐方式：使用目录内的 `.env.example` 生成 `.env`，再填写变量。

```bash
cp .env.example .env
```

必填变量：

- `DOUBAO_APP_ID`
- `DOUBAO_ACCESS_KEY`

可选变量：

- `VIKINGDB_AK`
- `VIKINGDB_SK`
- `MEM0_LLM_API_KEY`（仅在 `--memory=mem0` 时需要）

记忆后端与环境变量对应关系：

- `--memory=viking`：需要 `VIKINGDB_AK` / `VIKINGDB_SK`
- `--memory=mem0`：需要 `MEM0_LLM_API_KEY`（`MEM0_GRAPHDB_PASSWD` 仅在你启用 Neo4j/Graph Store 配置时需要）

2) 语音与角色

- 可用发音人：

   - `zh_female_vv_jupiter_bigtts`：对应vv音色，活泼灵动的女声，有很强的分享欲
   - `zh_female_xiaohe_jupiter_bigtts`：对应xiaohe音色，甜美活泼的女声，有明显的台湾口音
   - `zh_male_yunzhou_jupiter_bigtts`：对应yunzhou音色，清爽沉稳的男声
   - `zh_male_xiaotian_jupiter_bigtts`：对应xiaotian音色，清爽磁性的男声

## 安装

```bash
pip install -r requirements.txt
```

## 运行（可组合使用）

参数说明：

- `--mod`：运行模式，`keep_alive`（默认，麦克风输入）或 `text`（纯文本输入）
- `--audio-file`：发送音频文件（WAV）到服务端；设置后会自动切到 `audio_file` 模式
- `--format`：TTS 输出音频格式，`pcm`（默认）或 `pcm_s16le`
- `--memory`：记忆后端，`none`（默认）/ `mem0` / `viking`
- `--aec`：启用 macOS 系统级 AEC（可用时），不可用则自动回退到 PyAudio

麦克风：
   ```bash
   python main.py
   # 或显式指定：python main.py --mod=keep_alive
   ```
文本：
   ```bash
   python main.py --mod=text
   ```
音频文件：
   ```bash
   python main.py --audio-file path/to/input.wav
   ```
启用记忆存储（选择后端）：
   ```bash
   python main.py --memory=viking
   # 或：python main.py --memory=mem0
   ```
启用 AEC（回声消除）：
   ```bash
   python main.py --aec
   ```

## AEC 说明（macOS）

- 当前 `--aec` 仅在 macOS 上启用硬件 VPIO（Voice Processing / AEC），其它平台会自动回退到原来的 PyAudio 录放音路径（为后续跨平台预留接口）。
- AEC 生效的关键是：服务端下发的音频必须从同一个音频引擎播放出来，系统才能做回声参考；本项目在 `--aec` 模式下会把 TTS 音频走 macOS 音频引擎播放。
- macOS 依赖（仅在你需要 `--aec` 时安装）：
   - `pyobjc-framework-AVFoundation`
   - `pyobjc-framework-Cocoa`

排查建议：

- 如果你想先验证系统级 AEC 是否可用，可以运行测试脚本：
   - `python tools/aec_test.py`

安装示例：

```bash
pip install pyobjc-framework-AVFoundation pyobjc-framework-Cocoa
```

## 音频文件输入注意事项

- `--audio-file` 读取 WAV 文件并按块发送，不会自动重采样/变更声道。
- 建议使用与 `input_audio_config` 一致的音频参数（默认：单声道、16kHz、16-bit PCM），否则识别效果或播放可能异常。