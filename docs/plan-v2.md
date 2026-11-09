# gf2-story-tool v2 任务计划(交接版)

> 本文档自包含:接手者不需要之前的会话记录。
> 代码在 `/data/user/0/cc.codroid/files/home/workspace/gf2/`,
> 数据在 `/sdcard/Download/gf2-dump/Table/`(125MB,只读,别改)。
> 运行环境:手机端 Python 3.14,无第三方依赖(protobuf 是手写 wire 解析器)。

## 零、已确立的事实(接手前必读,别重新踩坑)

1. **Table 格式**:`.bytes` 文件 = 4 字节小端 uint32(跳过长度)+ protobuf 消息体。
   解析入口:`gf2_table.py` 的 `read_table()` / `parse_fields()`。
2. **语言包**:`LangPackageTableCnData.bytes` 51.8 万条 id→中文文本,
   `load_lang()` 已封装。**其他语言表是 8 字节空壳**(B服只有中文)。
3. **表的角色定位(已验证)**:
   - `Avg3dContentData` = 演出正文 21966 行(id = 组号×1000+序,组内 id 升序=阅读序)
   - `DialoguePageData` = 宿舍/档案对话 2366 页(f3=说话人 f4=头像,自包含)
   - `GuildwarStoryData → GuildwarStoryParagraphData` = 公会战剧情链
   - `AvgContentData` 17.5 万条 = **系统文本池(公告/邮件/成就/UI),不是剧情**,已排除
4. **已踩过的坑(不要重试)**:
   - 台词 id 的 6 位前缀归属:猜过 DialogueGroup×100、AvgData/AvgPlot 拆位、
     StageGrid、StageConfig×1000、ChapterData×100 —— **全部错误**。
     id 空间在各表间大量重叠,单靠数值匹配必然误报。
   - `StageConfigData.f9-f13` 的 packed 数组指向 StageEnemy/StageEvent 的 id,
     **不是台词引用**。战前台词(若存在)走别的链,别再从这五个字段下手。
   - `Dimbreath/GFL2Data`(GitHub)是 2021 年的远古 dump,内容与当前 B服表差异巨大,
     不要拿它当 schema 参考。
5. **说话人现状**:文本内嵌格式只有 4.9%(两种:`<color=..>名:</color>文` 和裸 `名:文`,
   `gf2_extract.py` 的 `clean_text()` 都已处理)。其余说话人在演出配置层,
   需 AssetBundles(见任务 T9/T10)。
6. **排版原则(不可违背)**:无说话人的行按旁白缩进,**不许猜说话人**;
   `{}` 占位符原样保留;名单类组过滤规则在 `gf2_books.py` 的 `is_roster()`。

## 一、任务清单

### T1 支线家族批量接入 ★☆☆(体量最大,纯劳动力,给 ds)

把以下表族接入 `gf2_extract.py` + `gf2_books.py`,每族照抄 DialoguePage 的实现模式
(`flat_records` → `lang_ref` → `clean_text` → 按 f1 或组聚段 → corpus 家族 → 成卷):

| 家族 | 表 | 备注 |
|---|---|---|
| 咖啡厅 | KittyCafeDialogueData / KittyCafeContentByDialogueIdData / Kittycafe2 系 | 先 probe 字段再写 |
| 宿舍闲聊 | LobbyDialogueData(24KB) | |
| 宿舍剧情 | LobbyGunStoryData(26KB)/LobbyGunStoryByGunIdData | 按枪(角色)分组 |
| 好感剧情 | LoveAvgData(14KB)/LoveAvgByGunIdData | |
| 个人剧情 | CharacterAvgData(f3=角色id)/CharacterAvgByGunIdData | |
| 棋局剧情 | ChessStoryData(标题 f2=lang)→ f3 指向段表 | 段表叫什么要 probe |
| 副官对话 | AdjutantConversationData(9.9KB) | |
| 暗区对话 | DarkzoneDialogueData(258B,很小) | |
| 行为对话 | BehaviorDialogData / DialogueGroupData / DialogNodeData / DialogTreeData | 树形,可能要遍历 |
| 角色语音 | CharacterVoiceData(13.7KB) | 有触发场景标签 |
| 健身房 | FitnessgameAvgData | 极小,顺手 |

**验收**:每族报告条数;抽 3 组人工读,语义连贯;不出现名单混入(复用 `is_roster`)。
**禁止**:对组号做任何拆位猜测(见坑 4)。

### T2 清洗与过滤加强 ★☆☆

- 富文本:统计 `<sprite...>`、嵌套标签、`\n` 段内换行的出现率,补 `TAG_RE`;
- `{}`/`{0}` 占位符:统计出现率,输出清单到 `out/placeholders.tsv`(不替换,只记录);
- 组内噪音行:全是"……"/单个语气词的行,连续 5 行以上才整组标疑;
- `is_roster()` 阈值 0.8 用新数据复测,不准就调并写注释说明依据。

**验收**:清洗前后 diff 样本 20 条放 `docs/cleaning-diff.md`;总行数变化 < 3%(防止误杀)。

### T3 测试套件 ★☆☆(照抄 limbus-story-tool 的模式)

`tests/test_gf2.py`:不依赖游戏数据的纯构造样例——
- `clean_text` 两种说话人格式/无说话人/嵌套标签/空串
- `read_table` 长度头跳过(构造 protobuf 字节)
- `is_roster` 名单/正文判别
- `group_title` 短首行跳过(limbus 踩过"第 3 节·袮"的坑)
- EPUB:mimetype 首位不压缩、nav 存在(用 zipfile 断言)
- 跑法 `python3 tests/test_gf2.py`,0 fail 才许提交

### T4 EPUB 封面 ★☆☆(模板已验证)

复用 `/data/user/0/cc.codroid/files/home/workspace/limbus-story-tool/volumize.py` 的
封面生成链(SVG → rsvg-convert → magick JPEG q88),改三处:
- 底色换 GF2 军械风(暗底 + 铜金/军绿点缀,参考游戏 UI 的暗棕+黄铜)
- kicker 文案:`MAIN STORY`/`DORMITORY`/`GUILD WAR`/家族名
- 页脚:`少女前线2:追放 · 卷名 · N 节`
先出 3 张样图放 `docs/cover-samples/`,等确认再全量。
注意 `.nomedia`(防相册污染)——limbus 已实现,直接抄。

### T5 卷册命名改进 ★★☆

组名现在用首行摘要(18 字),改进启发式:首个说话人 + 首个非寒暄句;
同卷内组名去重(现在是"…(2)"式堆叠)。验收:抽查 10 卷,无重名、无寒暄标题("嗯。""……")。

### T6 系统文本池二次分拣 ★★☆

`AvgContentData` 17.5 万条虽是系统池,但**活动邮件里有叙事正文**
(如"新装采购"公告那种长文,以及剧情活动信件)。筛法:长度>200 且含叙事特征
(引号对话/"指挥官"称谓/段落结构),按发件人/lang id 区间聚类成"邮件集"卷。
这是阅读价值判断,做完给我看样本再入书。

### T7 公会战链复查 ★★☆(我留的疑点)

现在 102 篇只有 235 行(平均 2.3 行/篇),太少。复查:
- `GuildwarStoryParagraphData` 的文本字段是否真是 f2/f3(probe 前 10 条看 lang 命中率);
- f6 packed 段落引用是否漏段(packed 解析对不对);
- 篇均行数应该 >10 才合理,否则继续查链路上是不是还有一层表。

### T8 主线骨架预置 ★★☆

把 ChapterData(296 章章名)+ StoryData(1669 关,pre/next 拓扑序)输出成
`out/outline.json`(章 → 有序关卡列表,关卡名 lang 解析)。T9 破译归属后直接 join。
拓扑排序函数 `stage_order()` 已在 git 历史里(v1 版 gf2_extract.py 的旧提交),翻出来用。

### T9 组↔章节归属破译 ★★★(留给 kanha,ds 别碰)

需要 AssetBundles(用户还没搬,几 GB)或 lua 热更脚本。
演出配置里应有 组号→章节/关卡/角色的映射,拿到后回填 corpus。
**依赖:用户搬出 AssetBundles 文件夹**。

### T10 说话人补全 ★★★(留给 kanha)

演出层配置(AVG 剧本 TextAsset)含逐句 speaker/GunId。
依赖:AssetBundles 解密(工具:nijinekoyo/GF2AssetBundleDecryption 的 XOR 逻辑,
密钥在其 Go 源码里已公开,Python 十行可复刻;UnityPy 已装好 1.25.4)。

## 二、工作流约定(ds 接手必读)

1. **只改** `~/workspace/gf2/` 下代码;`/sdcard/Download/gf2-dump/Table/` 只读;
2. 每任务一提交,信息格式 `T1: 咖啡厅/宿舍家族接入(+行数)`,
   结尾加 `Co-Authored-By: Claude Code <noreply@anthropic.com>`;
3. 提交前跑 `python3 tests/test_gf2.py`(T3 完成前至少手动跑全管线不崩);
4. 产物不入库(.gitignore 已拦 out/ 和 *.jsonl,发现新的产物文件要补规则);
5. 卡住 30 分钟以上的,写进 `docs/blocked.md` 跳过,不要瞎猜——
   本项目的教训就是"猜 id 编码"全错,宁可标 blocked。
6. 难度 ★★★ 的两个任务不要动,等 AssetBundles 到位。

## 三、完成后的整体状态(v2 出口)

- 语料:演出 2.2 万行 + 支线家族(T1 全接入,预计 +3~5 万行)+ 邮件集(T6)
- 书:约 250-300 卷,带封面,说话人覆盖 4.9%→(T10 后 90%+)
- 结构:outline.json 章节骨架 + 归属 join(T9 后主线精确挂章)
- 测试:全绿;然后与 limbus-story-tool 同流程开源(bundle→GitHub)

## 四、执行状态(2026-11-09)

| 任务 | 状态 | 结果 |
|---|---|---|
| T3 测试套件 | ✅ 完成 | 16 组断言 0 fail;修 {} 误判说话人、寒暄组标题 |
| T1 支线家族 | ✅ 完成(部分) | 接入 5 族 +649 行;5 族文本链未闭合记 blocked.md(B1-B6) |
| T2 清洗加强 | ✅ 完成 | 标签仅 color/size;placeholders.tsv + 20 条 diff;roster 命中 1/1474 |
| T4 封面 | ⏸ 样图完成,等确认 | docs/cover-samples/ 3 张;全量接入待确认 |
| T5 卷内去重 | ✅ 完成 | 88 处重名 -> 0 |
| T7 公会战复查 | ✅ 完成 | 109 段为纯演出视频(f4=Assets 路径),输出占位行;235->344 行 |
| T8 主线骨架 | ✅ 完成 | out/outline.json:296 章 / 1669 关拓扑序 |
| T6 文本池分拣 | ⏸ 样本完成,等确认 | >=120 字 63 条,叙事候选 26 条 -> out/email_candidates.tsv |
| T9 归属破译 | ⛔ 阻塞(见 blocked.md B7) | Table 内无映射;catalog 不在客户端;bundle 双哈希 |
| T10 说话人补全 | ⛔ 阻塞(见 blocked.md B7) | 主线无说话人表;剧本配置仅在 44GB bundle 内 |
