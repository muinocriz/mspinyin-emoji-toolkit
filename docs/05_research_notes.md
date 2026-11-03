# 研究备注：已确认 / 待确认

## 已确认

- `ChsPinyinUDP.lex` 是 `mschxudp`。
- 当前样本 3099 条可完整解析。
- 文件存在 offset table；记录包含 UTF-16LE `py` 和 `text`。
- 原始 `py` 有序。
- 未修改 round-trip 可逐字节一致。
- 当前样本中存在大量直接 Emoji 映射。
- 修改后的系统 LEX 已在实机被 `ChsIME` 重新加载并生效；切到英文再切回微软拼音即可刷新。
- `niubi → 🐮🍺` 已作为实际新增候选验证成功。

## 高置信推断

- `candidate_slot=5` 在 Emoji 记录中高度对应第 5 候选。
- `type_id=6` 是新增普通 Emoji 最保守的默认类别值。
- UDP 很可能表示 User Defined Phrase(s)，而不是网络协议 UDP。

## 尚未确认

- `flags_byte` 每一 bit 的官方含义。
- `type_id` 1..9 的完整枚举语义。
- record/header timestamp 的正式定义。
- 当前 Windows 构建是否还有动态/在线来源与 UDP 合并。
- 其他 Windows 构建、Beta 分支、双拼资源是否具有同样加载行为，需要逐版本验证。
