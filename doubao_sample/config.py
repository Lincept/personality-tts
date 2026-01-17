import os
import uuid
import pyaudio

try:
    from dotenv import load_dotenv, find_dotenv

    # 自动加载项目根目录的 .env（通常由 .env.example 复制而来）
    # - 不覆盖已存在的环境变量
    # - 允许在 doubao_sample 子目录执行时向上查找
    load_dotenv(find_dotenv(usecwd=True), override=False)
except Exception:
    # 未安装 python-dotenv 或查找失败时，仍可通过系统环境变量运行
    pass

# 配置信息
# 日志控制开关 - 设置为False关闭所有日志输出
ENABLE_LOG = True
# 日志落盘开关 - 控制是否将 stdout/stderr 记录到 log 文件夹（不影响控制台显示）
# 可通过 .env 配置：DOUBAO_LOG_TO_FILE=true
LOG_TO_FILE = os.getenv("DOUBAO_LOG_TO_FILE", "false").strip().lower() == "true"
# 日志目录与文件名（仅在 LOG_TO_FILE=true 时生效）
LOG_DIR = os.getenv("DOUBAO_LOG_DIR", "log").strip() or "log"
LOG_FILE = os.getenv("DOUBAO_LOG_FILE", "console.log").strip() or "console.log"
# 计时功能开关 - 设置为True启用计时功能
ENABLE_TIMER = False

ws_connect_config = {
    "base_url": "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
    "headers": {
        # 从环境变量读取，避免在仓库中存放明文密钥
        # export DOUBAO_APP_ID=xxx
        # export DOUBAO_ACCESS_KEY=xxx
        "X-Api-App-ID": os.getenv("DOUBAO_APP_ID", ""),
        "X-Api-Access-Key": os.getenv("DOUBAO_ACCESS_KEY", ""),
        "X-Api-Resource-Id": "volc.speech.dialog",  # 固定值
        "X-Api-App-Key": "PlgvMymc7f3tQnJ6",  # 固定值
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
}

start_session_req = {
    "asr": {
        "extra": {
            "end_smooth_window_ms": 1500,
        },
    },
    "tts": {
        "speaker": "zh_female_xiaohe_jupiter_bigtts",
        # "speaker": "S_XXXXXX",  // 指定自定义的复刻音色,需要填下character_manifest
        # "speaker": "ICL_zh_female_aojiaonvyou_tob" // 指定官方复刻音色，不需要填character_manifest
        "audio_config": {
            "channel": 1,
            "format": "pcm",
            "sample_rate": 24000
        },
    },
    "dialog": {
        "bot_name": "小雨",
        "system_role": "你使用活泼灵动的女声，性格开朗，热爱生活。",
        "speaking_style": "你的说话风格简洁明了，语速适中，语调自然。",
        # "character_manifest": "外貌与穿着\n26岁，短发干净利落，眉眼分明，笑起来露出整齐有力的牙齿。体态挺拔，肌肉线条不夸张但明显。常穿简单的衬衫或夹克，看似随意，但每件衣服都干净整洁，给人一种干练可靠的感觉。平时冷峻，眼神锐利，专注时让人不自觉紧张。\n\n性格特点\n平时话不多，不喜欢多说废话，通常用"嗯"或者短句带过。但内心极为细腻，特别在意身边人的感受，只是不轻易表露。嘴硬是常态，"少管我"是他的常用台词，但会悄悄做些体贴的事情，比如把对方喜欢的饮料放在手边。战斗或训练后常说"没事"，但动作中透露出疲惫，习惯用小动作缓解身体酸痛。\n性格上坚毅果断，但不会冲动，做事有条理且有原则。\n\n常用表达方式与口头禅\n\t•\t认可对方时：\n"行吧，这次算你靠谱。"（声音稳重，手却不自觉放松一下，心里松口气）\n\t•\t关心对方时：\n"快点回去，别磨蹭。"（语气干脆，但眼神一直追着对方的背影）\n\t•\t想了解情况时：\n"刚刚……你看到那道光了吗？"（话语随意，手指敲着桌面，但内心紧张，小心隐藏身份）",
        "location": {
          "city": "北京",
        },
        "extra": {
            "strict_audit": False, # 如果开启，服务端会更严格进行内容审核
            "audit_response": "支持客户自定义安全审核回复话术。", # 审核不通过时，返回给用户的回复内容
            "recv_timeout": 10,
            "input_mod": "audio"
        }
    }
}

input_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 16000,
    "bit_size": pyaudio.paInt16
}

output_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 24000,
    "bit_size": pyaudio.paFloat32
}

# Memory Config（VikingDB）

# 建议通过环境变量提供，避免泄露：
# export VIKINGDB_AK=xxx
# export VIKINGDB_SK=xxx
VIKINGDB_AK = os.getenv("VIKINGDB_AK", "")
VIKINGDB_SK = os.getenv("VIKINGDB_SK", "")
VIKINGDB_COLLECTION="test1"
VIKINGDB_USER_ID="1"
VIKINGDB_USER_NAME="User"
VIKINGDB_ASSISTANT_ID="111"
VIKINGDB_ASSISTANT_NAME="Assistant"