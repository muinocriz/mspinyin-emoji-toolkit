# MSPinyin Emoji Toolkit

## Microsoft Pinyin Emoji 映射调查报告与编辑工具

> 项目目标：解释一个看似简单、但实际牵涉 Windows 输入法多套数据通道的问题：**为什么某些 Emoji 在 `Win + .` 独立 Emoji 面板里能搜索到，但微软拼音默认候选里却没有？**
>
> 本报告以 `🪣`（BUCKET，U+1FAA3）为主要例子，记录从用户自定义短语、个人学习数据，到系统词典二进制逆向、Emoji 年代分析、LEX 双向转换和系统替换实验的完整调查过程。

---

## 0. 结论先行

这次调查得到的核心结论是：

1. **`Win + .` Emoji 面板和微软拼音候选中的 Emoji 不是同一套映射数据。**
2. 在本次上传的 Windows 样本中，微软拼音自带的直接“拼音 → Emoji”映射可以明确定位到：

   ```text
   C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex
   ```

3. 该文件使用 `mschxudp` 家族的变长记录格式，和微软“用户自定义短语”文件在容器结构上高度相似，但它是**系统随输入法提供的内置候选资源**，不是当前用户的自定义短语文件。
4. 本机样本的 `ChsPinyinUDP.lex` 有 3099 条记录，其中 1386 条含 U+1F000–U+1FAFF 范围的 Emoji；这批 Emoji 映射呈现非常明显的 **2017 / Unicode 10.0 / Emoji 5.0 内容截止**：2017 年新增 Emoji 基本覆盖，而 2018 / Unicode 11.0 之后的新 Emoji 为 0。
5. `🪣`、`🪜`、`🪞`、`🪟`、`🪥` 等 Unicode 13 / Emoji 13 时代字符在本机 `ChsPinyinUDP.lex` 中均不存在，所以微软拼音输入 `shuitong` 不出现 `🪣` 是词库内容缺失，而不是字体不支持。
6. `Win + .` 走的是另一套 Emoji 搜索/语言资源。微软仍在 Windows 版本更新中维护 Emoji 面板的 Emoji 集合和 search terms；它与旧的拼音候选注入机制解耦。
7. 本项目已经完成：
   - `LEX → CSV`
   - Excel/CSV 修改
   - `CSV → LEX`
   - 自动按 `py` 排序
   - 报告新增记录最终位置
   - 未修改 round-trip 逐字节一致验证
8. **实机加载验证已经成功**：在本次测试机器上，替换系统 `ChsPinyinUDP.lex` 后，先切换到英文输入法，再切回“中文（简体）- 微软拼音”，新加入的映射即可生效；不需要重启整台电脑。这说明在该 Windows / 微软拼音版本中，手工重建并替换后的合法 LEX 能被 `ChsIME` 重新加载并实际参与候选生成。需要强调的是，这仍是对本次实机版本的验证，不应无条件推广到所有 Windows 构建。

---

# 1. 起点：为什么 `Win + .` 有 🪣，微软拼音却没有？

最初的问题来自一个很具体的现象：

```text
Win + .
搜索“水桶”
→ 可以找到 🪣
```

但使用微软拼音：

```text
输入 shuitong
→ 候选中没有 🪣
```

`🪣` 是：

```text
U+1FAA3 BUCKET
```

它属于 Unicode 13.0 / Emoji 13.0 时代的新字符。Unicode Emoji 13.0 的官方列表中明确包含 `U+1FAA3 bucket`，同一批还有 `🪜` ladder、`🪞` mirror、`🪟` window、`🪥` toothbrush。

这立即产生两个可能性：

```text
A. Win+. 和微软拼音共享 Emoji 数据，但微软拼音搜索逻辑出了问题

B. 两者根本是两套独立的数据和搜索机制
```

后续二进制分析最终支持 **B**。

参考：

- Unicode Emoji 13.0 list: https://unicode.org/emoji/charts-13.0/emoji-list.html
- Unicode 13 Symbols and Pictographs Extended-A: https://www.unicode.org/charts/PDF/Unicode-13.0/U130-1FA70.pdf

---

# 2. 第一条路：先研究“用户自定义短语”

## 2.1 为什么从 UserDefinedPhrase.dat 开始

微软拼音设置中存在“用户定义的短语”导入/导出功能，因此最直接的想法是：

> 如果我们能自己添加 `shuitong → 🪣`，也许微软内置 Emoji 本身就是同一种数据。

公开的社区逆向项目已经证明 Microsoft Pinyin User Defined Phrase 使用一种以：

```text
mschxudp
```

开头的二进制格式。

典型关系是：

```text
UserDefinedPhrase.dat / mschxudp
    → 用户主动添加的自定义短语
```

例如：

```text
shuitong → 🪣
tizi     → 🪜
jingzi   → 🪞
chuanghu → 🪟
yashua   → 🪥
```

可以打包为用户自定义短语 `.dat` 后通过微软拼音设置导入。

本项目最初也使用这一格式生成过测试文件，从而确认：

- `py` 是输入码/拼音字符串；
- `text` 是输出候选；
- `text` 本质上是 UTF-16LE 字符串，所以不仅能放单个汉字，也能放 Emoji；
- 候选位置由记录中的一个字节控制。

## 2.2 参考的开源项目

这一步主要参考了以下项目：

### kyan001/UserDefinedPhraser

https://github.com/kyan001/UserDefinedPhraser

该项目明确把 UDP 称为 **User Defined Phrases**，支持生成 Win10 微软拼音 `UserDefinedPhrase.dat`，并给出了 `mschxudp` 文件头、offset table 和词条结构示例。

### nopdan/rose

https://github.com/nopdan/rose

该项目将：

```text
msudp
```

定义为“微软用户自定义短语”，并把：

```text
mspy_udl
```

独立定义为“微软拼音自学习词汇”。这一点很重要，因为它直接提示我们：**用户自定义短语和输入法自学习数据不是同一种文件。**

### Nativu5/MSPinyinEmoji

https://github.com/Nativu5/MSPinyinEmoji

这是一个直接利用用户自定义短语机制给微软拼音补 Emoji 候选的项目。它说明“通过用户短语增加 Emoji”是可行路线，但这仍然不能证明微软原生 Emoji 是存放在用户自定义短语数据里的。

## 2.3 项目中的解析工具

本项目提供：

```text
tools/MSPinyinUserPhrase_to_CSV.py
```

用于把 `UserDefinedPhrase.dat` / `mschxudp` 解析为 CSV。

实际上它复用了本项目对 `mschxudp` 记录容器的解析逻辑，因为用户自定义 DAT 与后面发现的 `ChsPinyinUDP.lex` 属于同一家族。

示例：

```powershell
python .\tools\MSPinyinUserPhrase_to_CSV.py `
  --input .\UserDefinedPhrase.dat `
  --output .\UserDefinedPhrase.csv
```

---

# 3. 第二条路：微软拼音的个人数据文件到底分别干什么？

随后检查了当前用户目录中的微软拼音个人数据，重点包括：

```text
ChsPinyinDeletedCands.dat
ChsPinyinIH.dat
ChsPinyinUDL.dat
ChsPinyinPinnedCands.dat
```

以及相应的 `.bak`、`_Beta` 版本。

调查后可以把几个主要文件大致分成：

```text
UserDefinedPhrase.dat / mschxudp
    → 用户自定义短语

ChsPinyinUDL.dat
    → 自学习短语 + 完整拼音索引 + 时间

ChsPinyinIH.dat
    → 学习/历史词条 + 输入计数 + 时间

ChsPinyinDeletedCands.dat
    → 删除候选的内部不透明记录
```

注意：上面是根据样本、已有逆向项目和实测结构总结的语义，不代表微软公开的二进制格式文档。

---

# 4. ChsPinyinUDL.dat 解码

## 4.1 样本结构

本次样本：

```text
文件大小：368640 bytes = 0x5A000
magic：55 AA 88 81
记录区：0x2400
每条记录：60 bytes
header +0x0C：5974 条
```

这与 `nopdan/rose` 的 `format/mspy_udl` 实现以及公开的微软拼音取证研究相吻合。

每条 60-byte 记录，我们实测可按下面方式解释：

```text
+0x00  uint32     时间字段
+0x04  3 bytes    简拼/短 key
+0x07  3 bytes    其他结构字段，本样本常见 00 00 04
+0x0A  uint8      汉字 UTF-16 code unit 数
+0x0B  uint8      flag，本样本多数为 0x5A，少量 0xAA
+0x0C  UTF-16LE   词条文本
随后            每个汉字对应一个 uint16 拼音索引
剩余            padding / 未知字段
```

例如样本记录：

```text
爱爱我
拼音索引：1 1 345
→ ai'ai'wo

按不动了
拼音索引：2 20 72 170
→ an'bu'dong'le

熬出啊那个
→ ao'chu'a'na'ge
```

## 4.2 拼音索引表

这里一个关键发现是：UDL 并不是直接把 `ai'ai'wo` 这样的完整拼音作为字符串保存，而是保存 uint16 索引。

`nopdan/rose` 的：

```text
format/mspy_udl/pinyin_list.go
```

给出 413 个微软拼音内部音节索引，我们用同一张表成功解出了本机 5974 条记录的完整拼音。

参考：

- https://github.com/nopdan/rose/blob/main/format/mspy_udl/mspy_udl.go
- https://github.com/nopdan/rose/blob/main/format/mspy_udl/pinyin_list.go

项目中已经把这张表和解析器整理为：

```text
tools/mspy_pinyin_list.py
tools/MSPinyinUDL_to_CSV.py
```

使用：

```powershell
python .\tools\MSPinyinUDL_to_CSV.py `
  --input .\ChsPinyinUDL.dat `
  --output .\ChsPinyinUDL.csv
```

输出包括：

```text
word
pinyin
pinyin_indices
short_key
timestamp_raw
timestamp_utc
flag
原始 record hex
```

## 4.3 时间字段

UDL 的时间值可以合理解释为：

```text
2000-01-01 00:00:00 UTC + uint32 秒数
```

`rose` 也采用了这一转换方式。

但是报告中仍然把它称为“时间字段”，而不武断地把每条记录的时间定义为“最后一次输入时间”。

---

# 5. ChsPinyinIH.dat 解码

## 5.1 样本结构

本次样本：

```text
文件大小：496640 bytes = 0x79400
magic：55 AA 88 80
记录区：0x1400
每条记录：60 bytes
header +0x0C：8192 slots
```

记录可稳定解码为：

```text
+0x00 uint32      UTF-16 code unit 长度
+0x04 uint32      时间字段
+0x08 uint32      输入次数/频率型计数
+0x0C UTF-16LE    词条文本
后部             其他内部数据/padding
```

本机示例：

```text
〇
时间：2026-06-22 07:48:07Z
count：1

一
时间：2026-11-01 19:43:00Z
count：4

一下
时间：2026-11-02 16:21:23Z
count：4
```

因此 IH 与 UDL 的角色明显不同：UDL 保存可恢复完整拼音的自学习词条，而 IH 更像“输入历史/学习计数”结构。

项目解析器：

```text
tools/MSPinyinIH_to_CSV.py
```

使用：

```powershell
python .\tools\MSPinyinIH_to_CSV.py `
  --input .\ChsPinyinIH.dat `
  --output .\ChsPinyinIH.csv
```

公开的 Windows 输入法取证资料也曾指出：UDL 从 `0x2400` 开始、IH 从 `0x1400` 开始，两者均使用固定 60-byte 记录。

参考：

- https://9bie.org/index.php/archives/786/comment-page-1?replyTo=1489

---

# 6. ChsPinyinDeletedCands.dat 解码

该文件和 UDL/IH 完全不同。

本次样本：

```text
文件大小：2048 bytes
0x00：“DEL ”
version：2
header +0x14：9 条
记录区：0x400
每条：8 bytes
```

实测 9 条记录形如：

```text
0x0000D0F6, 0x30BB0F0A
0x0001DEEF, 0x30A4B33E
0x00021CA5, 0x3243A030
...
```

关键在于：**这里没有被删除候选的明文 UTF-16 字符串。**

因此它更像内部 ID / hash / 索引组合。我们目前只能可靠导出不透明记录，而不能根据这一个文件恢复“用户到底删除了哪个词”。

项目工具：

```text
tools/MSPinyinDeletedCands_dump.py
```

它故意只输出两个 uint32 和 raw hex，不伪造不存在的“词语解析”。

```powershell
python .\tools\MSPinyinDeletedCands_dump.py `
  --input .\ChsPinyinDeletedCands.dat `
  --output .\ChsPinyinDeletedCands.csv
```

---

# 7. 一个重要排除：内置 Emoji 并不在个人数据里

对上述文件进行实际扫描后：

```text
ChsPinyinUDL.dat
    Emoji 记录：0

ChsPinyinIH.dat
    Emoji 记录：0

ChsPinyinDeletedCands.dat
    没有可见明文 Emoji/候选字符串
```

这说明微软拼音里原本存在的：

```text
xiaoku → 😂
aini   → 😘
huoyan → 🔥
```

不是个人学习产生的，也不依赖 UDL/IH。

于是调查方向从：

```text
用户目录
```

转向：

```text
Windows 系统输入法组件目录 / 系统词典 / 语言模型
```

当时的判断是：内置 Emoji 很可能跟微软拼音程序本体一起安装在系统组件目录或语言资源包里，而且**未必存在一个名字直白的 `Emoji.dat`**，它可能藏在：

- 主词典；
- 辅助候选词典；
- 压缩 lex；
- language model；
- resource DLL；
- 内部数据库或索引。

---

# 8. 如何缩小系统文件范围

## 8.1 候选系统文件

最终对以下文件进行了直接二进制检查：

| 文件 | 大小 | 文件头/内部标识 | 实际推断用途 |
|---|---:|---|---|
| `ChsPinyinUDP.lex` | 128,884 | `mschxudp` | **直接拼音/输入码 → 特殊候选/Emoji 映射** |
| `ChsPinyin.lex` | 9,164,920 | `IMED`, `kunlun-main` | 主静态拼音词典 |
| `ChsPinyin.lm` | 16,395,512 | `PBLM` | 概率语言模型/排序评分 |
| `ChsPinyinAP.lex` | 2,218,030 | `mschxudp` | 上下文 → 后续短语/预测关联 |
| `ChsPinyinHAP.lex` | 217,808 | `IMDX`, `新词热词` | 新词/热词相关索引 |
| `ChsLearningModel.lex` | 10,958,398 | `CNLM`, feature templates | 学习/序列特征模型 |
| `ChsExtra.lex` | 12,502,864 | `IMED`, `taihang-extra` | 额外符号/颜文字等资源 |

## 8.2 为什么最开始会怀疑 LM / Extra / 主词典

在不知道格式之前，Emoji 候选可能来自三个层次：

```text
主词典：决定候选“有什么”
语言模型：决定候选“排多高”
额外资源：混入符号/Emoji/颜文字
```

因此一开始不能直接假设 `UDP` 就是答案，而是需要根据：

- 文件签名；
- 可读字符串；
- UTF-16 Emoji surrogate pair 数量；
- 熵；
- 是否能结构化遍历全部记录；

逐步排除。

## 8.3 实际二进制证据

### `ChsPinyin.lex`

```text
signature: IMED
内部 UTF-16: kunlun-main
```

体积约 9.16 MB，明显是主词典类资源。虽然能找到一些普通符号字符，但没有形成我们需要的“拼音 → 新 Emoji”直接结构证据。

### `ChsPinyin.lm`

```text
signature: PBLM
entropy ≈ 7.83 bits/byte
```

高度压缩/模型化，符合 language model 特征；扫描没有发现足以解释大批 Emoji 直接映射的数据。

### `ChsPinyinAP.lex`

同样以 `mschxudp` 开头，而且 63,702 条记录全部可以按变长结构解析。但左侧字段并不是拼音。例如：

```text
“一万元” → “以上”
“一万元” → “左右”
“一下了” → “。”
```

所以它更像上下文关联/下一短语预测，不是 Emoji 拼音表。

`AP` 的官方缩写含义目前没有找到可靠文档，因此这里只描述其**实测行为**，不擅自扩写 acronym。

### `ChsPinyinHAP.lex`

内部很早的位置直接出现 UTF-16：

```text
新词热词
```

因此它与动态/新热词候选有关，但没有发现目标 Emoji 映射。

### `ChsLearningModel.lex`

内部包含：

```text
ChsLearningModel
U00:%x[-2,0]
U01:%x[-1,0]
U02:%x[0,0]
...
```

这更接近 CRF/序列模型类 feature template，不是简单候选映射表。

### `ChsExtra.lex`

内部 UTF-16 标识：

```text
taihang-extra
```

并有大量 ASCII 颜文字资源，因此最初嫌疑很高；但没有找到 U+1F000–U+1FAFF 范围的大批 Emoji 映射。

### `ChsPinyinUDP.lex`

最终它给出了最直接的证据：

```text
aa          → 😫
abxingxie   → 🆎
aerfa       → α
huoyan      → 🔥
xiaoku      → 😂
aini        → 😘
anjing      → 🤫
baolong     → 🦖
danao       → 🧠
```

因此调查可以从“推测”升级为：

> **在本次上传的 Windows 系统样本中，内置的直接拼音/输入码 → Emoji 映射确实存在于 `ChsPinyinUDP.lex`。**

---

# 9. `ChsPinyinUDP.lex` 到底是什么

## 9.1 “UDP” 是不是网络里的 User Datagram Protocol？

显然不是。

微软官方 Settings URI 中存在：

```text
ms-settings:regionlanguage-chsime-pinyin-udp
```

而公开社区工具长期把微软拼音的 UDP 称为：

```text
User Defined Phrase / User Defined Phrases
```

例如 `UserDefinedPhraser` 就直接使用这一命名。

因此本项目认为：

> **UDP 在这个上下文中几乎可以确定属于 User Defined Phrase(s) 一类命名，而不是 User Datagram Protocol。**

但目前没有找到一份微软官方 glossary 明文写出 “UDP = User Defined Phrase”，所以报告不把该展开标成“微软官方定义”。

参考：

- Microsoft Settings URI 文档： https://learn.microsoft.com/windows/apps/develop/launch/launch-settings
- UserDefinedPhraser： https://github.com/kyan001/UserDefinedPhraser

## 9.2 为什么系统自带文件也叫 UDP？

这是本次调查一个有意思的点：

```text
用户导出的 UserDefinedPhrase.dat
```

和：

```text
系统 ChsPinyinUDP.lex
```

共享 `mschxudp` 容器风格，但它们并不是同一层用户数据。

最合理的解释是 Microsoft Pinyin 复用了同一类“input code → phrase candidate”的数据结构来承载系统扩展候选。

因此：

```text
同一种/相近容器格式
≠
同一个数据生命周期
```

用户短语可以随用户添加、导入和清除；系统 UDP 则跟 Windows/输入法组件一起部署。

---

# 10. `ChsPinyinUDP.lex` 的实际内容

本机文件：

```text
大小：128884 bytes
signature：mschxudp
record count：3099
```

全部 3099 条记录可以无错误结构化解析。

其中含 U+1F000–U+1FAFF Emoji code point 的记录：

```text
1386 条
```

候选 slot 分布：

```text
slot 5：1336
slot 4：39
slot 6：7
slot 2：2
slot 7：2
```

也就是大约 96.4% 的这类 Emoji 记录直接携带：

```text
candidate_slot = 5
```

这解释了为什么很多用户长期观察到：

> 微软拼音的 Emoji/特殊符号经常“霸占第五候选”。

同时整个 UDP 文件还存在特殊 slot 值，例如 `231`、`22`，主要集中在其他类别记录，所以不能把该字节对所有记录都简单解释成普通人看到的“第 N 个候选”。对于 Emoji 记录，`5` 与实际第五候选的相关性非常强。

---

# 11. 为什么 🪣 没有：词库内容真的停在旧年代

我们检查了目标：

```text
🪣 U+1FAA3 bucket
🪜 U+1FA9C ladder
🪞 U+1FA9E mirror
🪟 U+1FA9F window
🪥 U+1FAA5 toothbrush
```

在 `ChsPinyinUDP.lex` 中均为：

```text
0 条
```

与此同时，2017 年 Emoji 5.0 时代的字符大量存在：

```text
🧕
🦖
🧠
🧔
🧙
🧚
🧜
🧞
🦒
🦔
🥨
🥪
🥣
...
```

而较新的：

```text
🥶 2018
🥳 2018
🦩 2019
🦦 2019
🧄 2019
🧅 2019
🪣 2020
🪜 2020
🪞 2020
🪟 2020
🪥 2020
```

均不存在。

---

# 12. 精确估算：Emoji 映射内容停止更新在哪一年？

为了避免“凭几个 Emoji 猜年份”，我们对 UDP 中所有 Emoji code point 做了 Unicode Age 统计。

这里必须区分：

```text
Unicode Age
```

和：

```text
完整 Emoji release 中的所有 sequence 数量
```

我们统计的是“当前带 Emoji property 的 code point 最初进入哪个 Unicode 版本”，不是把 Emoji ZWJ sequence 总数混成同一个概念。

结果非常明显：

```text
Unicode 10.0 / 2017 新增的 Emoji-property code point：
当前集合 56 个
UDP 中存在 54 个
覆盖率 96.43%

缺：
🧒 U+1F9D2
🧟 U+1F9DF
```

然后出现断崖：

```text
Unicode 11.0：66 个，UDP 中 0
Unicode 12.0：61 个，UDP 中 0
Unicode 13.0：55 个，UDP 中 0
Unicode 14.0：37 个，UDP 中 0
Unicode 15.0：20 个，UDP 中 0
Unicode 16.0：7 个，UDP 中 0
```

我们还检查了一个漏洞：Emoji 新版本有时会给旧 code point 增加新的 emoji presentation 或 sequence，所以“没有新 code point”不一定等于“完全没更新”。

因此进一步检查 Emoji 11.0 的代表性旧 code point / sequence，例如：

```text
♟
♾
🏴‍☠️
👨‍🦰
👩‍🦰
```

同样未在该 UDP 映射中发现。

Unicode 官方版本表：

```text
Emoji 5.0  → 2017-06-20 → Unicode 10.0
Emoji 11.0 → 2018-05-21 → Unicode 11.0
```

因此对**这一份实际上传的 `ChsPinyinUDP.lex` 内容**，目前最有力的结论是：

> **Emoji 映射最后一次系统性扩充停在 2017 年的 Emoji 5.0 / Unicode 10.0；从 2018 年 Emoji 11.0 开始，没有发现实质性新增。**

参考：

- Unicode Emoji version table: https://www.unicode.org/reports/tr51/
- Emoji 5.0 version chart: https://www.unicode.org/emoji/charts-5.0/emoji-versions.html

## 12.1 为什么文件本身却看起来是 2025 年？

`ChsPinyinUDP.lex` 文件头 `0x20` 的 qword：

```text
0x689D9DC7
```

按 Unix seconds 解释对应：

```text
2025-08-14 08:26:47 UTC
```

这和“内容停在 2017”并不冲突。

更合理的解释是：

```text
文件打包/生成/部署版本
    可以继续变化

文件中的 Emoji 映射集合
    可以多年没有实质扩充
```

所以准确表述应该是：

> 微软后来仍可能重新打包或重新生成这个系统资源，但其中 Emoji 映射内容从 2017 之后没有看到系统性维护。

不能说“这个文件从 2017 年以后就再也没有被微软碰过”。

---

# 13. 是否只有我们遇到这个问题？

不是。

## 13.1 用户发现更新后 Emoji/符号候选消失

2023 年 Microsoft Q&A 有用户明确描述：过去微软拼音输入：

```text
alpha   → α
jiantou → →（第五候选）
xiaoku  → 😂
```

系统更新后这些特殊候选不再出现，只能改用字符面板。

参考：

https://learn.microsoft.com/en-us/answers/questions/4069875/where-is-the-greeks-emoji-in-win10-chinese-pinyin

这说明这套候选资源本身在不同 Windows/IME 版本之间也可能有加载、配置或部署变化。

## 13.2 有人反而想删除这些 Emoji 候选

2026 年小众软件论坛有用户抱怨，关闭“表情符号及符号面板按钮、新词热词、云建议”等选项后，Emoji 仍然占据候选黄金位。

参考：

https://meta.appinn.net/t/topic/86158

这从另一个角度支持了我们的判断：这些 Emoji 不是简单由“云建议”或“自学习”产生，而属于更底层的候选资源。

## 13.3 自定义双拼和内置方案的行为也不一致

2026 年 Microsoft Q&A 还有用户报告：微软内置双拼方案可以出现 Emoji/符号候选，而自定义双拼方案不能正确触发。

参考：

https://learn.microsoft.com/zh-cn/answers/questions/5698848/question-5698848

这提示 Emoji 候选逻辑可能还依赖 IME 当前编码方案和内部触发路径，而不是一个完全通用的“中文含义搜索器”。

## 13.4 社区已经有人专门补这块缺口

`Nativu5/MSPinyinEmoji` 通过用户自定义短语文件补充 Emoji 候选：

https://github.com/Nativu5/MSPinyinEmoji

项目存在本身就说明“微软拼音原生 Emoji 候选不够完整”是一个真实需求，而不是本机孤例。

---

# 14. 微软为什么可能放弃维护这一套旧 Emoji 候选逻辑？

这一节是**推测，不是微软官方解释**。

目前没有找到微软公开文档明确说：

> “我们在 2017 年决定停止维护 Microsoft Pinyin UDP Emoji。”

但从产品架构演变可以推测几个原因。

## 14.1 旧逻辑本质上是“输入法候选注入”

`ChsPinyinUDP.lex` 的形式是：

```text
shuitong → 某个固定候选
xiaoku   → 😂
huoyan   → 🔥
```

这要求为中文拼音预先维护大量触发词，并且还要决定：

```text
到底排第几候选？
哪些同义词都要触发？
全拼和双拼怎么映射？
中文多义词怎么办？
新增 Emoji 怎么补？
```

这是一个输入法特定、语言特定、排序敏感的维护问题。

## 14.2 Emoji 越来越多后，候选位会被污染

本次样本中大量 Emoji 直接占 slot 5。

这对于喜欢 Emoji 的用户很方便，但对只想快速输入汉字的人来说就是候选干扰。2026 年社区用户“想把候选中的表情符号干掉”正好体现了这种冲突。

## 14.3 独立 Emoji 面板更适合做统一搜索入口

`Win + .` 可以把 Emoji 搜索独立成：

```text
Emoji 字符集合
+
各语言的 short name / search keywords
+
统一 UI
```

而不必让每个 IME 为每种输入方案分别塞候选。

Unicode CLDR 本身就维护 Emoji 的 localized short names 和 search keywords。CLDR 规范明确说这些 keywords 可以用于：

- 搜索字符；
- predictive typing。

参考：

- https://cldr.unicode.org/translation/characters/short-names-and-keywords
- https://unicode.org/reports/tr35/tr35-general.html

**目前没有公开证据证明 Windows Emoji 面板运行时直接读取 CLDR XML。** 更准确的说法是：Win+. 的语言搜索架构与 CLDR 这种“Emoji → 本地化名字/关键词”的数据模型高度一致，微软完全可以把相应数据编译进 Windows 自己的语言搜索资源，并额外做自己的修改。

## 14.4 微软仍在维护 Win+. 的 search terms

这点有官方证据。

Windows Insider Build 21277 在加入 Emoji 12.1 / 13.0 字形时，微软明确说明还改进了 Emoji search terms，并邀请用户反馈“用什么词搜索、期待出现哪个 Emoji”。

参考：

https://blogs.windows.com/windows-insider/2020/12/10/announcing-windows-10-insider-preview-build-21277/

2021 Build 21337 又继续给 Emoji panel 增加更多语言的搜索支持。

参考：

https://blogs.windows.com/windows-insider/2021/03/17/announcing-windows-10-insider-preview-build-21337/

因此从产品投入看，微软确实持续维护：

```text
Win+. Emoji repertoire + localized search
```

而我们在 `ChsPinyinUDP.lex` 中看到的旧“拼音直接映射 Emoji”则没有同步扩张到 2018+。

---

# 15. `Win + .` 搜索为什么比旧拼音映射更有优势

可以把两种模型画成：

## Microsoft Pinyin 旧 UDP

```text
输入 ASCII 拼音
     ↓
ChsPinyinUDP.lex
     ↓
shuitong → 固定候选
     ↓
候选窗第 5 位之类的位置
```

优点：

- 打字过程中直接出现，快；
- 不需要打开额外面板。

缺点：

- 必须为每种语言/输入方案维护触发码；
- 候选排序会干扰正常文字输入；
- 新 Emoji 的同步成本高；
- 同义词覆盖困难；
- 全拼/双拼/自定义方案行为容易分叉。

## Win+. Emoji panel

```text
Emoji repertoire
      +
本地化名称 / keywords
      ↓
独立搜索索引
      ↓
用户搜索“水桶”
      ↓
🪣
```

优点：

- Emoji 全集和输入法候选排序解耦；
- 一套 Emoji repertoire 可以服务多语言；
- 同一个 Emoji 可以有多个关键词；
- 更新 Emoji 字形时可以同步更新 search terms；
- 不会占用普通拼音候选位；
- 可以不断增加支持语言，而不需要改每个 IME 的字典结构。

## 15.1 搜索是否需要联网？

普通 Emoji 搜索本身更符合“本地语言搜索资源”的模式，不是每输入一个词就向服务器查询。

微软通过 Windows build / language feature 更新 Emoji panel 和 search terms，所以：

```text
更新时可能联网
运行搜索本身通常不依赖实时网络查询
```

这和 GIF 搜索不同；GIF 属于网络内容。

---

# 16. `ChsPinyinUDP.lex` 的二进制格式

## 16.1 文件总体布局

本机样本：

```text
0x0000 ┌─────────────────────────────┐
       │ 64-byte header              │
0x0040 ├─────────────────────────────┤
       │ uint32 record_offsets[]     │
       │ count × 4 bytes             │
       ├─────────────────────────────┤
       │ variable-length records     │
       │ ...                         │
       └─────────────────────────────┘
```

header 大致为：

| offset | 类型 | 样本意义 |
|---:|---|---|
| `0x00` | 8 bytes | ASCII `mschxudp` |
| `0x08` | uint32 | `0x00600002` |
| `0x0C` | uint32 | `1` |
| `0x10` | uint32 | offset table 起点，样本为 `0x40` |
| `0x14` | uint32 | records data 起点 |
| `0x18` | uint32 | 文件总长度 |
| `0x1C` | uint32 | record count，样本为 `3099` |
| `0x20` | uint64 | 文件头时间/版本型字段 |
| `0x28` | 24 bytes | 保留/未知 |

偏移表中的每个 uint32 是相对于 records data 起点的记录偏移。

## 16.2 单条记录

本机 `ChsPinyinUDP.lex` 可表示为：

```text
+0x00 uint32     record_magic
+0x04 uint16     text/phrase 起始偏移
+0x06 uint8      candidate_slot
+0x07 uint8      flags_byte
+0x08 uint32     type_id
+0x0C uint32     record_timestamp
+0x10 UTF-16LE   py，00 00 结尾
...   UTF-16LE   text，00 00 结尾
```

其中在本机 3099 条记录中：

```text
record_magic      全部 = 1048592 = 0x00100010
flags_byte        全部 = 19 = 0x13
record_timestamp  全部 = 724750598 = 0x2B32D106
```

`type_id` 分布为：

```text
6 → 1993
3 → 321
4 → 261
1 → 250
2 → 179
5 → 81
8 → 8
9 → 4
7 → 2
```

在 1386 条非 BMP Emoji 记录里：

```text
type_id 6 → 1317
```

所以项目对于**新增普通 Emoji**采用保守默认：

```text
candidate_slot = 5
record_magic   = 1048592
flags_byte      = 19
type_id        = 6
record_timestamp = 724750598
```

但要强调：

- `record_magic` 的确切微软内部命名未知；
- `flags_byte` 的位定义未知；
- `type_id=6` 不能直接写成“官方定义的 Emoji 类型”；
- `record_timestamp` 的业务语义未知。

我们只是根据大量现有 Emoji 记录选择“最接近系统原始数据的默认组合”。

---

# 17. 用户实际编辑 CSV 时需要填哪些字段？

完整 CSV 有：

```text
index
py
text
candidate_slot
record_magic
flags_byte
type_id
record_timestamp
```

对于新记录，真正需要用户关心的通常只有：

```text
py
text
candidate_slot
```

例如：

```csv
,niubi,🐮🍺,5,,,,
```

转换器会从 template 自动补内部默认字段。

## 17.1 一个非常重要的实机发现：`py` 要写拼音，不要写中文

用户实际测试时发现：

正确：

```text
py   = niubi
text = 🐮🍺
```

错误思路：

```text
py = 牛比
```

`py` 不是“中文触发词的含义”，而是 IME 用来匹配的**输入码字符串**。

所以：

```text
输入 niubi
→ 匹配 CSV 中 py=niubi
→ 候选 text=🐮🍺
```

这也解释了为什么 `Win + .` 的“中文关键词搜索”不能简单等价于微软拼音 UDP：

```text
Win+. 搜索的是自然语言 keyword
微软拼音 UDP 查的是输入码/拼音字符串
```

---

# 18. `text` 能不能放多个 Emoji？

可以。

`text` 是一个 UTF-16LE 字符串，不要求只有一个 code point。

因此以下都能在格式层面成立：

```text
niubi → 🐮🍺
haha  → 😂😂😂
huo   → 🔥牛逼🔥
```

微软原始 UDP 本身也有大量多 code point / ZWJ Emoji，例如职业、家庭、彩虹旗等组合。

所以：

```text
🐮🍺
```

会被作为一个整体候选字符串，而不是两个独立候选。

---

# 19. LEX ↔ CSV 工具链

项目当前正式工具：

```text
tools/
├─ MSPinyinUDP_LEX_to_CSV.py
├─ MSPinyinUDP_CSV_to_LEX.py
├─ MSPinyinUDP_apply_patch.py
├─ MSPinyinUDP_verify.py
├─ MSPinyinUserPhrase_to_CSV.py
├─ MSPinyinUDL_to_CSV.py
├─ MSPinyinIH_to_CSV.py
├─ MSPinyinDeletedCands_dump.py
└─ mspy_pinyin_list.py
```

## 19.1 LEX → CSV

```powershell
python .\tools\MSPinyinUDP_LEX_to_CSV.py --input .\ChsPinyinUDP.lex --output .\work.csv --metadata .\metadata.json
```

## 19.2 Excel 修改

Excel 保存时选择：

```text
CSV UTF-8（逗号分隔）
```

例如最后增加：

```csv
,niubi,🐮🍺,5,,,,
,shuitong,🪣,5,,,,
,tizi,🪜,5,,,,
```

## 19.3 CSV → LEX

PowerShell 推荐使用**单行命令**：

```powershell
python .\tools\MSPinyinUDP_CSV_to_LEX.py --csv .\work.csv --template .\ChsPinyinUDP.lex --output .\ChsPinyinUDP.modified.lex
```

转换器会：

1. 读取 CSV；
2. 从原始 template 继承文件头和内部默认字段；
3. 自动按 `py` 字典序排序；
4. 稳定保留相同 `py` 记录之间的相对顺序；
5. 重建 offset table；
6. 重算 `data_start` / file size；
7. 输出新的 LEX；
8. 报告新增记录最终位置。

例如可能打印：

```text
[新增记录最终位置]
第 1661 条记录 / Excel 第 1662 行 : niubi -> 🐮🍺 (slot=5)
```

## 19.4 `index` 不需要手工改

`index` 只用于阅读。

生成 LEX 时脚本不依赖 CSV 中的 `index`。

因此可以直接把新增内容加在 Excel 最后一行；脚本会自动把 `niubi` 插回正确的拼音排序位置。

这项修改来自一次重要排查：原版 3099 条 `py` 是严格字典序排列。如果新记录直接被追加到文件尾，而运行时使用有序查找/二分检索，就可能无法命中。因此最新转换器始终自动排序。

## 19.5 未修改 round-trip 验证

对本机原始：

```text
ChsPinyinUDP.lex
```

执行：

```text
LEX → CSV → LEX
```

在 CSV 不做任何修改时，重建文件 SHA256 与原文件完全一致：

```text
87e687342ae4ce05936e47b23af51ce144d8a29a0d702ec0a95fa04d5073c39a
```

即：

```text
byte-for-byte identical
```

这证明当前解析器/写入器对于该样本的基本二进制布局是可逆的。

---

# 20. PowerShell 常见错误记录

这次实机操作遇到的错误也保留下来，因为它们非常容易重复出现。

## 20.1 `copy /Y` 在 PowerShell 中报错

错误：

```text
Copy-Item : 找不到接受实际参数 ... 的位置形式参数
```

原因：PowerShell 中：

```text
copy
```

不是 CMD 的 `copy.exe` 语法，而是：

```text
Copy-Item
```

的 alias，所以它不认识 CMD 风格的：

```text
/Y
```

正确 PowerShell：

```powershell
Copy-Item "C:\...\ChsPinyinUDP.modified.lex" "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" -Force
```

如果一定要用 CMD 语法：

```powershell
cmd /c copy /Y "source" "destination"
```

---

## 20.2 Python 两条命令粘在一起

出现过：

```text
ChsPinyinUDP.modified.lexpython MSPinyinUDP_CSV_to_LEX_...
```

随后 PowerShell 报：

```text
一元运算符“--”后面缺少表达式
```

原因不是 Python，也不是脚本参数，而是两条命令复制时没有换行，导致：

```text
.lexpython
```

被拼成一个连续 token。

最稳妥的方法是使用一整行：

```powershell
python .\tools\MSPinyinUDP_CSV_to_LEX.py --csv .\work.csv --template .\ChsPinyinUDP.lex --output .\ChsPinyinUDP.modified.lex
```

如果需要 PowerShell 多行续写，要使用反引号：

```powershell
python .\tools\MSPinyinUDP_CSV_to_LEX.py `
  --csv .\work.csv `
  --template .\ChsPinyinUDP.lex `
  --output .\ChsPinyinUDP.modified.lex
```

注意反引号后不要再留空格。

---

# 21. TrustedInstaller 权限：为什么不能直接覆盖

`C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex` 属于 Windows 系统组件资源，普通管理员也可能看到：

```text
你需要 TrustedInstaller 提供的权限才能对此文件进行更改
```

推荐原则：

> **只修改目标文件，不要把整个 `C:\Windows\InputMethod\CHS` 目录永久改成管理员所有。**

## 21.1 先备份

```powershell
Copy-Item "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" "$env:USERPROFILE\Desktop\ChsPinyinUDP.original.lex"
```

## 21.2 切到英文输入法并停止 ChsIME

```powershell
taskkill /F /IM ChsIME.exe
```

不存在进程也没关系。

## 21.3 临时取得目标文件所有权

管理员 PowerShell / CMD：

```powershell
takeown /F "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" /A
```

给 Administrators 临时完全控制：

```powershell
icacls "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" /grant "*S-1-5-32-544:F"
```

使用 SID 是为了避免中文/英文 Windows 的 Administrators 名称差异。

## 21.4 PowerShell 替换

```powershell
Copy-Item "C:\path\ChsPinyinUDP.modified.lex" "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" -Force
```

## 21.5 一定要检查 SHA256

```powershell
Get-FileHash "C:\path\ChsPinyinUDP.modified.lex"
Get-FileHash "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex"
```

两者必须一致。

并建议**重启以后再检查一次**，因为 Windows Update、SFC、组件服务或其他保护机制可能恢复系统原文件。

---

# 22. 替换完成后如何恢复 TrustedInstaller

先删除刚添加的 Administrators 显式 grant：

```powershell
icacls "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" /remove:g "*S-1-5-32-544"
```

再把 owner 还给：

```powershell
icacls "C:\Windows\InputMethod\CHS\ChsPinyinUDP.lex" /setowner "NT SERVICE\TrustedInstaller"
```

这比把系统目录永久留在管理员控制下更稳妥。

如果 IME 出现异常，优先恢复备份的原始 LEX。

---

# 23. 如何重启 ChsIME

最简单方式：

1. `Win + Space` 切到英文键盘；
2. 执行：

```powershell
taskkill /F /IM ChsIME.exe
```

3. 再 `Win + Space` 切回微软拼音；
4. 点击文本框输入，Windows 通常会自动重新启动 `ChsIME.exe`。

检查：

```powershell
Get-Process ChsIME -ErrorAction SilentlyContinue
```

如果 Text Services Framework 状态异常，也可尝试：

```powershell
ctfmon.exe
```

本次实机验证表明，**不需要注销或重启 Windows**：替换 `ChsPinyinUDP.lex` 后，先切换到英文输入法，再切回“中文（简体）- 微软拼音”，新增候选即可出现。注销/重启仍可作为故障排查手段，但不再是本次验证所必需的步骤。

---

# 24. 系统加载验证：已经形成实机闭环

本次调查最终完成了下面的闭环：

```text
原始 ChsPinyinUDP.lex
  ↓
LEX → CSV
  ↓
新增 niubi → 🐮🍺 等记录
  ↓
CSV → LEX（自动按 py 排序）
  ↓
替换系统 ChsPinyinUDP.lex
  ↓
切换到英文输入法
  ↓
再切回微软拼音
  ↓
新候选实际出现
```

因此，对本次测试机器和当前 Windows / 微软拼音版本，可以确认：

- 重建后的 LEX 不仅在结构上合法，也能被 `ChsIME` 实际加载；
- 新增记录会参与候选生成；
- 切换离开微软拼音再切回即可触发重新加载，不需要重启电脑；
- `niubi → 🐮🍺` 已成为实际生效案例。

仍然需要保留的边界是：该结论属于**本次实机版本验证**，不能未经测试直接推广到所有 Windows 构建、Beta 输入法分支或双拼资源。若其他版本不生效，再使用 `Get-FileHash`、Process Monitor 等手段检查文件恢复、读取路径和版本差异。

---

# 25. 项目目录

```text
mspinyin-emoji-toolkit/
├─ README.md                         # 本调查报告
├─ tools/
│  ├─ MSPinyinUDP_LEX_to_CSV.py      # 系统 UDP LEX → CSV
│  ├─ MSPinyinUDP_CSV_to_LEX.py      # CSV → 系统 UDP LEX
│  ├─ MSPinyinUDP_apply_patch.py      # 合并补丁 CSV
│  ├─ MSPinyinUDP_verify.py           # 结构/hash/比较验证
│  ├─ MSPinyinUserPhrase_to_CSV.py   # UserDefinedPhrase.dat → CSV
│  ├─ MSPinyinUDL_to_CSV.py          # ChsPinyinUDL.dat → CSV
│  ├─ MSPinyinIH_to_CSV.py           # ChsPinyinIH.dat → CSV
│  ├─ MSPinyinDeletedCands_dump.py   # DeletedCands opaque record dump
│  └─ mspy_pinyin_list.py            # UDL 413 音节索引表
├─ data/
│  ├─ ChsPinyinUDP_full_roundtrip.csv
│  └─ ChsPinyinUDP_emoji_mappings.csv
├─ patches/
│  └─ emoji_update_example.csv
└─ docs/
   ├─ 01_topics_and_findings.md
   ├─ 02_lex_format.md
   ├─ 03_workflow.md
   ├─ 04_system_replacement.md
   └─ 05_research_notes.md
```

原始 Microsoft 系统文件不打包进项目。回写时应使用**本机当前 Windows 版本**的 `ChsPinyinUDP.lex` 作为 template。

---

# 26. 推荐工作流

## 只想研究，不改系统

```powershell
python .\tools\MSPinyinUDP_LEX_to_CSV.py --input .\ChsPinyinUDP.lex --output .\work.csv --metadata .\metadata.json
```

然后用 Excel/文本工具分析即可。

## 想增加映射

### 方式 A：用户自定义短语

更安全、对 Windows 系统文件侵入更小，适合正常使用。

例如：

```text
niubi → 🐮🍺
```

这是社区 `MSPinyinEmoji` 等项目采用的路线。

### 方式 B：修改系统 `ChsPinyinUDP.lex`

更适合逆向实验，可以研究微软原生候选数据结构，但存在：

- TrustedInstaller 权限；
- Windows Resource Protection；
- 更新恢复；
- IME 缓存；
- 当前版本是否接受修改文件；

等额外问题。

---

# 27. 已确认、强推断、未确认

为了避免把逆向结果写得过头，项目使用下面的证据等级。

## 已确认

- 本机 `ChsPinyinUDP.lex` 是 `mschxudp` 结构。
- 全部 3099 条记录可以结构化解析。
- 存在明确 `py → Emoji` 记录，例如 `xiaoku → 😂`。
- `🪣/🪜/🪞/🪟/🪥` 不在该文件。
- 1386 条记录包含 U+1F000–U+1FAFF Emoji。
- 绝大多数此类 Emoji 的 candidate slot 为 5。
- UDL/IH 是固定 60-byte 个人学习数据结构。
- UDL 中拼音通过 uint16 index 保存，可用 413 音节表恢复。
- DeletedCands 样本没有删除短语明文。
- LEX → CSV → LEX 未修改 round-trip 可逐字节一致。
- `text` 可以是多个 Emoji / ZWJ sequence / 任意 UTF-16LE 字符串。
- `py` 应填写输入码，例如 `niubi`，而不是中文“牛比”。

## 强推断

- `UDP` 在 Microsoft Pinyin 上下文中指向 User Defined Phrase(s) 家族含义。
- `ChsPinyinAP.lex` 是 context/association prediction 类型资源。
- `ChsPinyin.lm` 负责概率/排序评分。
- `ChsPinyinHAP.lex` 与“新词热词”资源有关。
- `type_id=6` 是新增 Emoji 最合适的现有类别默认值。

## 未确认 / 不应写成事实

- 微软内部每个字段的正式变量名。
- `AP`、`HAP` 的官方 acronym 全称。
- Windows `Win + .` 是否直接使用 CLDR XML，还是使用微软自己编译/扩展后的 locale index。
- 微软停止维护旧 Pinyin Emoji 映射的官方原因。
- 其他 Windows 构建、Beta 分支或不同输入方案是否同样接受这一修改，仍需要逐版本验证。

---

# 28. 后续调查方向

最值得继续做的两项实验：

### A. Process Monitor 实测 ChsIME 读取路径

在输入 `niubi` / `shuitong` 时过滤：

```text
Process Name is ChsIME.exe
Operation is CreateFile / ReadFile
Path contains InputMethod\CHS
```

可以直接回答：当前 Windows 构建到底是否读取 `ChsPinyinUDP.lex`，以及是否还读取了另一个版本/缓存文件。

### B. 定位 Win+. 的本地中文 Emoji keyword 数据

可以在 `TextInputHost`、Language.Basic、SystemApps、WindowsApps、`.pri` 等资源范围做文件访问跟踪，验证：

```text
水桶 → 🪣
```

到底由哪个本地资源提供。

这会把当前“两个系统是独立的”进一步推进到“Win+. 的具体文件/资源路径是什么”。

---

# 29. 参考资料

### Microsoft / Unicode

- Microsoft Settings URI (`chsime-pinyin-udp`)  
  https://learn.microsoft.com/windows/apps/develop/launch/launch-settings

- Windows Insider Build 21277 — Emoji 12.1/13.0 与 search terms 更新  
  https://blogs.windows.com/windows-insider/2020/12/10/announcing-windows-10-insider-preview-build-21277/

- Windows Insider Build 21337 — Emoji panel 增加更多搜索语言  
  https://blogs.windows.com/windows-insider/2021/03/17/announcing-windows-10-insider-preview-build-21337/

- Unicode Emoji / UTS #51 version table  
  https://www.unicode.org/reports/tr51/

- Unicode Emoji 13.0 list  
  https://unicode.org/emoji/charts-13.0/emoji-list.html

- CLDR Emoji short names and keywords  
  https://cldr.unicode.org/translation/characters/short-names-and-keywords

- CLDR LDML annotations/search keywords  
  https://unicode.org/reports/tr35/tr35-general.html

### GitHub / reverse engineering

- kyan001/UserDefinedPhraser  
  https://github.com/kyan001/UserDefinedPhraser

- nopdan/rose  
  https://github.com/nopdan/rose

- rose Microsoft Pinyin UDL parser  
  https://github.com/nopdan/rose/blob/main/format/mspy_udl/mspy_udl.go

- rose Microsoft Pinyin UDL pinyin index list  
  https://github.com/nopdan/rose/blob/main/format/mspy_udl/pinyin_list.go

- Nativu5/MSPinyinEmoji  
  https://github.com/Nativu5/MSPinyinEmoji

- studyzy/imewlconverter  
  https://github.com/studyzy/imewlconverter

### 用户报告 / 取证资料

- Microsoft Q&A: alpha / jiantou / xiaoku 特殊候选更新后消失  
  https://learn.microsoft.com/en-us/answers/questions/4069875/where-is-the-greeks-emoji-in-win10-chinese-pinyin

- Microsoft Q&A: 自定义双拼无法出现 Emoji/符号候选  
  https://learn.microsoft.com/zh-cn/answers/questions/5698848/question-5698848

- 小众软件：微软拼音 Emoji 候选无法关闭  
  https://meta.appinn.net/t/topic/86158

- Windows 输入法 UDL/IH 取证结构  
  https://9bie.org/index.php/archives/786/comment-page-1?replyTo=1489

---

# 30. 最后的工程原则

这个项目的重点不是“暴力改系统词库”，而是把调查变成一条可重复验证的链路：

```text
观察现象
  ↓
区分用户数据 / 系统数据
  ↓
解析实际二进制
  ↓
用样本验证字段
  ↓
排除错误候选文件
  ↓
定位 ChsPinyinUDP.lex
  ↓
量化 Emoji 年代断层
  ↓
LEX ↔ CSV 可逆
  ↓
构造最小修改
  ↓
hash / reload / runtime tracing 验证
```

本次调查现在已经完成“最小修改 → 系统替换 → 输入法重新加载 → 候选实际出现”的实机闭环验证。对于已经过这一闭环验证的结论，可以标记为“实机验证”；对于字段官方语义、跨 Windows 版本兼容性、微软内部设计意图等仍未得到直接证据的部分，则继续保持“推断”或“未知”标签，不能把逆向猜测写成微软官方规范。
