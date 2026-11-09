# 评审决议 v2.2(2026-11-09 第二轮)

> 输入:docs/project-report.md(224 卷收口状态)。
> 核心新结论:**B2/B4 是同一个缺口,解法是"序对位"而非"值匹配"**;
> P6-A 的 metadata 方向撤回,改查 catalog。

## 一、主线推断:B2/B4 最后一跳 = 序对位

### 依据(全部来自报告自身数字)
- Avg3DPlotData **1497 条** vs 演出组 **1474 组** —— 量级几乎相等;
- 此前所有失败尝试都是**值匹配**(全字段整值/拆位),均未试**序对位**;
- Avg3DPlot.f5 携带角色 id 数组;Avg3DPlot.f3/f8 是 txtName(M01101),
  其编码语义已证(M03003 ↔ 关卡 code "3-2");
- B4 的 ByGunId.f2 整值 100% 命中 Avg3DPlotData;B2 的 ByGunId.f2
  命中 AvgPlotData —— 两族都停在同一点:plot 表 ↔ avg3d 组的对应。

### 假设
两条表是**一一对应的平行序列**:plot 表存编排(章节/角色/txtName),
content 表存文本行,中间无显式外键。按各自 id 升序排列,第 N 项互相对应。

### 验证判据(按序执行,任一步失败即降级)
1. **角色交集**:取前 20 对;plot.f5 角色 id 数组 ↔ 组内文本出现的角色名
   (可从 4.9% 内嵌说话人 + GunData 名字表建立 id→名映射)。
   交集率 >50% 即强证据。
2. **章节隔离**:取第 1 章(txtName M01xxx)与第 8 章(M08xxx)各 5 对,
   交叉验证——第 1 章的组不应出现第 8 章特有角色。无交叉即强证据。
3. **首尾校准**:若整体命中率低于 50% 但首尾若干对命中,说明存在**段偏移**
   (两条表起点不同),用首尾命中对推偏移量后重验。偏移校准属于结构验证,
   不是拆位猜测,不违 B7。
4. 全通过 → 落 data 映射表(plot_id → group_id),B2/B4 同时闭合,
   并顺带解决跨组顺序(章内组序 = plot 序)。

### 若失败
写进 blocked.md:序对位已试、角色交集率 X%、章节隔离结果 Y。
不再尝试第三种顺序方案(如按 txtName 排序对位)——两种排序都失败即
判定"对应关系不在可排序维度",收手。

## 二、B3 棋局:5 分钟整值查

ChessStoryByGroupData.f2 的 796 个内容 id → ChessStageData 已证(坐标)。
但棋局对话文本大概率同样落在 Avg3dContent:把这 796 个 id 整值逐一对
**Avg3dContent 的组 id 集**与**行 id 集**各查一次。
判据:命中率 >50% 即闭;0 命中则棋局无台词(纯战棋),记 blocked。

## 三、完成度分母:孤儿文本统计

语言包 51.8 万条 - 全部已接家族引用集 = 孤儿集;滤长度 >100 → 候选家族池。
按 lang id 区间聚类,每簇取 3 条读;语义连贯且属某玩法即立项。
预期候选:角色档案、武器/道具描述、活动剧情、誓约/Tpsshoot。
判据产出:out/orphan_families.tsv(簇、条数、样例、判定),作为
README「已知边界」的量化版本,也是完成度的分母。

## 四、P6-A 修正:撤回 metadata,改查 catalog

**判断**:Addressables 的 location→bundle 映射在 catalog(catalog.json /
catalog.bin),global-metadata.dat 只含代码字符串字面量,**不会有**
"资源路径→bundle 哈希"的完整映射。靠 metadata 反推 44GB 文件名,
成功率估 <30%,不做。

**替代路径(按序)**:
1. **APK 内找 catalog**(首要):用户导出 APK 后
   `unzip -l xx.apk | grep -iE 'catalog|/aa/|addressables|settings.json'`
   —— 命中 catalog.json(几 MB JSON)即得完整 location 表,双哈希当场消解;
2. catalog 为 .bin:是序列化 CatalogFile,社区有解析脚本,小文件手机可跑;
3. **热更目录全搬**:catalog 也可能在 LocalCache/Data 或 files/ 下
   (名字含 catalog_/hash),让用户把 LocalCache/Data 全目录搬一次(半小时);
4. 否决:UnityPy 读已知 bundle 的 container 列表(只能看已知文件内部,
   无法反查未知文件名);反编译加载代码(答案仍在 catalog,价值低)。

**不确定(标注)**:以上基于 Unity Addressables 1.x 默认行为;
GF2 若自定义封装,路径可能不同——但"catalog 在 APK 或热更目录"概率高,先查。

## 五、优先级(替代 v2.1 序列)

```
① B4/B2 序对位验证(1 小时,可能一次通两族)
② B3 棋局整值查(5 分钟)
③ 孤儿文本统计(2 小时,完成度分母)
④ 用户导出 APK / 全搬 LocalCache,查 catalog(P6 唯一正解)
⑤ GitHub 推送(用户操作,已备好,不再等)
```

## 六、遗漏维度(新增三条)

1. **跨组顺序未验证**:组内顺序已证(id 升序),章内多组先后无依据——
   序对位顺带解决;若序对位失败,成书卷内组序必须标注「顺序未证」。
2. **EPUB 无人通读**:224 卷均机器拼装。抽 1 卷(建议最大主线卷)从头读到尾,
   检查分节断裂/重复/顺序错位。机器指标过不了"读起来对不对"。
3. **负结果边界要精确**:B8(wiki 不可达)写明查了哪几个源;catalog 核查
   写明"6 处 LocalCache 目录,未查 APK 内"——否则下一个人(或开源后的社区)
   会重复劳动。

## 七、执行结果(待填)
