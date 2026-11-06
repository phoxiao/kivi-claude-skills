# 写入 AGENTS.md / CLAUDE.md 的规则片段

## 写入方式

1. 找到项目的规则文件。两个都有时，写到被另一个引用的那个，只写一处。
2. 文件里已有 UI 规则时，合并进去并去掉重复项，保持文件原有语言。
3. 默认用完整版。规则文件已经很长时用一句版。
4. 项目面向 C 端新手时，把「面向专业用户」一句改成实际受众。

某个模型执行不稳定时，把第一条的 `Avoid` 换成 `Never add`，或在具体任务里再强调一次。

## 一句版

```markdown
- Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining.
```

## 完整版

```markdown
## UI/UX

- Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining.
- This UI is for professional users: write the interface as a tool, not a manual.
- Every label, icon, badge, card, and description must serve a clear user purpose. Say each piece of information once, in the place closest to where it is used.
- Use one level of container. Group with whitespace and alignment.
- Put secondary details behind progressive disclosure.
- Keep what prevents mistakes: error and empty states with their cause and next step, explicit values instead of blanks (every row in a status column), consequences of destructive actions, units and time ranges, form labels, and accessible names for icon-only controls.
- Keep destructive actions apart from routine ones and label them with the action and its target.
- When simplifying, keep to the facts the page already states.
- Build the features requested; list further ideas separately for the user to decide.
- Match the typography, spacing, colors, and components of existing screens.
- Before adding a UI element, check whether removing or simplifying an existing one achieves the same goal.
```
