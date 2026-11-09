# 卡住的问题(现象 + 已试方案)

## B1 KittyCafe / Kittycafe2 正文链未闭合(T1 遗留)
- `KittyCafeDialogueData` 13 条,f9=101248 等数字,**不是语言包 id**(lang 无此键);
  `KittyCafeContentByDialogueIdData` 的 f2 是 packed varint(解出 10110101 等 9 位数),
  同样不在语言包 id 集。
- 已试:f9 直查 lang(0/13);f2 packed 直查 lang;按 ×100/×1000 拆位(不试,禁止拆位)。
- 怀疑:正文挂在 `EsCellData`/`TpsshootMissionData` 一类引用表,或这两个 9 位数是
  另一 id 空间。**留给 T9 破译归属时一起处理。**

## B2 LoveAvg / CharacterAvg 正文位置不明(T1 遗留)
- `LoveAvgData`/`CharacterAvgData` 是**解锁条件表**(f4/f8 是"升级至20解锁"类文本),
  f5 是道具 id,不是正文。
- `LoveAvgByGunIdData`/`CharacterAvgByGunIdData` 只有 f1(枪 id)+ f2 packed,
  packed 解出的值不在语言包。
- 已试:packed 直查 lang;f1 拆位(不试,禁止拆位)。

## B3 ChessStory 正文位置不明(T1 遗留)
- `ChessStoryData` 796 条:f2 是代号("NC-2-10"),f3=101122(段表引用?),pre/next 链完整。
- `ChessStoryByGroupData` 未 probe 完;f3 指向的表未定位。
- 下一步:probe ChessStoryByGroupData,按 f3 值全表反查(注意 id 空间重叠误报)。

## B4 LobbyGunStory 正文位置不明(T1 遗留)
- `LobbyGunStoryData` 是**目录表**:f4=标题("赞美的艺术·Ⅰ")、f5=pre 链,
  正文在 `LobbyGunStoryByGunIdData`(未 probe)。
- 下一步:probe LobbyGunStoryByGunIdData 的 f2 packed 是否指向 lang(同 B2 症状)。

## B5 副官对话说话人是资源名(T1 降级)
- AdjutantConversationData 的动画名 `c_Charolic_idle_to_apathy` → 抽到 "Charolic",
  是英文资源名不是中文名。映射表(枪 id → 中文名)未定位。
- 影响:仅显示观感,数据正确。

## B6 EsAvgPlot / FitnessgameAvg / CharacterVoice(T1 遗留)
- EsAvgPlotData:f2/f3 是 `AA01115…` 资源名,无文本字段。
- FitnessgameAvgData 仅 2 条,f3 是标题("L12343")——太小,不够成书。
- CharacterVoiceData 是语音触发矩阵(voice id),无文本。

## B7 T9/T10 依赖的剧本配置不在可达范围(T9/T10 阻塞,已穷尽本地手段)
**目标**:演出组(305203…)↔章节/关卡的映射 + 逐句说话人。

**已穷尽的尝试(2026-11-09)**:
1. Table 全表扫描「字段值=已知角色名」→ 只有 DialoguePageData 自身(宿舍)命中,
   无主线说话人表。
2. Avg3DPlotData(1497 条, txtName 为 M03003 格式)、AvgData 与演出组前缀
   (100101/305203…)全字段比对 → 零命中,映射不在 Table。
3. AssetBundles_Android:6 个样本 bundle 全部为美术(Texture2D/Mesh/Shader);
   文件名是内容哈希,**内部 AssetBundle m_Name 也是哈希**(de5fc524…bundle)。
4. Addressables catalog:LocalCache/Data 下无 catalog 文件 —— 清单在服务端/APK 内。
5. 社区无公开带说话人剧情数据源(GitHub 搜索:工具类为主)。

**结论**:剧本配置(逐句 speaker + 组归属)只存在于加密 bundle 中,
定位它需要 catalog(PC 客户端可获得)或全量扫描 44GB(手机端不可行)。

**后续可行路径(需要 PC 环境)**:
- PC 版客户端(国际服)的 catalog 在安装目录,拿到后可精确列出 avg_*.bundle 并只搬那几个
- 或 PC 上跑 GF2AssetBundleDecryption + 全量解包(44GB 在 PC 上可接受)
- USM 字幕提取(exilium-tools 的 subtitle_extractor)只能覆盖 20 个过场视频,覆盖面小
