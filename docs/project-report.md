# gf2-story-tool 项目全景报告(供外部评审)

日期:2026-11-09 · 版本:v2.1 收口状态
代码:`/data/user/0/cc.codroid/files/home/workspace/gf2/`(git,20 提交)

---

## 1. 项目目标

把《少女前线2:追放》(Girls' Frontline 2: Exilium,B服)的剧情文本从游戏
静态表(Table)提取为结构化语料,并生成可离线阅读的 EPUB。约束:纯手机端
(Android 16,aarch64,Python 3.14),无 PC、无 root、无第三方依赖(protobuf 手写解析)。

## 2. 数据形态(已逆向的部分)

### 2.1 Table 静态表(125MB,已全量解析)
- 文件 = 4 字节小端 uint32(跳过长度)+ protobuf 消息体
- 无加密;2264 张表(ps:目录实际 .bytes 文件数约 2200+)
- 语言包 `LangPackageTableCnData`:51.8 万条 id→中文文本;其他语言表(B服)8 字节空壳
- 结构:ChapterData(296 章)→ StoryData(1669 关,pre/next 链)→ 各剧情家族

### 2.2 AssetBundle(44GB,未解析)
- Unity Addressables 打包;文件名 = 内容哈希(000a02c2…bundle)
- 内部 AssetBundle m_Name 也是哈希,无任何语义
- XOR 加密(前 0x8000 字节,密钥公开于 nijinekoyo/GF2AssetBundleDecryption 源码);
  解包链路已验证可通(gf2_bundle.py,UnityPy 1.25.4)
- 6 个样本 bundle 全部是美术资源(Texture2D/Mesh/Shader/GameObject)
- catalog 文件不在客户端(服务端/APK 内)

## 3. 已完成成果

| 家族 | 来源表 | 规模 |
|---|---|---|
| 演出对白 | Avg3dContentData(组=id//1000) | 21,966 行 / 1,474 组 |
| 宿舍对话 | DialoguePageData(f3=说话人,f4=头像) | 2,366 页 / 1,707 组 |
| 公会战 | GuildwarStoryData→ParagraphData(f6 packed) | 344 行 / 102 篇 |
| 大厅闲聊 | LobbyDialogueData(f3 台词,f6 选项) | 471 行 |
| 副官对话 | AdjutantConversationData(f3 台词) | 98 行 |
| 休息室 | LoungeDialogData(f3 名,f4 台词) | 63 行 |
| 互动 | BehaviorDialogData | 7 行 |
| 暗区 | DarkzoneDialogueData(f5 名,f6 台词) | 10 行 |
| 咖啡厅Ⅰ | KittyCafeContentData(f2 组,f4 说话人,f5 台词) | 136 行 / 13 组 |
| 咖啡厅Ⅱ | Kittycafe2ContentData(同构) | 1,323 行 / 128 组 |
| 信件/报道 | AvgContentData 筛选(≥120 字+叙事特征) | 199 段 / 36 篇 |

- 成书 **224 卷 EPUB3**(浅色简约封面,cover-image 声明,目录可跳转)
- 测试 16 组断言全绿;数据版本闸门(version 1195672 / bv 1190370)入 report.json
- 章节骨架 out/outline.json(296 章 / 1669 关拓扑序)已备,待归属映射

## 4. 问题清单与当前结论

### P0 级:A1 逐句说话人(主线覆盖 4.9%)
- 27,000+ 行正文中仅约 1,079 行文本内嵌说话人(两种格式:`<color=..>名:</color>文`
  与裸 `名:文`)
- 全表扫描「字段值=已知角色名」只有宿舍对话自身命中 → Table 无主线说话人表
- 结论:说话人在演出配置(bundle 内)

### P0 级:A2 组↔章节归属
- 148 个演出组(6 位号,如 305203)无法挂到 296 章章节树
- 已试:拆位猜测×7(全错)、全字段整值比对(Avg3DPlotData/AvgData/StageConfig/
  StoryData 零命中)、packed 数组反查(只有战斗关卡事件,id 空间重叠误报)、
  Avg3DPlot f9/f10 验证(41/1473 巧合)
- 结论:映射不在 Table

### P1 级:家族正文链未通
- **B2 好感/个人剧情**:标题表在(LoveAvgData.f5「形影不离」「狐狸尾巴1」);
  ByGunId.f2 整值 100% 命中 LoveAvgData 与 AvgPlotData(f1 子集);正文行表不在 Table
- **B3 棋局**:ChessStory.f3→ChessStoryByGroupData 100%;其 f2 packed 的 796 个内容 id
  →ChessStageData(地图坐标串,无文本)
- **B4 宿舍剧情**:ByGunId.f2 整值 100% 命中 Avg3DPlotData(1497 条,txtName=M01101 格式);
  缺口是 Avg3DPlotData↔Avg3dContent 组的最后一跳

### P2 级:观感/小表
- 副官说话人为英文资源名(Charolic,非「夏罗莉克」)
- EsAvgPlot(资源名无文本)/Fitnessgame(2 条)/CharacterVoice(语音矩阵)

### P3 级:流程
- 仓库未推 GitHub(bundle 已备)
- 20 个 USM 过场视频(.usm,CriWare)字幕未提取(覆盖面小)

## 5. 已穷尽并记录的死路(勿重复)

1. id 拆位猜测 ×7(DialogueGroup×100、AvgData/AvgPlot 拆位、StageGrid、
   StageConfig×1000、ChapterData、Dg×1000、9 位/10 位空间)——全错
2. Table 全表字段值=角色名扫描——无主线说话人表
3. bundle 文件名+内部名双哈希——无法按名定位
4. catalog 不在客户端(6 处目录核查)
5. 社区数据源:GitHub 只有工具类;biligame wiki 仅 2021 一测 9 条旧页;
   灰机 403;gf2.wiki 不可达

## 6. 待验证方案(P6-A,需用户导出 APK)

1. vivo 文件管理器:应用详情→分享安装包→导出 GF2 APK(约 2GB)
2. 解 zip 取 `assets/bin/Data/Managed/Metadata/global-metadata.dat`(IL2CPP)
3. 提取字符串字面量,过滤 `avg`/`story`/`dialog`/`.bundle`
4. **关键判据**:6 个已知样本 bundle 的哈希名(000a02c2…/00b1f92f… 等)是否出现在
   metadata 字符串中——出现任一即证明 asset 地址表在 metadata 内,可批量导出
   「资源路径→bundle 哈希」清单;不出现则考虑 fnv1a/自定义哈希再试(成本封顶半天)
5. 命中 → 精确取件 → T9/T10 解锁(归属+说话人)
不确定点:Addressables 的 location 列表通常在 catalog,而非 global-metadata;
metadata 里更可能是**资源路径字符串**(如 `Assets/…/avg/M01101`)而非 bundle 哈希——
若只有路径没有映射,仍需 catalog。

## 7. 环境与合规

- 只读游戏文件,不修改、不注入、不绕过登录/付费
- 解密用公开工具算法(XOR 密钥来自开源仓库),不涉及 DRM 破解
- 产物仅供个人研究;仓库 NOTICE 声明不含任何游戏数据,数据不入库
- MIT 代码许可(仅覆盖代码)

## 8. 请评审回答

1. 完成度评价:224 卷/11 家族,在"Table 可及"前提下这个覆盖算完整吗?
2. P1 级 B2/B3/B4 有无未尝试的表间关联思路?(注意死路清单,勿重复)
3. P6-A 的技术可行性判断:IL2CPP global-metadata.dat 字符串是否可能包含
   Addressables 的 location/bundle 映射?有无更可靠的替代(如 IL2CPP dump 后
   反编译 AssetBundle 加载代码)?
4. 优先级建议与遗漏维度(数据质量/合规/工程结构)。
