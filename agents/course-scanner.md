# 课程扫描 Agent（course-scanner）

## 角色
把任意专业的课程资源目录变成一份可编辑的 `course-config.json` 草稿。

## 输入
- 资源根目录：`{{RESOURCES_DIR}}`
- 平台目录：`{{PLATFORM_DIR}}`

## 步骤
1. 先运行：
   ```
   python bot.py scan --platform <平台目录> --resources <资源目录>
   ```
2. 检查生成的 `course-config.json`：
   - 每个一级目录 = 一门课；如果某目录其实是多门课（如「构成设计基础」下有 3 门子课），改成 3 条课程配置，root 指向子目录。
   - `type`：有视频 → `video`；只有 PDF/图片 → `gallery`；B 站 → `bilibili`。
   - `modules`：`stage`（第一层目录当模块）或 `flat`（全部课时一个模块）。
3. 补齐 `title`、`subtitle`、`description`、`category`、`tags`；分类要和专业方向一致，不要都叫「专业核心」。
4. 检查视频文件名：纯英文/纯页码的课程，标记为需要 `content-optimizer` 处理命名与翻译。
5. 运行 `python bot.py build --platform <平台目录>` 验证能生成数据。

## 输出
- 更新后的 `course-config.json`
- 扫描报告：课程数、课时数、时长、类型、缺字幕/缺资料情况
- 建议先跑哪个 Agent（内容优化 / UI 调整）
