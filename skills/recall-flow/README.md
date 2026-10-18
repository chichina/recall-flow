# 知行卡片学习 Skill v2（本机开发版）

四条工作流：宿主AI整理资料并输出带出处笔记；固定模板生成独立复习目录并自动带入数据；真人网页作答后回传实际记录、宿主评估并生成次日计划；真实APKG/UTF-8 TSV导出。

`knowledge-cards-coach/` 是完整可分发Skill源码。`tests/` 是合成测试，不包含真实用户知识库或学习记录。依赖与运行产物不进入技能包。界面复用用户授权读取的chichina/recall-flow固定提交a9f55d51ed28a6e87a854e1a92db485fd5102bdf，来源与修改记录在references/provenance.json。

## 本地运行

需要Python3.10+、Node20+。不需要npm构建、外部站点、LLM API密钥或Anki桌面安装。

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r '.\knowledge-cards-coach\requirements.txt'
& '.\.venv\Scripts\python.exe' -X utf8 '.\knowledge-cards-coach\scripts\coach.py' init --workspace '..\v2-demo\我的学习库'
& '.\.venv\Scripts\python.exe' -X utf8 '.\knowledge-cards-coach\scripts\coach.py' ingest --workspace '..\v2-demo\我的学习库' --file '.\knowledge-cards-coach\examples\source.md'
& '.\.venv\Scripts\python.exe' -X utf8 '.\knowledge-cards-coach\scripts\coach.py' ingest --workspace '..\v2-demo\我的学习库' --file '.\knowledge-cards-coach\examples\source.png'
& '.\.venv\Scripts\python.exe' -X utf8 '.\knowledge-cards-coach\scripts\coach.py' ingest --workspace '..\v2-demo\我的学习库' --file '.\knowledge-cards-coach\examples\source.pdf'
& '.\.venv\Scripts\python.exe' -X utf8 '.\knowledge-cards-coach\scripts\coach.py' notes --workspace '..\v2-demo\我的学习库' --file '.\knowledge-cards-coach\examples\synthetic-pack.json'
& '.\.venv\Scripts\python.exe' -X utf8 '.\knowledge-cards-coach\scripts\coach.py' build-review --workspace '..\v2-demo\我的学习库'
```

学习包中的知识摘要、问题与rubric由宿主AI整理。脚本不会OCR，也不会语义判分。示例图片文本已由本轮宿主模型视觉核读，仅证明该合成样例，不代表真实扫描件OCR评测。开放题先显示待评估；结束后只有本机保存成功才显示成功，否则保留浏览器记录并提供session导出。

## 验证

完整测试环境可额外安装requirements-dev.txt；其中Anki仅为Python/Rust导入后端，不安装桌面应用。浏览器测试使用独立临时上下文，测试我们生成的127.0.0.1页面，不操作用户果办窗口，也不是用户桌面截图。

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-dev.txt
& '.\.venv\Scripts\python.exe' -X utf8 tests/test_workflow.py
& '.\.venv\Scripts\python.exe' -X utf8 tests/test_web.py
node tests/test_core.mjs
```

实际结果与限制见TEST_REPORT.md。果办已由用户确认登录；当前会话没有原生窗口控制接口，未声称已在果办创建/导入/实测。不会因UI缺口停下本机开发，不修改果办安全配置、不读凭据、不发布技能市场；按用户最新明确授权将源码交付GitHub，最终验收由用户自己的客户端Codex完成。比赛开放提交日期按用户给出的10月20日执行，10月18日仅准备。
