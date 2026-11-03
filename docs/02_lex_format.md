# ChsPinyinUDP.lex 格式（当前样本）

## 文件布局

```text
0x00  8 bytes   ASCII "mschxudp"
0x08  uint32    magic/version-like
0x0C  uint32    version-like
0x10  uint32    offset table start（样本为 0x40）
0x14  uint32    record data start
0x18  uint32    file size
0x1C  uint32    record count
0x20  uint64    header timestamp/version-like field
0x28  3*uint64  reserved/unknown
0x40...         uint32 offset table
...             variable-length records
```

每个 offset 相对于 `record data start`。

## 记录布局

```text
+0x00 uint32 record_magic
+0x04 uint16 phrase_offset
+0x06 uint8  candidate_slot / rank-like byte
+0x07 uint8  flags_byte
+0x08 uint32 type_id
+0x0C uint32 record_timestamp/version-like
+0x10 UTF-16LE py + 00 00
       phrase_offset 指向 text 起点
       UTF-16LE text + 00 00
```

当前样本中：

- `record_magic` 全部为 `0x00100010`。
- `flags_byte` 全部为 `0x13`。
- Emoji 新增记录保守默认使用 `type_id=6`。
- 普通 Emoji 大量使用 `candidate_slot=5`。
- `candidate_slot` 对特殊词类不一定能按“第 N 候选”字面解释；例如存在 22、231。

这些字段的官方语义没有公开，因此文档区分“观察到的事实”和“推测”。
