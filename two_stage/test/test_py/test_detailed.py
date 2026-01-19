#!/usr/bin/env python3
"""
详细功能测试脚本 - 验证 main.py 的各种功能和边界情况
"""
import subprocess
import sys
import os
import json


class TestResult:
    """测试结果类"""
    def __init__(self, name, passed, details="", output=""):
        self.name = name
        self.passed = passed
        self.details = details
        self.output = output


def run_command_with_timeout(cmd, timeout=5):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -2, "", str(e)


def test_help_command():
    """测试 1: 帮助命令"""
    returncode, stdout, stderr = run_command_with_timeout("python3 -m src.main --help")
    
    if returncode == 0:
        # 检查关键信息是否存在
        checks = [
            "Personality TTS" in stdout,
            "--text" in stdout,
            "--voice" in stdout,
            "--list-devices" in stdout,
            "--check-asr" in stdout,
            "--role" in stdout
        ]
        
        if all(checks):
            return TestResult(
                "帮助命令",
                True,
                "所有关键参数都显示",
                stdout[:300]
            )
        else:
            return TestResult(
                "帮助命令",
                False,
                "缺少某些关键参数",
                stdout[:300]
            )
    else:
        return TestResult(
            "帮助命令",
            False,
            f"返回码: {returncode}",
            stderr[:200]
        )


def test_list_devices():
    """测试 2: 列出音频设备"""
    returncode, stdout, stderr = run_command_with_timeout("python3 -m src.main --list-devices")
    
    if returncode == 0:
        # 检查输出格式
        checks = [
            "可用的音频输入设备" in stdout,
            "设备" in stdout,
            "输入通道数" in stdout,
            "采样率" in stdout
        ]
        
        if all(checks):
            return TestResult(
                "列出音频设备",
                True,
                "输出格式正确",
                stdout[:400]
            )
        else:
            return TestResult(
                "列出音频设备",
                False,
                "输出格式不正确",
                stdout[:400]
            )
    else:
        return TestResult(
            "列出音频设备",
            False,
            f"返回码: {returncode}",
            stderr[:200]
        )


def test_check_asr():
    """测试 3: 检查 ASR 鉴权"""
    returncode, stdout, stderr = run_command_with_timeout("python3 -m src.main --check-asr")
    
    # 检查是否显示了脱敏的 API Key
    if "DashScope Key:" in stdout:
        if returncode == 0:
            return TestResult(
                "检查 ASR 鉴权",
                True,
                "鉴权成功",
                stdout[:300]
            )
        else:
            # 可能是 API Key 未配置或网络问题
            return TestResult(
                "检查 ASR 鉴权",
                False,
                "鉴权失败（可能未配置 API Key）",
                stdout[:300]
            )
    else:
        return TestResult(
            "检查 ASR 鉴权",
            False,
            "未显示 API Key 信息",
            stdout[:300]
        )


def test_text_mode_help():
    """测试 4: 文字模式帮助"""
    returncode, stdout, stderr = run_command_with_timeout("python3 -m src.main --text --help")
    
    if returncode == 0:
        return TestResult(
            "文字模式帮助",
            True,
            "参数解析正确",
            stdout[:300]
        )
    else:
        return TestResult(
            "文字模式帮助",
            False,
            f"返回码: {returncode}",
            stderr[:200]
        )


def test_voice_mode_help():
    """测试 5: 语音模式帮助"""
    returncode, stdout, stderr = run_command_with_timeout("python3 -m src.main --voice --help")
    
    if returncode == 0:
        return TestResult(
            "语音模式帮助",
            True,
            "参数解析正确",
            stdout[:300]
        )
    else:
        return TestResult(
            "语音模式帮助",
            False,
            f"返回码: {returncode}",
            stderr[:200]
        )


def test_invalid_argument():
    """测试 6: 无效参数"""
    returncode, stdout, stderr = run_command_with_timeout("python3 -m src.main --invalid-arg")
    
    if returncode != 0:
        return TestResult(
            "无效参数处理",
            True,
            "正确拒绝无效参数",
            stderr[:200]
        )
    else:
        return TestResult(
            "无效参数处理",
            False,
            "未正确拒绝无效参数",
            stdout[:200]
        )


def test_role_parameter():
    """测试 7: 角色参数"""
    returncode, stdout, stderr = run_command_with_timeout(
        "python3 -m src.main --role natural --help"
    )
    
    if returncode == 0:
        return TestResult(
            "角色参数",
            True,
            "角色参数解析正确",
            stdout[:300]
        )
    else:
        return TestResult(
            "角色参数",
            False,
            f"返回码: {returncode}",
            stderr[:200]
        )


def test_asr_model_parameter():
    """测试 8: ASR 模型参数"""
    returncode, stdout, stderr = run_command_with_timeout(
        "python3 -m src.main --asr-model paraformer-realtime-v2 --help"
    )
    
    if returncode == 0:
        return TestResult(
            "ASR 模型参数",
            True,
            "ASR 模型参数解析正确",
            stdout[:300]
        )
    else:
        return TestResult(
            "ASR 模型参数",
            False,
            f"返回码: {returncode}",
            stderr[:200]
        )


def test_mutually_exclusive_modes():
    """测试 9: 互斥模式"""
    returncode, stdout, stderr = run_command_with_timeout(
        "python3 -m src.main --text --voice"
    )
    
    if returncode != 0:
        return TestResult(
            "互斥模式",
            True,
            "正确拒绝同时使用 --text 和 --voice",
            stderr[:200]
        )
    else:
        return TestResult(
            "互斥模式",
            False,
            "未正确处理互斥模式",
            stdout[:200]
        )


def test_module_import():
    """测试 10: 模块导入"""
    try:
        result = subprocess.run(
            "python3 -c \"from src.main import VoiceInteractiveMode, LLMTTSTest; print('Import successful')\"",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and "Import successful" in result.stdout:
            return TestResult(
                "模块导入",
                True,
                "所有类导入成功",
                result.stdout
            )
        else:
            return TestResult(
                "模块导入",
                False,
                "导入失败",
                result.stderr[:200]
            )
    except Exception as e:
        return TestResult(
            "模块导入",
            False,
            str(e),
            ""
        )


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("Personality TTS 详细功能测试")
    print("="*70)
    
    tests = [
        test_help_command,
        test_list_devices,
        test_check_asr,
        test_text_mode_help,
        test_voice_mode_help,
        test_invalid_argument,
        test_role_parameter,
        test_asr_model_parameter,
        test_mutually_exclusive_modes,
        test_module_import
    ]
    
    results = []
    
    for i, test_func in enumerate(tests, 1):
        print(f"\n[{i}/{len(tests)}] 运行测试: {test_func.__doc__}")
        result = test_func()
        results.append(result)
        
        status = "✅ 通过" if result.passed else "❌ 失败"
        print(f"  状态: {status}")
        if result.details:
            print(f"  详情: {result.details}")
        if result.output:
            print(f"  输出: {result.output}")
    
    # 生成总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    # 失败的测试
    failed_tests = [r for r in results if not r.passed]
    if failed_tests:
        print("\n失败的测试:")
        for test in failed_tests:
            print(f"  - {test.name}: {test.details}")
    
    # 保存结果到 JSON
    result_data = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": f"{passed/total*100:.1f}%",
        "tests": [
            {
                "name": r.name,
                "passed": r.passed,
                "details": r.details
            }
            for r in results
        ]
    }
    
    result_file = "test/doc/test_results.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试结果已保存到: {result_file}")
    
    # 返回退出码
    if passed == total:
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
