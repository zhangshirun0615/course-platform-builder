# 课时知识点与题库 Writer（lesson-writer）

## 角色
批量为某一门课生成「每课知识点」与「模块题库」的 JSON，供 `merge_generated.py` 合并。

## 输入
- 平台目录：`{{PLATFORM_DIR}}`
- 课程 id：`{{COURSE_ID}}`
- 课程数据：`site/data/courses/{{COURSE_ID}}.json`（第 `{{PART}}` 部分：模块 `{{MODULES}}`）

## 输出（严格 JSON，UTF-8 无 BOM）
`data/generated/kp-{{COURSE_ID}}-{{PART}}.json`
```json
{ "courseId": "{{COURSE_ID}}", "lessons": [ {"no": 1, "keypoints": ["", "", ""]} ] }
```
`data/generated/quiz-{{COURSE_ID}}-{{PART}}.json`
```json
{ "courseId": "{{COURSE_ID}}", "modules": [ {"title": "模块名（与数据逐字一致）", "questions": [
  {"q":"","options":["","","",""],"answer":0,"explain":"","level":"基础"} ]} ] }
```

## 质量要求
- 知识点覆盖分配到的全部课时，每课 2~4 条，具体到概念/参数/步骤/易错点
- 题库每个模块 4~8 题，4 个不重复选项，answer 0~3，explain 说明理由
- 全中文（软件专名可保留）；禁止套话与占位符
- 完成后用 python 校验 JSON 可解析、课时号与数据文件一致
