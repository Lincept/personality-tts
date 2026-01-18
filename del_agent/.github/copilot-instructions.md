# AI Data Factory - Copilot Instructions

## 🏗️ Architecture Overview

This is a **modular AI agent framework** for processing unstructured text data, built on a three-layer architecture:

### Core Layer (`core/`)
- **BaseAgent**: Abstract base class for all agents with lifecycle management (`process()`, `prepare_input()`, `validate_output()`)
- **LLMProvider**: Unified adapter supporting OpenAI-compatible APIs (DeepSeek, Moonshot, 豆包)
- **PromptManager**: YAML/JSON template loader with Jinja2 variable substitution
- **VerificationLoop** (Phase 1): Implements `Agent Output → Critic Check → Pass/Retry` pattern for quality control

### Data Layer (`models/schemas.py`)
All data models use **Pydantic with strict validation**:
- `CommentCleaningResult`, `RawReview`, `CriticFeedback`, `StructuredKnowledgeNode`
- Every model must have validators for critical fields (see `@validator` decorators)

### Agent Layer (`agents/`)
- **RawCommentCleaner**: Text cleaning agent (removes emotion, extracts facts)
- Agents inherit from `BaseAgent` and implement: `get_output_schema()`, `get_prompt_template_name()`

## 🎯 Critical Development Patterns

### 1. Creating New Agents (Template)
```python
from core.base_agent import BaseAgent
from models.schemas import YourResultModel  # Must be Pydantic BaseModel
from typing import Type

class YourAgent(BaseAgent):
    def get_output_schema(self) -> Type[BaseModel]:
        return YourResultModel
    
    def get_prompt_template_name(self) -> str:
        return "your_template_name"  # Must exist in prompts/templates/
    
    # Optional: Override for custom input processing
    def prepare_input(self, raw_input: Any, **kwargs) -> Dict[str, Any]:
        return {"input_field": raw_input, **kwargs}
```

### 2. Using Verification Loop (Phase 1 Innovation)
```python
# Standard processing (no verification)
result = agent.process(input_data)

# With verification loop (requires critic agent)
result = agent.process_with_verification(
    raw_input=input_data,
    critic_agent=critic_instance,  # Must implement evaluate() or be BaseAgent
    max_retries=3,
    strictness_level=0.7
)

# Access feedback history
print(result.metadata['feedback_history'])  # List[CriticFeedback]
print(result.metadata['verification_stats'])  # Dict with attempts, approval status
```

### 3. Prompt Templates (YAML Required)
Location: `prompts/templates/{name}.yaml`
```yaml
name: agent_name
system_prompt: |
  You are a {role}...
  
user_prompt: |
  Process this: {{ input_field }}
  Context: {{ context }}
```

**Critical**: Template variables MUST match keys in `prepare_input()` return dict.

### 4. Configuration Pattern
- **Environment variables**: Defined in `.env` (git-ignored), read by `utils/config.py`
- **LLM configs**: `config/settings.yaml` → auto-loads env vars for API keys
- **Agent configs**: Also in `settings.yaml` under `agents:` section

```python
from utils.config import get_config_manager
config_manager = get_config_manager()
agent_config = config_manager.get_agent_config("comment_cleaner")
```

## 🚀 Essential Workflows

### Running Tests
```bash
# Simple tests (no pytest dependency)
python tests/test_simple.py

# Phase 1 verification loop tests
python tests/test_verification.py  # Requires pytest

# Demos
python examples/demo.py              # Main demo
python examples/demo_verification.py # Verification loop demo
```

### Adding LLM Provider
1. Get API key → Add to `.env` (e.g., `NEW_PROVIDER_API_KEY=...`)
2. Add config to `config/settings.yaml` under `llm_providers:`
3. Update `utils/config.py` env key mapping in `_parse_config()` (line ~95)

### Project-Specific Commands
```bash
# Quick start script (sets PYTHONPATH correctly)
./run.sh test-config  # Verify config
./run.sh demo        # Run main demo

# Manual execution (from project root)
PYTHONPATH=$(pwd):$PYTHONPATH python del_agent/examples/demo.py
```

## 🧩 Critical Integration Points

### Phase 1 → Phase 2 Handoff
**Completed** (Phase 1): `VerificationLoop`, `BaseAgent.process_with_verification()`, 6 new data models
**Next** (Phase 2): Implement `CriticAgent` in `agents/critic.py` with:
- `evaluate(output: BaseModel, context: Any) -> CriticFeedback` method
- Prompt template: `prompts/templates/critic.yaml`
- See `config/del1.md` for full Phase 2 roadmap

### Data Flow Pattern
```
User Input → prepare_input() → PromptManager.render_messages() 
          → LLMProvider.generate_structured() → Pydantic validation
          → validate_output() → [Optional: VerificationLoop] → Result
```

## 📐 Type Hinting Convention (Enforced)

**100% coverage required**. All functions must have:
```python
def function_name(
    param1: str,
    param2: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Tuple[BaseModel, List[CriticFeedback]]:
```

## 🎨 Code Conventions

1. **Pydantic Models**: Always use `Field()` with description and example
   ```python
   field_name: str = Field(..., description="Purpose", example="sample")
   ```

2. **Logging**: Use class-level logger (initialized in `__init__`)
   ```python
   self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
   ```

3. **Error Handling**: Return error in model's `success=False` + `error_message`, don't raise
   ```python
   return YourResultModel(success=False, error_message=str(e), ...)
   ```

4. **Batch Processing**: Name method `analyze_batch()` or `process_batch()`, return `List[ResultModel]`

## 📚 Key Files for Context

- `config/del1.md`: Full system design (8-phase roadmap, architectural decisions)
- `PHASE1_REPORT.md`: Phase 1 completion status and testing results
- `README.md`: User-facing quickstart and API examples
- `core/base_agent.py`: Agent lifecycle (read first when creating new agents)
- `core/verification.py`: Verification loop implementation (Phase 1 innovation)

## 🔍 Debugging Tips

- Check `metadata` field in results for execution details and feedback history
- Use `agent.get_stats()` for performance metrics
- Enable detailed logging: `VerificationLoop(enable_logging=True)`
- All prompt templates cached; restart if editing YAML files

## ⚠️ Anti-Patterns (Avoid)

1. ❌ Don't modify `core/base_agent.py` `process()` directly → Use `process_with_verification()` instead
2. ❌ Don't hardcode API keys → Always use `.env` + `config/settings.yaml`
3. ❌ Don't create agents without Pydantic output schema → Validation is mandatory
4. ❌ Don't use relative imports in test files → Tests should work standalone (see `tests/test_simple.py` line 17-18)
5. ❌ Don't implement verification logic per-agent → Use `VerificationLoop` (reusable)

## 🎓 Project-Specific Terminology

- **核验循环 (Verification Loop)**: Quality control pattern with automatic retry
- **黑话解码 (Slang Decoding)**: Academic jargon translation (e.g., "学术妲己" → "promises but doesn't deliver")
- **去极化 (De-polarization)**: Removing emotional language while preserving facts
- **权重分析 (Weight Analysis)**: Credibility scoring: `f(IdentityConfidence, TimeDecay, OutlierStatus)`

---

**Current Status**: Phase 1 complete (6/6 tests passing), Phase 2 in planning.
**Target Use Case**: Processing online reviews of academic advisors → structured knowledge base.
