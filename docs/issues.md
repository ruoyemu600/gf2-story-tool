# gf2-story-tool 问题清单(供外部评审)

> 项目:《少女前线2:追放》(B服)剧情文本提取管线,纯手机端(Python 3.14,Termux 环境)。
> 代码:`/data/user/0/cc.codroid/files/home/workspace/gf2/`
> 数据:`/sdcard/Download/gf2-dump/Table/`(125MB 静态表)、`/sdcard/Download/gf2-dump/`(6 个样本 bundle)、`/sdcard/Download/gf2-dump/Mobile/`(1.8GB 视频)、44GB AssetBundles(仅手机上,未搬运)
> 本文档目的:请评审判定问题优先级、评估 B 级问题的挖掘路径、检查 A 级是否还有未尝试的思路。

---

## 一、项目已完成的部分(背景)

- Table 解析:`.bytes` = 4 字节小端长度头 + protobuf(手写 wire 解析器,非官方 schema)
- 语言包 51.8 万条中文文本全量解开
- 演出对白 21,966 行(Avg3dContentData,id=组号×1000+序)
- 宿舍对话 2,366 页(DialoguePageData,自带说话人 f3+头像 f4)
- 公会战 102 篇 344 行(GuildwarStoryData→ParagraphData,f6 packed 段落引用)
- 支线 5 族 649 行(大厅/副官/休息室/互动/暗区)
- 信件/报道 36 篇 199 段(AvgContentData 中 ≥120 字+叙事特征)
- 成书 222 卷 EPUB3(浅色简约封面,cover-image 声明完整)
- 测试 tests/test_gf2.py 16 组断言全绿

## 二、问题的分级框架

- A 级:影响阅读质量的结构性缺口(归属/说话人)
- B 级:家族文本链未闭合(数据在,接不上)
- C 级:观感瑕疵
- D 级:交付流程

---

## A 级问题

### A1 逐句说话人缺失(覆盖率 4.9%)

**症状**:主线演出对白 21,966 行中只有 1,079 行文本内嵌说话人
(`<color=#..>名:</color>文` 或裸 `名:文` 两种格式),其余 95% 是纯对白,
成书按旁白缩进输出(不猜说话人)。

**证据**:
- 全表扫描「字段值 = 已知角色名文本」:只有 DialoguePageData(宿舍)命中,
  主线无任何表含逐句说话人。
- Avg3dContentData 行结构只有 f1(id)/f2/f3(同文本双份),无 speaker 字段。
- 说话人大概率在演出配置(AssetBundles 内的 AVG 剧本)里。

### A2 组↔章节归属未接

**症状**:演出对白按「组」组织(组号如 305203/100101,1474 组),
组→章节/关卡的映射未知。成书只能按组号前 3 位聚卷,
卷名是「演出剧情 100(组100-293)」这种匿名形式。

**已备好但未用**:`out/outline.json`——296 章章节树(官方章名:
双摆推演/第二信号/缺位拟合/逆序矩阵/异频共振/简谐周期/放射衰变/叠影效应…)
+ 1669 关卡的 pre/next 拓扑序。只缺「组 → 关卡」这一根引线。

**已试(全部失败)**:
1. 组号拆位猜测 ×7(详见 B7)
2. 组前缀与 Avg3DPlotData(1497 条,txtName=M03003 格式)、AvgData、StageConfig、
   StoryData 全字段比对 → 零命中
3. 全表 packed 数组反查(找"谁引用了台词 id")→ 只找到系统表,无主线映射

### A3 主线关卡战前台词未接入

**症状**:StageConfigData 的 f9-f13 是 packed 数组,最初怀疑是台词组,
经查指向 StageEnemy/StageEvent 的 id(事件/敌人引用),非台词。
战前对白(若有)链路未知。

---

## B 级问题(数据在,链未接)

### B1 KittyCafe / Kittycafe2(咖啡厅)

- `KittyCafeDialogueData`(13 条):f1=id(101101),f2=组(101),f9=101248(数字)
- `KittyCafeContentByDialogueIdData`(13 条):f1=对话id,f2=packed varint
  (解出 10110101 这种 9 位数)
- **两者解出的数字都不在语言包里**(lang 无此键)。
- `Kittycafe2DialogueData` 128 条同构(f1=101410,f8=101410)
- 已试:f9 直查 lang / f2 packed 直查 lang / 配对 DialoguePage 的「组×1000+序」模式
- **待试**:这些 9 位数是否属于另一个文本命名空间(例如 EsCellData/其他表的 id 空间)

### B2 LoveAvg / CharacterAvg(好感/个人剧情)

- `LoveAvgData`(408 条)/`CharacterAvgData`(332 条)经查是**解锁条件表**
  (f4/f8 是「乌尔丽德升级至20解锁」类文本),正文不在这里。
- `LoveAvgByGunIdData`(68 条)/`CharacterAvgByGunIdData`(55 条)只有 f1(枪id)+
  f2 packed,packed 值不在语言包。
- **待试**:f2 packed 是否指向 EsCellData 或其它文本行表(同 B1)

### B3 ChessStory(棋局剧情)

- `ChessStoryData` 796 条:f2 是代号("NC-2-10"),f3=101122/201114(疑似段表 id),
  pre/next 链完整,f9=难度/章节号。
- `ChessStoryByGroupData`(2956B)未 probe。
- **待试**:probe ChessStoryByGroupData,看 f3 是否指向它

### B4 LobbyGunStory(宿舍剧情目录)

- `LobbyGunStoryData`(272 条)是**目录表**:f4=标题(「赞美的艺术·Ⅰ」),
  f5=pre 链,f3=枪 id(1044),f9/f10 是占位("下载中")。
- 正文应在 `LobbyGunStoryByGunIdData`(未 probe)。
- **待试**:probe LobbyGunStoryByGunIdData 的 f2 packed 指向哪

### B5 副官对话说话人显示为资源名

- AdjutantConversationData 的 f4/f5/f6 是动画名 `c_Charolic_idle_to_apathy`,
  抽出的说话人是 "Charolic"(英文),不是「夏罗莉克」。
- 影响:仅观感;数据正确。枪 id→中文名映射表未定位。

### B6 小表/无文本表(低价值)

- EsAvgPlotData(135 条):f2/f3 是 `AA01115…` 资源名,无文本
- FitnessgameAvgData(2 条):太小
- CharacterVoiceData(49 条):语音触发矩阵,无文本

---

## C 级问题

- C1 邮件卷部分节标题=正文首行,略有重复感
- C2 匿名卷名(「演出剧情 100」)对读者无信息量(依赖 A2 解决)
- C3 20 个 USM 过场视频字幕未提取(exilium-tools 有 subtitle_extractor,覆盖面小)

## D 级问题

- D1 仓库未推 GitHub(bundle 已备好:`/sdcard/Download/gf2-story-tool.bundle`)
- D2 limbus 项目(另一款游戏)有 380 个文件缺文件级标题,等解包资源

---

## 三、B7:已确认为死路的尝试(勿重复)

1. **组号拆位猜测 ×7 全错**:DialogueGroup×100、AvgData/AvgPlot 拆位、StageGrid、
   StageConfig×1000、ChapterData、Dg×1000、9位/10位 id 空间假设。
   教训:id 空间在各表间大量重叠,数值匹配必然误报;不做拆位推断。
2. **Table 内无主线说话人表**:全表扫描「字段值=已知角色名」,只有宿舍对话命中。
3. **bundle 双哈希**:文件名(000a02c2…bundle)与 AssetBundle 内部 m_Name
   (de5fc524…bundle)都是哈希,无语义。
4. **catalog 不在客户端**:LocalCache/Data 下无 catalog 文件,清单在服务端/APK 内。
5. **6 个样本 bundle 全是美术**(Texture2D/Mesh/Shader/GameObject),未见 TextAsset。

## 四、当前可用资源

| 资源 | 位置 | 状态 |
|---|---|---|
| Table 静态表 | /sdcard/Download/gf2-dump/Table/ | 全量可读 |
| 样本 bundle | /sdcard/Download/gf2-dump/*.bundle | 6 个,已解密验证 |
| Mobile 视频目录 | /sdcard/Download/gf2-dump/Mobile/ | 1.8GB USM,未用 |
| 44GB AssetBundles | 手机游戏目录内 | 哈希命名,无法定位 |
| 解密工具 | gf2_bundle.py(已实现 XOR+UnityPy) | 已验证可用 |

## 五、想请评审回答的问题

1. B1-B4 的挖掘路径是否合理?有无更优的表间关联思路?
2. A1/A2 在无 PC、catalog 不可得的前提下,是否还有未尝试的本地手段?
   (例如:全局扫描 44GB 的可行性折中方案、从 USM 字幕反推、从游戏内文本快照比对)
3. 问题优先级排序是否认同?(建议:先 B1-B4,再推 GitHub,最后等 PC 做 A)
4. 有无遗漏的问题维度(数据质量/版权合规/工程结构)?
