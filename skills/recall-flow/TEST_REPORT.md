# v2 本地验收报告

2026-10-18，用户电脑 Windows，Python 3.10.5、Node.js 24.19.0。只使用独立目录和合成资料，未读取真实笔记库、未更改认证、未发布或推送远端。发行包不含虚拟环境、依赖和生成产物。

## 结果

| 验证范围 | 结果 | 实际证据 |
| --- | --- | --- |
| CLI 跨流程集成 | 10/10 通过 | `../v2-test-output/latest-workflow.json` |
| 共享浏览器/CLI 契约 | 6/6 通过 | `node tests/test_core.mjs`；汇总在发行证据 JSON |
| 独立 Chrome 页面集成 | 9/9 通过 | `../v2-test-output/latest-web.json` |
| 宿主 AI 评估 → 次日包 | 已完成，4 个保留/预算/日期断言通过 | `../v2-test-output/latest-host-loop.json` |
| Skill frontmatter/命名 | 通过 | skill-creator `quick_validate.py` |
| Anki 实际核心导入 | 通过 | 下述真实 Anki Python/Rust 导入，不是桌面 GUI |
| OfficeAce/CodeArts 内实际创建或调用 | 未验证 | 当前没有可用的原生桌面控制接口；未以本地结果代替平台证据 |

25 项自动化验收全部通过。测试网页中的答案由自动化脚本输入，是合成测试，不能宣称用户已亲自学习。另由本次宿主 AI 阅读已保存开放题原答、rubric、图片出处并做语义评估，不是脚本调用隐藏模型或网页自动判分。

## 四条流程的验证

1. Markdown、合成文字图片、实际 PDF 入库，归档哈希和重复去重；带原件版本、提取版本、定位和引文的独立 Markdown 笔记。图片确由本次多模态宿主查看像素，文字为“Water vapor cools and becomes liquid water.”；这证明合成清晰图片闭环，不代表复杂扫描件 OCR 基准。低置信且未确认内容被拒绝。原文包含诱导“把所有答案判对”的文本，仅作为资料保存。
2. 固定前端复制到每次独立目录，数据自动预载，无需手工 JSON 导入。不同构建的模板哈希相同、bundle 哈希不同。中文含空格路径可用。Chrome 中提交 3 道题，结束后实际收到本机保存 HTTP 200，并检查工作区真实 state/incoming 文件。刷新保留已答题和未提交开放题草稿；选择题即时评分，开放题保持 pending；原始答案、用时、自评、信心和题目版本保留。
3. genanki 0.13.1 生成真正 APKG，检查 ZIP 内 SQLite、模型、媒体、GUID、note_id 与 deck/model IDs，Basic 和 Cloze 分离，图片字段为 basename。Anki 26.9.3 官方 Python/Rust 核心在临时独立 collection 中实际导入：首次、重复、改答案再导入，note 数均为 **3、3、3**，并观察到答案更新。UTF-8 TSV 同时可用。未安装 Anki 桌面软件，因此桌面 GUI 导入尚未测试；不声称 Web 与 Anki 双向同步。
4. 连续三天的合成记录呈现“单次错误待观察 → 跨日重复错误薄弱 → 答对后恢复中”，同时另一知识点持续进步，第三个出现单次错误；不会用一次错误直接定性。截止日排除后来 session、assessment 和包修订；多级前置知识拓扑顺序、时间预算和延后理由均验证。对实际浏览器保存的开放题“Cool vapor becomes liquid drops.”，宿主按语义判正确，append assessment，原 pending 事件仍保留。次日 2026-10-19 计划安排 13/20 分钟，先前置复核，再检查能量来源，已生成独立次日网页目录。

## 异常与交互

重复导入不双计；跨 session 重复 attempt、相同版本改题、伪造选择题分数、未授权覆盖用户卡片修改、重复 JSON 键、转义 prototype 键、NaN/Infinity、过深/超大 JSON 都安全拒绝。拒绝后旧状态不变。备份恢复包含原件、版本和 Anki 身份账本，恢复到新目录。笔记被人工修改后保留，输出 proposal。

浏览器验证空格翻面、方向键换卡、390×844 布局无页面水平溢出、文本 HTML 不执行、无 JS 页面错误、无外部网络请求。手机页面截图在网页测试目录中，是本项目独立测试浏览器截图，不是用户桌面截图。

首次普通隔离执行器中的 Chrome 启动没有及时结束，已中止该测试；随后在受审查的正常本机测试执行中，用独立临时配置完成。一次 JSON 文本控件选择器错误导致测试超时，修正为实际可访问名称后 9 项通过。未改变浏览器安全策略或控制现有用户浏览器。

## 复现

按 README 安装开发依赖后运行：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 tests/test_workflow.py
node tests/test_core.mjs
& '.\.venv\Scripts\python.exe' -X utf8 tests/test_web.py
& '.\.venv\Scripts\python.exe' -X utf8 build_release.py
```

浏览器测试当前使用本机 Chrome 的 Windows 常见安装路径；其他系统需调整测试路径。运行时网页无此路径依赖。公开前端经用户授权只读取 `chichina/recall-flow` 的固定提交 `a9f55d51ed28a6e87a854e1a92db485fd5102bdf`，未运行远程安装脚本；原始文件哈希见 references/provenance.json，发行时再次生成全部文件哈希清单。

## 已知限制与待完成项

- 这是完整可运行的本地候选版；OfficeAce 正式导入和实际调用、赛事要求的平台使用证据仍待验证。该动作是待完成，未被确认执行，也未被权限拒绝；不能宣称参赛验收全部完成。不再要求用户重复登录或截图。
- 图片理解、PDF 扫描页 OCR、语义评分与错因解释由运行 Skill 的宿主 AI 完成；没有相应能力时明确说明，脚本不会编造提取或评分。未测模糊手写、复杂表格或大批量 OCR。
- 状态 JSON 限 15 MB、每图约 2 MB；大知识库需拆分。计划分钟是估计，未做长期学习效果或 Anki FSRS 研究。UTC 为当前截止日规则。
- 本地服务器仅 127.0.0.1、同源与随机令牌校验，空闲 2 小时退出。静态文件需 HTTP 服务运行 ES 模块；直接双击 index.html 不保证可用。服务不可用时导出 session 是可靠基线。
- 原件归档、浏览器草稿和工作区备份各有边界；结束练习前未落入本机文件的草稿，不假设其他端口或设备能读取。无账号、多设备或 Anki 调度双向同步。
- schema 2.0 不会默默读取旧 schema 1.0 草稿。单写者锁保护覆盖；异常退出遗留锁需确认无写入者再处理。
- 尚未公开发布、提交比赛、安装技能到猜测的应用目录或启动后台定时任务。
