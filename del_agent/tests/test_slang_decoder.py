"""
Phase 2.2 - SlangDecoderAgent 单元测试

测试黑话解码智能体的所有核心功能：
1. 初始化和词典加载
2. 黑话识别和解码
3. 词典动态更新
4. 批量处理
5. 词典持久化
6. 搜索和统计功能

作者：AI Data Factory
创建日期：2026-01-19
"""

import sys
import os
from pathlib import Path
import json
import tempfile

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.slang_decoder import SlangDecoderAgent
from models.schemas import SlangDecodingResult


class MockLLMProvider:
    """Mock LLM Provider for testing"""
    
    def generate_structured(self, messages, response_model=None, **kwargs):
        """模拟 LLM 的结构化输出"""
        # response_model 参数设为可选，默认为 SlangDecodingResult
        if response_model is None:
            response_model = SlangDecodingResult
        
        # 从 messages 中提取用户输入
        user_message = None
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 模拟黑话识别逻辑
        text = user_message if user_message else ""
        
        slang_patterns = {
            "学术妲己": "善于承诺但不兑现的导师",
            "画饼": "做出承诺但不实现",
            "学术黑厂": "工作环境恶劣、压榨学生的实验室",
            "鸽子王": "经常爽约、不守信用的人",
            "PPT吹得天花乱坠": "宣传时夸大其词",
            "放养": "导师很少指导学生",
            "内卷": "过度竞争导致效率低下"
        }
        
        # 识别文本中的黑话
        identified_slang = {}
        decoded_text = text
        
        for slang, meaning in slang_patterns.items():
            if slang in text:
                identified_slang[slang] = meaning
                decoded_text = decoded_text.replace(slang, meaning)
        
        # 如果没有识别到黑话，返回原文
        if not identified_slang:
            decoded_text = text
            confidence = 0.6
        else:
            confidence = 0.9
        
        return SlangDecodingResult(
            decoded_text=decoded_text,
            slang_dictionary=identified_slang,
            confidence_score=confidence,
            success=True
        )


def test_initialization():
    """测试1：初始化和词典加载"""
    print("\n" + "="*70)
    print("测试1：SlangDecoderAgent 初始化")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    
    # 无词典初始化
    decoder = SlangDecoderAgent(llm_provider)
    assert len(decoder.slang_dictionary) == 0
    print("✓ 无词典初始化成功")
    
    # 使用临时词典文件初始化
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.json',
        delete=False,
        encoding='utf-8'
    ) as f:
        initial_dict = {
            "学术妲己": "善于承诺但不兑现的导师",
            "画饼": "做出承诺但不实现"
        }
        json.dump(initial_dict, f, ensure_ascii=False)
        temp_path = Path(f.name)
    
    try:
        decoder_with_dict = SlangDecoderAgent(
            llm_provider,
            slang_dict_path=temp_path
        )
        assert len(decoder_with_dict.slang_dictionary) == 2
        assert "学术妲己" in decoder_with_dict.slang_dictionary
        print(f"✓ 从文件加载词典成功 ({len(decoder_with_dict.slang_dictionary)} 个术语)")
    finally:
        temp_path.unlink()
    
    print("✅ 测试1通过！")
    return True


def test_decode_slang():
    """测试2：黑话识别和解码"""
    print("\n" + "="*70)
    print("测试2：黑话识别和解码")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    # 场景1：包含多个黑话的文本
    text1 = "这个导师是学术妲己，总是画饼，实验室就是学术黑厂"
    result1 = decoder.process(text1)
    
    print(f"\n输入文本: {text1}")
    print(f"解码结果: {result1.decoded_text}")
    print(f"识别黑话: {list(result1.slang_dictionary.keys())}")
    print(f"置信度: {result1.confidence_score}")
    
    assert result1.success
    assert len(result1.slang_dictionary) > 0
    assert result1.decoded_text != text1  # 应该有变化
    print("✓ 场景1：多黑话文本解码成功")
    
    # 场景2：无黑话的普通文本
    text2 = "导师很好，经费充足，指导认真"
    result2 = decoder.process(text2)
    
    print(f"\n输入文本: {text2}")
    print(f"解码结果: {result2.decoded_text}")
    print(f"识别黑话: {list(result2.slang_dictionary.keys())}")
    
    assert result2.success
    print("✓ 场景2：普通文本处理成功")
    
    print("✅ 测试2通过！")
    return True


def test_update_dictionary():
    """测试3：词典动态更新"""
    print("\n" + "="*70)
    print("测试3：词典动态更新")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    initial_count = len(decoder.slang_dictionary)
    print(f"初始词典大小: {initial_count}")
    
    # 添加新术语
    new_terms = {
        "鸽子王": "经常爽约、不守信用的人",
        "放养": "导师很少指导学生"
    }
    
    updated_count = decoder.update_dictionary(new_terms)
    print(f"更新了 {updated_count} 个术语")
    print(f"当前词典大小: {len(decoder.slang_dictionary)}")
    
    assert len(decoder.slang_dictionary) >= initial_count + 2
    assert "鸽子王" in decoder.slang_dictionary
    assert "放养" in decoder.slang_dictionary
    print("✓ 词典更新成功")
    
    # 更新已有术语
    override_terms = {"鸽子王": "经常不守约定的导师"}
    decoder.update_dictionary(override_terms)
    assert decoder.slang_dictionary["鸽子王"] == "经常不守约定的导师"
    print("✓ 术语覆盖更新成功")
    
    print("✅ 测试3通过！")
    return True


def test_validate_output():
    """测试4：输出验证"""
    print("\n" + "="*70)
    print("测试4：输出验证")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    # 有效输出
    valid_output = SlangDecodingResult(
        decoded_text="导师善于承诺但不兑现",
        slang_dictionary={"学术妲己": "善于承诺但不兑现的导师"},
        confidence_score=0.9
    )
    assert decoder.validate_output(valid_output) is True
    print("✓ 有效输出验证通过")
    
    # 空文本
    invalid_output = SlangDecodingResult(
        decoded_text="",
        slang_dictionary={},
        confidence_score=0.5
    )
    assert decoder.validate_output(invalid_output) is False
    print("✓ 空文本正确拒绝")
    
    # 无效置信度
    try:
        invalid_confidence = SlangDecodingResult(
            decoded_text="测试",
            slang_dictionary={},
            confidence_score=1.5
        )
        print("❌ 应该拒绝无效置信度")
        return False
    except Exception:
        print("✓ 无效置信度正确拒绝")
    
    print("✅ 测试4通过！")
    return True


def test_batch_decode():
    """测试5：批量解码"""
    print("\n" + "="*70)
    print("测试5：批量解码")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    texts = [
        "这个导师是学术妲己",
        "实验室内卷严重",
        "导师经常放养学生",
        "经费充足，环境良好"
    ]
    
    results = decoder.decode_batch(texts)
    
    print(f"批量处理 {len(texts)} 条文本")
    print(f"成功处理: {sum(1 for r in results if r.success)}/{len(results)}")
    
    for i, result in enumerate(results, 1):
        status = "✅" if result.success else "❌"
        slang_count = len(result.slang_dictionary)
        print(f"  {status} 文本{i}: 识别 {slang_count} 个黑话")
    
    assert len(results) == len(texts)
    assert all(r.success for r in results)
    
    print("✅ 测试5通过！")
    return True


def test_dictionary_persistence():
    """测试6：词典持久化"""
    print("\n" + "="*70)
    print("测试6：词典持久化")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    
    # 创建临时文件
    temp_file = Path(tempfile.gettempdir()) / "test_slang_dict.json"
    
    try:
        # 第一个实例：创建并保存词典
        decoder1 = SlangDecoderAgent(
            llm_provider,
            slang_dict_path=temp_file,
            auto_save=True
        )
        
        decoder1.update_dictionary({
            "学术妲己": "善于承诺但不兑现的导师",
            "画饼": "做出承诺但不实现"
        })
        
        dict_size_1 = len(decoder1.slang_dictionary)
        print(f"✓ 第一个实例保存词典: {dict_size_1} 个术语")
        
        # 第二个实例：加载保存的词典
        decoder2 = SlangDecoderAgent(
            llm_provider,
            slang_dict_path=temp_file
        )
        
        dict_size_2 = len(decoder2.slang_dictionary)
        print(f"✓ 第二个实例加载词典: {dict_size_2} 个术语")
        
        assert dict_size_1 == dict_size_2
        assert decoder2.slang_dictionary == decoder1.slang_dictionary
        print("✓ 词典持久化成功")
        
    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()
    
    print("✅ 测试6通过！")
    return True


def test_search_and_stats():
    """测试7：搜索和统计功能"""
    print("\n" + "="*70)
    print("测试7：搜索和统计功能")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    # 添加测试数据
    decoder.update_dictionary({
        "学术妲己": "善于承诺但不兑现的导师",
        "画饼": "做出承诺但不实现",
        "学术黑厂": "工作环境恶劣的实验室",
        "放养": "导师很少指导"
    })
    
    # 统计信息
    stats = decoder.get_dictionary_stats()
    print(f"\n词典统计:")
    print(f"  - 总术语数: {stats['total_terms']}")
    print(f"  - 自动保存: {stats['auto_save_enabled']}")
    print(f"  - 示例术语: {list(stats['sample_terms'].keys())}")
    
    assert stats['total_terms'] == 4
    print("✓ 统计信息正确")
    
    # 搜索功能
    search_results = decoder.search_slang("学术")
    print(f"\n搜索 '学术' 的结果: {len(search_results)} 条")
    for slang, meaning in search_results.items():
        print(f"  - {slang}: {meaning}")
    
    assert len(search_results) >= 2  # "学术妲己" 和 "学术黑厂"
    print("✓ 搜索功能正常")
    
    print("✅ 测试7通过！")
    return True


def test_prepare_input():
    """测试8：输入数据准备"""
    print("\n" + "="*70)
    print("测试8：输入数据准备")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    # 添加一些已知黑话
    decoder.update_dictionary({
        "学术妲己": "善于承诺但不兑现的导师",
        "画饼": "做出承诺但不实现"
    })
    
    # 准备输入
    raw_text = "这个导师总是画饼"
    prepared = decoder.prepare_input(raw_text)
    
    print(f"原始输入: {raw_text}")
    print(f"准备后的数据键: {list(prepared.keys())}")
    print(f"词典大小: {prepared['dictionary_size']}")
    
    assert "text" in prepared
    assert "existing_dictionary" in prepared
    assert "dictionary_size" in prepared
    assert prepared["dictionary_size"] == 2
    
    print("✓ 输入数据准备正确")
    print("✅ 测试8通过！")
    return True


def test_clear_dictionary():
    """测试9：清空词典"""
    print("\n" + "="*70)
    print("测试9：清空词典")
    print("="*70)
    
    llm_provider = MockLLMProvider()
    decoder = SlangDecoderAgent(llm_provider, auto_save=False)
    
    # 添加数据
    decoder.update_dictionary({
        "学术妲己": "善于承诺但不兑现的导师",
        "画饼": "做出承诺但不实现"
    })
    
    print(f"清空前: {len(decoder.slang_dictionary)} 个术语")
    
    # 清空
    decoder.clear_dictionary()
    
    print(f"清空后: {len(decoder.slang_dictionary)} 个术语")
    
    assert len(decoder.slang_dictionary) == 0
    print("✓ 词典清空成功")
    
    print("✅ 测试9通过！")
    return True


def run_all_tests():
    """运行所有测试"""
    print("="*70)
    print("Phase 2.2 - SlangDecoderAgent 单元测试")
    print("="*70)
    
    tests = [
        test_initialization,
        test_decode_slang,
        test_update_dictionary,
        test_validate_output,
        test_batch_decode,
        test_dictionary_persistence,
        test_search_and_stats,
        test_prepare_input,
        test_clear_dictionary
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ 测试失败: {test_func.__name__}")
            print(f"   错误: {e}")
        except Exception as e:
            failed += 1
            print(f"❌ 测试失败: {test_func.__name__}")
            print(f"   错误:")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Phase 2.2 SlangDecoderAgent 实现成功！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要修复")


if __name__ == "__main__":
    run_all_tests()
