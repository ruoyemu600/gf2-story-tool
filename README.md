# gf2-story-tool

《少女前线2:追放》(Girls' Frontline 2: Exilium)剧情文本提取管线:从游戏热更静态表(Table)提取剧情对白,合订成可阅读的 txt / EPUB3。

**本仓库只含代码。** 数据(游戏 Table、提取产物)不入库,见 NOTICE。

> 📖 **整理好的剧情文本(224 卷 EPUB/TXT)在单独的仓库**:
> [gf2-story-text](https://github.com/ruoyemu600/gf2-story-text)
> (版权归散爆网络 / MICA Team,仅供学习研究,详见该仓库的 DISCLAIMER)

## 数据形态(已验证)

游戏热更资源 `files/LocalCache/Data/Table/*.bytes`:
- 格式 = 4 字节小端长度头 + protobuf 消息(社区工具 nijinekoyo/GF2AssetBundleDecryption 的 Go 源码确认;Table 未加密)
- 语言包 `LangPackageTableCnData` 51.8 万条 = 全量简中文本池(id → 文本)
- 演出对白 `Avg3dContentData` 2.2 万行;宿舍对话 `DialoguePageData` 2366 页(自带说话人+头像);公会战 `GuildwarStoryData → GuildwarStoryParagraphData` 链
- 章节树 `ChapterData`(296 章)/ 关卡链 `StoryData`(1669 关)结构完整

## 用法

```bash
# 1. 从游戏提取 Table 目录(手机:厂商文件管理器可进 Android/data;
#    PC:客户端目录 LocalCache/Data)
# 2. 解析成语料
python3 gf2_extract.py --table /path/to/Table --out out
# 3. 成书(txt + EPUB3)
python3 gf2_books.py --corpus out/corpus.json --out out/books
```

## 排版规则

- `<color=..>名:</color>文` 与裸 `名:文` 抽取说话人;无说话人按旁白缩进
- 富文本标签(color/size/b)剥离;`{}` 动态占位符原样保留
- 名单类组(80% 行 ≤6 字)过滤,不入书
- 公会战多分支(长城列车/莫科什/暗商)保留分支原文

## 数据版本

- 提取日期:2026-11-09
- Table `version.txt`:1195672,`bv_version.txt`:1190370(B服当前版本)
- 结构支持多语言(LangPackageTableEnus/Jajp/Kokr/Zhtc 等),但 **B服仅下载中文**,
  其他语言表为 8 字节空壳;换服/换语言只需替换对应 LangPackage 表。
- `out/report.json` 记录上述版本号与各家族行数基准——换版本重跑时对比,
  行数大幅漂移即需评估(数据级回归闸门)。

## 已知边界(诚实清单)

- 组 ↔ 章节/角色的归属编码未破译(v1 按 3 位前缀聚卷)
- 说话人仅在文本内嵌时可得(4.9%);其余在演出配置层,需 AssetBundles
- `AvgContentData` 17.5 万条是系统文本池(公告/邮件/成就),非剧情,已排除
- 誓约/好感剧情组与主线演出组的区分待 v2

## 结构

| 文件 | 作用 |
|---|---|
| `gf2_table.py` | Table 解析器(protobuf wire format 通用解码) |
| `gf2_extract.py` | 五层提取:语言包/演出对白/宿舍对话/公会战 → corpus.json |
| `gf2_books.py` | 成书:216 卷 txt + EPUB3(mimetype 首位不压缩 + nav) |
| `tools/discover_refs.py` | 表引用侦查器(破译 id 归属用) |

## 致谢

- 表格式来自 [nijinekoyo/GF2AssetBundleDecryption](https://github.com/nijinekoyo/GF2AssetBundleDecryption)(开源 Go 实现)
- 游戏本体:《少女前线2:追放》© 散爆网络 / MICA Team
