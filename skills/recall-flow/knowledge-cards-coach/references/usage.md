# Windows 安装与运行

技能目录可在任意中文路径。Node.js20+与Python3.10+可用后，依赖环境放在技能目录之外；无需修改PowerShell执行策略：

```powershell
python -m venv C:\学习资料\coach-env
& 'C:\学习资料\coach-env\Scripts\python.exe' -m pip install -r '<技能目录>\requirements.txt'
& 'C:\学习资料\coach-env\Scripts\python.exe' -X utf8 '<技能目录>\scripts\coach.py' init --workspace 'C:\学习资料\独立知识库'
```

命令执行器的参数应按数组传入，避免把资料内容拼入shell。下列示例中的`python`表示已安装依赖的解释器；CLI建议显式`-X utf8`，尤其是中文控制台。

## 合成示例

```powershell
python -X utf8 scripts/coach.py ingest --workspace '<新工作区>' --file examples/source.md
python -X utf8 scripts/coach.py ingest --workspace '<新工作区>' --file examples/source.png
python -X utf8 scripts/coach.py ingest --workspace '<新工作区>' --file examples/source.pdf
python -X utf8 scripts/coach.py notes --workspace '<新工作区>' --file examples/synthetic-pack.json
python -X utf8 scripts/coach.py build-review --workspace '<新工作区>'
```

原件、笔记、学习状态、独立reviews目录和导出产物均在新工作区。浏览器自动带入数据。固定资源没有每次生成；可对比各build-report的template_sha256，数据变化单独体现为bundle_sha256。

`--no-open`只构建并启动服务，不请求打开默认浏览器。`--no-serve --no-open`仅生成独立静态目录；可用任意本地静态HTTP服务查看，但需导出session，不应期待自动写本机文件。

本地保存服务仅绑定127.0.0.1，校验Origin、Host和本次随机令牌，接受schema校验过的session/backup。令牌是本次运行生成的本地写入防护，不是外部API密钥。网页结束练习或保存修订时回传；成功后写state和incoming。服务故障不会伪称文件已保存，页面保留浏览器记录并提示导出。

服务空闲2小时自动退出；这是当前复习的HTTP服务，不是定时复习任务。手动停止：

```powershell
python -X utf8 scripts/coach.py stop-review --workspace '<工作区>' --file '<本次reviews目录>'
```

## 总结、次日包与Anki

```powershell
python -X utf8 scripts/coach.py review --workspace '<工作区>' --as-of 2026-10-18 --minutes 20
# 宿主读host-assessment-request，写真实语义评估后：
python -X utf8 scripts/coach.py review --workspace '<工作区>' --assessment '<assessment.json>' --as-of 2026-10-18 --minutes 20
python -X utf8 scripts/coach.py build-review --workspace '<工作区>'
python -X utf8 scripts/coach.py export-anki --workspace '<工作区>' --out '<不存在的新导出目录>'
python -X utf8 scripts/coach.py backup --workspace '<工作区>' --out '<backup.json>'
python -X utf8 scripts/coach.py restore --workspace '<新的恢复目录>' --file '<backup.json>'
```

APKG已含模型与媒体；Basic/Cloze分别建模，UID在首字段，GUID不含答案。TSV更新须使用匹配的自定义note type，以UID首字段匹配；APKG可先创建模型。媒体在media目录，Anki字段用`<img src="basename.png">`。导出不写Anki用户配置，不导入Web调度；实际学习调度由Anki自己处理。

## 限制与来源

当前合同为v2，旧schema1.0需显式迁移；不自动把旧稿当完整新版。状态单写者，遇state.lock拒绝并发覆盖；崩溃残留锁需确认无写入者后处理。JSON15MB、单图约2MB；规模更大应分库。时间为估计分钟，不能保证实际用时。脚本不做独立LLM调用、OCR或未经证据的错因诊断。

固定前端来源与修改记录见provenance.json。Anki参考：
https://docs.ankiweb.net/manual/importing/text-files
https://docs.ankiweb.net/manual/importing/packaged-decks
https://docs.ankiweb.net/manual/exporting
https://github.com/kerrickstaley/genanki

果办集成需通过正式Skill目录/导入功能；当前仅本地脚本和测试得到验证。不修改果办安全设置、不注入应用、不打开远程调试、不读取登录凭据。用户已确认登录无需重复要求；不发布市场或推送远端。
