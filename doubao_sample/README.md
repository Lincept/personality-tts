# RealtimeDialog

实时语音对话程序，支持语音输入和语音输出。

## 使用说明

此demo使用python3.7环境进行开发调试，其他python版本可能会有兼容性问题，需要自己尝试解决。

1. 配置API密钥
   - 打开 `config.py` 文件
   - 修改以下两个字段：
     ```python
     "X-Api-App-ID": "火山控制台上端到端大模型对应的App ID",
     "X-Api-Access-Key": "火山控制台上端到端大模型对应的Access Key",
     ```
   - 修改speaker字段指定发音人，本次支持四个发音人：
     - `zh_female_vv_jupiter_bigtts`：中文vv女声
     - `zh_female_xiaohe_jupiter_bigtts`：中文xiaohe女声
     - `zh_male_yunzhou_jupiter_bigtts`：中文云洲男声
     - `zh_male_xiaotian_jupiter_bigtts`：中文小天男声

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   
3. 通过麦克风运行程序
   ```bash
   python main.py --format=pcm
   ```
4. 通过录音文件启动程序
   ```bash
   python main.py --audio=whoareyou.wav
   ```
5. 通过纯文本输入和程序交互
   ```bash
   python main.py --mod=text --recv_timeout=120
   ```

## 接入 Viking 长期记忆（可选）

该 demo 支持在每轮 ASR 结束后，从 Viking 记忆库检索相关历史记忆，并通过 `external_rag` 注入对话上下文；同时在会话结束时，会把本次对话（尽力收集到的 user/assistant 文本）写入记忆库。

前置条件（参考火山引擎文档）：

1. 开通 Viking 长期记忆，并在控制台创建记忆库（拿到 `collection_name`）
2. 设置记忆库鉴权 AK/SK 到环境变量：
   - `VOLC_ACCESSKEY`
   - `VOLC_SECRETKEY`

启用方式：

1. 修改 `config.py` 中的以下配置：
   - `MEMORY_ENABLE = True`
   - `MEMORY_COLLECTION_NAME = "你的collection_name"`
   - `MEMORY_USER_ID` / `MEMORY_ASSISTANT_ID`（至少填一个）
   - `MEMORY_TYPES`（可选，填事件规则里定义的 memory_type）
   - `MEMORY_LIMIT`（默认 3）
2. 运行：
   直接在 `config.py` 里填写：
   - `MEMORY_AK` / `MEMORY_SK`

   ```bash
   # 也可以通过环境变量提供 AK/SK
   export VOLC_ACCESSKEY=xxxx
   export VOLC_SECRETKEY=yyyy
   python main.py --format=pcm
   ```

实现说明：
- 记忆检索/归档逻辑都在 `memory_client.py` 中（包含 Viking API 调用封装）。
- demo 会在每轮 ASR 结束后检索记忆并通过 `external_rag` 注入；会话结束后归档本次对话到记忆库。

注意：
- 首次写入后索引构建可能需要 3–5 分钟，期间检索可能返回“索引构建中”的错误码，demo 会跳过该轮记忆注入。