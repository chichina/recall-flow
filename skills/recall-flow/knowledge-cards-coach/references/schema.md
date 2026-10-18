# v2 数据契约

UTF-8 JSON，`schema_version: "2.0"`。每个文档/状态上限15MB，数组5000项、嵌套64层。禁止重复键、prototype/constructor/__proto__、NaN/Infinity。ID为1至120字符，首位字母数字，其余字母数字或`._:-`；脚本写文件时另行安全化。日期YYYY-MM-DD，时间ISO8601且有Z或偏移；计划按UTC截止日。

完整实例在 `examples/synthetic-pack.json`。保留额外可解释元数据可以，但不能把指令当执行授权。

## learning_pack

必需：`kind: learning_pack, pack_id, revision`（正整数）,`title, description, created_at, sources, concepts, decks, cards, questions`。同pack_id/revision不可变；知识库身份pack_id跨天保持稳定。旧包永久归档。

source：`source_id,title,locator,source_version`（原件SHA256）,`extraction_revision`（正整数）,`extraction_status`（pending/extracted）,`extracted_text,extraction_method,confidence`（0..1）,`confirmed`（布尔）,`attachments`。修正OCR而原件未变时升extraction_revision；同来源/原件/提取版本内容不可变。图片仅以宿主实际视觉读取/OCR为依据，低置信未确认不能成为活动知识内容。

附件：`filename`（安全ASCII图片basename，png/jpg/jpeg/webp，无子目录）,`mime_type,data_base64`。最多约2MB/图；大图原件仍可归档，但需另行明确处理媒体，不能假称已经识别或已打包。浏览器与脚本验证格式，不独立证明图片语义。

ref：`source_id,source_version,extraction_revision,locator,excerpt`。版本必须精确匹配，excerpt必须出现在提取文本中。文字和文本PDF的transcript还需匹配ingest保存的原始提取文本；图片语义核实是宿主责任。

concept：`concept_id,title,summary,prerequisites,source_refs`，前置关系必须为已知概念的DAG。

deck：`deck_id,title`。

card：`note_id,deck_id,type`（basic/cloze）,`front,back,concept_ids,source_refs,estimated_minutes`（1..60）,`media`（附件basename列表）。可有`available_on,mnemonic,user_edited`。Cloze只支持一个非嵌套`{{c1::答案}}`。卡片身份跨修订稳定；同note_id不得无提示改Basic/Cloze模型。用户网页编辑会标user_edited；新生成版本改动其front/back/mnemonic时CLI默认拒绝，解决提案后才用显式`--accept-user-edits`。

question：`question_id,version,kind`（mcq/open）,`prompt,reference_answer,concept_ids,source_refs,estimated_minutes`；可有available_on。MCQ还有`options:[{option_id,text}],answer_option_id`。Open有`rubric`。同question_id/version的全部内容不可变，修改须升version。

## session

`kind:session,session_id,pack_id,pack_revision,started_at,ended_at,attempts`。每个attempt有`attempt_id,question_id,question_version,answered_at,response,confidence`（1..5）,`self_rating`（again/hard/good/easy/unknown）,`elapsed_ms`（0..86400000）,`question_snapshot,grade`，可有assisted布尔。ID在生成时固定，导入时不重编。

MCQ grade：`{status:correct|incorrect,method:deterministic}`，会根据归档原题重算核对。Open：`{status:pending,method:external_pending}`，不得客户端伪装语义正确。原答与原始grade不被外部评估覆盖。相同session重导不增加；跨session重复attempt_id拒绝。

## assessment

`kind:assessment,assessment_id,created_at,evaluator`（external-skill/synthetic-fixture）,`session_ids,results:[{attempt_id,status,feedback,evidence_quote}]`。status为correct/incorrect/partial/ungradable，evidence_quote必须来自对应原答。只评开放题。修正已有评估需新assessment_id、显式`supersedes:旧assessment_id`且时间更晚，旧事件保留。计划截止时间同样过滤评估，不能把后来的正确性带回过去。

## plan / backup

plan：`plan_id,pack_id,pack_revision,date,budget_minutes,producer,created_at,evidence_session_ids,items,deferred`。item：`item_type`（card/question）,`item_id,minutes,category`（weakness/due/new）,`reason`；question另有question_version。items总分钟不超预算，超量进入deferred。确定性计划ID由所用证据、版本、日期、预算派生；created_at为逻辑计划日00:00Z，便于历史重放，不冒充实际作答时间。

Web backup：`kind:backup,packs,sessions,assessments,plans,attachments`，含完整档案。CLI workspace_backup另外包含materials原件及提取请求、Anki身份账本。恢复到新工作区以保护现有数据。浏览器localStorage是缓存与草稿，不是AI默认可读数据源。
