# 评审决议:v2.1 执行计划(2026-11-09)

> 评审输入:docs/issues.md + docs/plan-v2.md 执行状态。
> 结论:B1-B4 大概率是同一个问题;A2 有纯本地解;GitHub 立即推。

## 执行序列(替代原优先级)

### P1 全表 f1 注册表匹配(5 分钟,一箭四雕)——最高优先

1. 遍历 Table/ 全部 *.bytes,建注册表:每张表的 f1 id 全集,标注表名;
   (Avg3dContentData 的行 id 是消息 f1,同规则;GuildwarStoryParagraphData 同)
2. 对下列"悬空引用"逐一做**整数值精确匹配**(in 集合,禁止拆位/前缀):
   - B1: KittyCafeContentByDialogueIdData.f2 packed 解出的值(如 10110101)
   - B1: KittyCafeDialogueData.f9(如 101248)
   - B2: LoveAvgByGunIdData.f2 packed 值 / CharacterAvgByGunIdData.f2 packed 值
   - B3: ChessStoryData.f3(如 101122)
   - B4: LobbyGunStoryByGunIdData.f2 packed 值
3. 判据:命中率 >80% 的表 = 持有正文的行表;0 命中才走 EsCellData 备选
   (备选判据:EsCell 的文本字段 lang 命中率)。
4. 预期:大概率命中 Avg3dContentData 或 DialoguePage 的 id 集
   (咖啡厅/好感/个人剧情是立绘演出,与主线共用 AVG 系统没理由另开行表)。
   注意位宽:10110101 是 8 位,Avg3dContent 是 9 位——整值不中再试组号语义(仅限
   命中表已确认的前提下,做"packed 值 = 该表某行 id"的整值验证)。
5. 副产品:若 ByGunId 表给出 角色→组 映射,直接喂给 A2(匿名组消掉一大半),
   并给 B5(角色中文名)提供 Gun→名字 的线索。

### P2 B1-B4 收尾(依赖 P1 结果)

- 命中行表 → 照 DialoguePage 模式接入四族 → 验收:每族报行数 + 抽 3 组人工读;
- 未命中 → probe ChessStoryByGroupData / EsCellData 各 15 分钟,仍无果记 blocked.md。

### P3 A2-wiki 反查(不等 PC,纯本地+网络)

1. 取社区 wiki(gf2.wiki 类)主线 8 章(双摆推演~叠影效应)各 3 句独有长句(>15 字);
2. 在本地语料做子串搜索,命中的组标注章节归属;
3. 说话人:wiki 行(说话人+行文本)→ 匹配本地行 → 回填 speaker;
4. **红线:wiki 文本只用于归属标注与说话人推断,一个字不进语料**;
5. 判据:每章 3 句命中唯一组为成功;一章多组按 wiki 顺序排组内卷序。
6. 先跑第 1 章验证方法,通了再铺开。

### P4 GitHub 立即推(D1)

- 工作完成度 90%,负结果(blocked.md/issues.md)本身就是开源价值;
- blocked.md/issues.md 确认已入 git(评审时未见提交记录);
- 推送步骤已备(bundle 在 /sdcard/Download/gf2-story-tool.bundle)。

### P5 数据版本快照(最紧急的合规缺口,随 P4 一起做)

- 找 Table 目录/同级目录的 version/resversion 文件,记录提取日期+游戏版本进
  README + out/report.json;
- README 写明"结构支持多语言,B服数据仅中文"(其他语言表是空壳);
- report.json 加各家族行数基准值(数据级回归闸门,防 Table 换版本静默漂移)。

### P6 长线(等用户配合,不阻塞)

- **A**:让用户导出 GF2 APK(vivo 文件管理器:应用详情→分享安装包)→
  解 zip 取 assets/bin/Data/Managed/Metadata/global-metadata.dat →
  提取字符串 → 过滤 avg/story/dialog/.bundle 名 → 算 MD5(不确定:可能是
  fnv1a/自定义,用 6 个样本 bundle 各试三种,都不中即放弃,成本封顶半天)→
  命中 ≥2/6 则按名定位 44GB 中的少量 bundle,T9/T10 解锁。
- **B**:USM 字幕(C3):1.8GB 视频的字幕轨是正经正文,复刻 exilium-tools 的
  USM 解析(Segment 头+字幕段,格式公开);独立于 bundle 问题。
- **B5 一句话**:在含 Gun/Character 名字的表里找 name 的 lang 引用,5 分钟。

## 否决记录(勿执行)

- "游戏内文本快照比对"(截屏+OCR):工程量与收益完全不成比例,否决;
- 任何形式的 id 拆位猜测:维持 B7 禁令;
- 全量扫 44GB:维持禁令,P6-A 的按名取件是替代方案。
