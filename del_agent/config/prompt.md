Role: System Architect & Lead Developer 
Task: 根据 req1.md，分阶段生成 Python 代码。 Constraints:
1. 代码必须模块化，大量使用 Type Hinting。
核心逻辑：重点实现 Agent 之间的 Verification Loop (核验循环)，这是保证数据质量的关键。
2. 对于 LLM 调用部分，使用占位符函数 call_llm(prompt, context) 代替实际 API 调用，以便于测试逻辑流。
3. 不要一次性生成所有代码，先从 Step 1 (Schema & Infra) 开始。
4. 请先分析已有的框架，思考如何更改和融合进这个框架中

Role: System Architect & Lead Developer 
Task: 根据 req1.md，分阶段生成 Python 代码。
Constraints:
1. 请先分析已有的框架，思考如何更改和融合进这个框架中，避免直接生成代码，先思考生成一个改动思路。这份代码已经能正常运行，API的配置也已经完全正确。
2. 代码必须模块化，大量使用 Type Hinting。
核心逻辑：重点实现 Agent 之间的 Verification Loop (核验循环)，这是保证数据质量的关键。
3. 把分析结果放到config/del1.md中，这将成为后续行动的参照。在文档中规划分步实现的策略。

