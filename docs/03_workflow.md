# 工作流

推荐链路：

```text
本机 ChsPinyinUDP.lex
    ↓ LEX_to_CSV
完整 CSV
    ↓ Excel 编辑 / apply_patch
修改后完整 CSV
    ↓ CSV_to_LEX（自动按 py 排序）
ChsPinyinUDP.modified.lex
    ↓ verify
结构 / SHA256 校验
```

## index

`index` 只用于查看，不参与回写。转换器会重建 offset table；新增记录无需手工修改 index。

## 新增 Emoji 推荐列

```text
py              例如 niubi
text            例如 🐮🍺
candidate_slot  5
record_magic    可留空，由模板默认补齐
flags_byte      可留空
type_id         可留空（新增默认 6）
record_timestamp 可留空
```

## 多 Emoji

`text` 是 UTF-16LE 字符串，不限制为单一 code point。`🐮🍺`、`👨‍⚕️`、`🔥文字🔥` 在格式层面都可以存储。
