#!/bin/bash
# Del Agent 快速启动脚本

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 检查 .env 文件
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  .env 文件不存在"
    echo "正在从 env.example 创建 .env 文件..."
    cp "$SCRIPT_DIR/env.example" "$SCRIPT_DIR/.env"
    echo "✓ 已创建 .env 文件"
    echo ""
    echo "请编辑 $SCRIPT_DIR/.env 文件，填写你的 API 密钥"
    echo "然后重新运行此脚本"
    exit 1
fi

# 运行参数处理
case "${1:-demo}" in
    test-config)
        echo "=== 运行配置测试 ==="
        python "$SCRIPT_DIR/examples/test_config.py"
        ;;
    demo)
        echo "=== 运行演示脚本 ==="
        python "$SCRIPT_DIR/examples/demo.py"
        ;;
    *)
        echo "用法: $0 [demo|test-config]"
        echo ""
        echo "  demo         - 运行完整演示（默认）"
        echo "  test-config  - 测试配置是否正确"
        exit 1
        ;;
esac
