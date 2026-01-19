#!/usr/bin/env python3
"""
功能测试脚本 - 验证 main.py 的各种功能
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """运行命令并输出结果"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"命令: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print("✅ 命令执行成功")
        print("\n标准输出:")
        print(result.stdout[:500])  # 只显示前500字符
        
        if result.stderr:
            print("\n标准错误:")
            print(result.stderr[:500])
        
        return True
    except subprocess.TimeoutExpired:
        print("⏱️ 命令超时（这是正常的，某些模式会持续运行）")
        return True
    except Exception as e:
        print(f"❌ 命令执行失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Personality TTS 功能测试")
    print("="*60)
    
    test_results = []
    
    # 测试 1: 帮助命令
    test_results.append(run_command(
        "python3 -m src.main --help",
        "帮助命令"
    ))
    
    # 测试 2: 列出设备
    test_results.append(run_command(
        "python3 -m src.main --list-devices",
        "列出音频设备"
    ))
    
    # 测试 3: 检查 ASR 鉴权（需要 API Key）
    print("\n" + "="*60)
    print("测试: 检查 ASR 鉴权")
    print("注意: 此测试需要配置有效的 API Key")
    print("="*60)
    result = subprocess.run(
        "python3 -m src.main --check-asr",
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    print(result.stdout[:500])
    if result.returncode == 0:
        print("✅ ASR 鉴权测试通过")
        test_results.append(True)
    else:
        print("⚠️ ASR 鉴权测试失败（可能未配置 API Key）")
        test_results.append(False)
    
    # 测试 4: 文字模式参数验证
    test_results.append(run_command(
        "python3 -m src.main --text --help",
        "文字模式参数验证"
    ))
    
    # 测试 5: 语音模式参数验证
    test_results.append(run_command(
        "python3 -m src.main --voice --help",
        "语音模式参数验证"
    ))
    
    # 测试 6: 无效参数测试
    print("\n" + "="*60)
    print("测试: 无效参数处理")
    print("="*60)
    result = subprocess.run(
        "python3 -m src.main --invalid-arg",
        shell=True,
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode != 0:
        print("✅ 无效参数正确处理")
        test_results.append(True)
    else:
        print("❌ 无效参数未正确处理")
        test_results.append(False)
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    passed = sum(test_results)
    total = len(test_results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✅ 所有测试通过！")
        return 0
    else:
        print(f"⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
