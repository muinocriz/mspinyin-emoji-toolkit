# 系统替换与验证

此部分属于实验步骤，重点是可恢复。

1. 备份当前系统 `ChsPinyinUDP.lex`。
2. 校验 `modified.lex` 结构。
3. 记录修改文件 SHA256。
4. 如确需替换系统目录，只对目标文件临时调整 TrustedInstaller/ACL，不要递归修改整个 CHS 目录。
5. 替换后立即比较系统文件 SHA256。
6. 切换到英文输入法，再切回“中文（简体）- 微软拼音”。本次实机测试中，这一步已经足以触发 `ChsIME` 重新加载词库并让新增候选生效，无需重启电脑。
7. 再次比较 SHA256，确认系统文件没有被保护机制恢复。
8. 确认当前使用的是全拼还是双拼；双拼可能使用另一套 UDP 资源。
9. 若其他 Windows 版本仍不生效，再用 Process Monitor 等方式确认 `ChsIME.exe` 实际读取路径。

PowerShell 复制使用 `Copy-Item -Force`；`copy /Y` 是 CMD 语法。

Windows Update、SFC 或组件服务可能恢复受保护文件，因此系统 LEX 修改适合研究验证，不适合作为长期稳定部署方案。
