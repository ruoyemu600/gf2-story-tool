# 卡住的问题(现象 + 已试方案)

## B1 KittyCafe / Kittycafe2 —— ✅ 已解决(P1 注册表匹配,2026-11-09)
正文行表就是同族的 `KittyCafeContentData` / `Kittycafe2ContentData`
(f2=对话组,f4=说话人,f5=台词,f6 为副本),两代共 +1459 行已接入。
以下原始记录保留作背景:

### 原始记录
- `KittyCafeDialogueData` 13 条,f9=101248 等数字,**不是语言包 id**(lang 无此键);
  `KittyCafeContentByDialogueIdData` 的 f2 是 packed varint(解出 10110101 等 9 位数),
  同样不在语言包 id 集。
- 已试:f9 直查 lang(0/13);f2 packed 直查 lang;按 ×100/×1000 拆位(不试,禁止拆位)。
- 怀疑:正文挂在 `EsCellData`/`TpsshootMissionData` 一类引用表,或这两个 9 位数是
  另一 id 空间。**留给 T9 破译归属时一起处理。**

## B2 LoveAvg / CharacterAvg —— ❌ 正文未通(2026-11-09 P1 后)
P1 结果:ByGunId 的 f2 整值 100% 命中 `LoveAvgData`/`CharacterAvgData`(均为标题/解锁索引表,
标题在 f5,如「形影不离」「狐狸尾巴1」),以及 `AvgPlotData`(f1 子集)。
正文仍不在任何已知行表;`AvgPlotData` 的 txtName 对应的演出正文链路未通。

### 原始记录
- `LoveAvgData`/`CharacterAvgData` 是**解锁条件表**(f4/f8 是"升级至20解锁"类文本),
  f5 是道具 id,不是正文。
- `LoveAvgByGunIdData`/`CharacterAvgByGunIdData` 只有 f1(枪 id)+ f2 packed,
  packed 解出的值不在语言包。
- 已试:packed 直查 lang;f1 拆位(不试,禁止拆位)。

## B3 ChessStory —— ❌ 正文未通(2026-11-09)
P1 结果:ChessStory.f3 → `ChessStoryByGroupData` 100%;其 f2 packed 的 796 个"内容 id"
→ `ChessStageData`(f9/f10 为坐标串,棋局地图),**无文本字段**。
棋局正文另有归属(类似关卡→台词的链),未定位。

### 原始记录
- `ChessStoryData` 796 条:f2 是代号("NC-2-10"),f3=101122(段表引用?),pre/next 链完整。
- `ChessStoryByGroupData` 未 probe 完;f3 指向的表未定位。
- 下一步:probe ChessStoryByGroupData,按 f3 值全表反查(注意 id 空间重叠误报)。

## B4 LobbyGunStory —— ❌ 正文未通(2026-11-09)
P1 结果:ByGunId.f2 整值 100% 命中 `Avg3DPlotData`(274/272)——宿舍剧情属于 3D 演出系统;
但 `Avg3DPlotData`(1497 条,txtName 如 M01101)与 `Avg3dContentData` 组(305203…)
的映射仍缺,正文未接。

### 原始记录
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

## B8 P3 wiki 反查不可行(2026-11-09)
- gf2.wiki / exilium.wiki:不可达(DNS/网络)。
- gf2.huijiwiki.com:403(反爬)。
- wiki.biligame.com/gf2:可达,但 MediaWiki 搜索「剧情」仅 9 条,
  且最相关页是 2021 年"一测首航测试"内容(与现代 8 章版本不符),无章节台词页。
- gamekee:首页为 JS 外壳,无静态正文可抓。
**结论**:P3 判据(每章 3 句独有长句)无法建立;等有可用 wiki 源或社区数据再重启。

## B9 序对位验证失败(2026-11-09 v2.2 ①)
**假设**:Avg3DPlotData(1497)与演出组(1474)按 id 升序一一对应。
**判据1(角色交集)**:前 20 对,plot.f5 角色名在组内文本/说话人出现率
平均 **3.9%**(15 对有效),远低于 50% 阈值。
**判据2(章节隔离)**:M 类 txtName 仅 5 条(M006xx/M007xx),M08 类 0 条,
隔离实验无法成立;已查的 5 对无第 8 章角色交叉(0/5,但样本无效)。
**判据3(首尾校准)**:首对(plot 1010101→组 0)与末三对(plot 2076030x→组 180010x)
均无可判角色,无校准依据。
**结论**:两条表不构成可排序的平行序列;按 v2.2 规则收手,
不再尝试第三种排序。附带观察:plot.f5 有 68 个角色名,但组内文本几乎不提角色名
(3.9%),暗示 Avg3dContent 的组可能不是 Avg3DPlot 的文本行(或是另一类内容)。

## B10 棋局无台词判定(2026-11-09 v2.2 ②)
ChessStoryByGroupData.f2 的 796 个内容 id:
- 对 Avg3dContent **组 id 集**命中 49/796 = 6.2%(小数字巧合,如 99801/99901)
- 对 Avg3dContent **行 id 集**命中 0/796 = 0.0%
判定:棋局为纯战棋玩法,**无剧情台词**;ChessStageData 的坐标数据与
ChessStoryData 的代号(pre/next)不需要接入成书。B3 关闭(无内容可提取)。

## B11 资源索引链彻底查空(2026-11-09 APK+catalog 轮)
**新证据(用户导出 APK + 热更目录三件套)**:

1. **APK 内 catalog**(`assets/AssetBundles_Android/catalog_main_9889.bin`,13MB):
   5,555 个 bundle 哈希名 + 395 个 Assets 路径;6 个热更样本哈希**全不在**——
   是安装时的初始版本。
2. **热更目录 `Version_CopyAsset.txt`**(1.28MB):当前版本**完整文件清单**,
   9,777 bundle + 4,324 .gf,格式 `{0}/<hash>.bundle#<MD5>#<大小>#<版本>`;
   6 个样本全部命中(版本 26419/27079,与 GameConfig 的
   CacheResVersion 4.0.5143.9889.28656 对齐)。**只有哈希,无资源名。**
3. **热更目录 `catalog_main_28656.bin`**(58MB,与 CacheResVersion 版本号一致):
   43,679 个 bundle 名、833 个 Assets 路径(全为 Scene/玩法资源);
   **剧情资源名(M01101 类)零出现**,Avg/avg/avg_ 全 0。
4. **Table 全表搜 6 个样本哈希:0 处**;搜 32 位 hex 字符串字段:0 处。
5. `Version_Ex1.bin`(207KB):无任何可打印资源名(加密/压缩)。

**结论**:GF2 使用自研资源加载系统。剧情 bundle 按资源名(M01101 等)在运行时加载,
「资源名→bundle 哈希」的索引**不在 APK、不在 catalog、不在 CopyAsset、不在 Table**——
只可能在 IL2CPP 代码逻辑中或服务端。手机端此路终点。
**残余可能**:对 9,777 个 bundle 做内容抽样(解包看 TextAsset m_Name),
但即使命中,全量定位仍需处理 44GB——手机端不可行,**不再尝试**。
**PC 端仍是唯一解**:全量解包 44GB 后按 TextAsset 名索引。

## B12 剧本通道终极确认(2026-11-09 APK+DLL+全量扫描,手机端终点)
**在本轮取得的全部新证据**:

1. **剧本引擎 = Utage ADV**(Assembly-CSharp.dll 内完整:AdvEngine/AdvScenarioPlayer/
   AdvScenarioThread/AdvScenarioData)。
2. **剧本路径**:`Assets/Utage/BuildResources/NewAVG_MainStory/CN_ChapterXX.xls`
   (主线)、`MainStory/ChapterXX`、`Activity/ChapterXX`——Utage 的 xls 剧本源。
3. **剧本下载器**:`Utage.WWWEx.LoadFromCacheOrDownloadAssetBundleAsync` ——
   剧本以 AssetBundle 形式从服务器下载,缓存在 **Unity 的 Cache(Android 上为
   /data/data/<包名>/cache/UnityCache,应用私有目录)**。
4. **`.gf` = ZIP 包**(PK 头);清单 4,899 个 .gf 对应各类资源包;
   已下载的 5 个是过场视频(TIME_Chapter_03_*.usm)。
5. **44GB 全量/抽样扫描**(解密后搜 Utage 路径/ScenarioData/中文):
   - 100–500KB:2,942 个全扫 → 关卡场景/Spine,0 剧本
   - 0.5–2MB:3,876 个全扫 → 场景/角色模型,4 个命中全是表情标签
   - 2–10MB:1,738 个全扫 → 角色模型/UI/粒子;61 个含剧本路径引用
     (角色包引用剧本地址),零剧本本体
   - >10MB:抽样 5 → 动画剪辑
6. **catalog(58MB)/CopyAsset/Table** 均无剧本 Key(CN_Chapter/MainStory 0 处)。
7. **现场抓取失败**:剧情播放时剧本只进内存与私有 UnityCache,外置目录零落盘
   (播放期间新一轮 AOT 产物出现,证明进程在跑)。

**结论(手机端终点,不可再推进)**:
剧本 AssetBundle 只存在于私有 UnityCache / 服务端。无 root、无 PC 条件下
无法取得。**解锁条件**:① root(读 UnityCache);② PC 客户端 + 全量解包;
③ 等社区剧本文本数据源。
