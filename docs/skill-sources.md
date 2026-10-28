# Skill 来源、安装渠道与限制

本项目不会把所有第三方 Skill 的完整文件复制进仓库。原因不是“只给名称就算完成”，而是这些 Skill 来自不同作者、许可证和运行平台；有些还依赖宿主工具或私有插件，复制一个 `SKILL.md` 并不能复制其能力。

机器可读的来源、固定提交、文件路径和 SHA-256 位于 [`skills/manifest.json`](../skills/manifest.json)。运行下面的命令只做校验和本机检查，不会执行或下载未知代码：

```bash
python -m tools.fetch_skills --validate-only --json
python -m tools.fetch_skills --check
```

## 先装哪一个

`hyperframes` 是本项目制作与检查视频的必需 Skill，其余全部按任务选装。先完成：

```bash
npx hyperframes@0.8.210 skills update hyperframes
```

然后重启 Agent 会话，让新安装的 Skill 被重新发现。只阅读规则、模板或填写制作方案时，不需要安装可选 Skill。

## 可公开取得的 Skill

| Skill | 用途 | 上游与安装渠道 | 许可证/注意事项 |
| --- | --- | --- | --- |
| `hyperframes` | HyperFrames 总路由与制作工作流 | `npx hyperframes@0.8.210 skills update hyperframes`；[上游仓库](https://github.com/heygen-com/hyperframes) | Apache-2.0；本项目固定 CLI 0.8.210。 |
| `cinematic-director` | 剧情、镜头调度、连续性与去 PPT 化 | [项目验收版本](https://github.com/cajias/agentic-video-skills/tree/master/plugins/cinematic-director/skills/cinematic-director)；[最新独立上游](https://github.com/wuwangzhang1216/DirectorSKILL) | MIT。独立上游可能比项目验收版本更新，模式和输出结构可能变化。 |
| `video-shotcraft` | 产品、页面、软件展示视频 | `npx skills add https://github.com/Vincentwei1021/video-shotcraft`；[上游仓库](https://github.com/Vincentwei1021/video-shotcraft) | Apache-2.0。 |
| `h3-prompt-writing` | MiniMax H3 提示词设计 | `npx skills add https://github.com/MiniMax-AI/MiniMax-H3 --skill h3-prompt-writing`；[官方仓库](https://github.com/MiniMax-AI/MiniMax-H3) | MiniMax H3 Community License，不是 MIT/Apache；安装和商用前阅读[完整协议](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)。 |
| `motion-design` | 运动原则、参数和动画系统 | `npx skills add https://github.com/soilmass/motion-design-agent --skill motion-design`；[上游仓库](https://github.com/soilmass/motion-design-agent) | MIT。 |
| `remotion` | Remotion 相关动效参考 | 安装完整 [motion-design-agent](https://github.com/soilmass/motion-design-agent)，子 Skill 位于 `skills/remotion` | Skill 文件是 MIT；Remotion 运行时适用其自己的许可证，二者不能混为一谈。 |
| `video-editing` | 实拍、录屏、FFmpeg 与后期流程 | `npx skills add https://github.com/affaan-m/ECC --skill video-editing`；[ECC 官方仓库](https://github.com/affaan-m/ECC) | MIT。只从 ECC 官方渠道安装，避免同名镜像。 |

`npx skills add` 默认取得上游当前版本，不等于安装清单中的固定提交。需要复现实验环境时，应按 `skills/manifest.json` 的 `repo`、`commit` 和 `skill_path` 检出文件，并核对 `skill_sha256`；需要最新功能时才使用上表命令，并在升级后重新验收视频流程。

## 不能用普通下载命令补齐的项

| Skill | 实际状态 | 下载者该怎么做 |
| --- | --- | --- |
| `imagegen` | Codex 平台内置 Skill，主要能力来自宿主提供的 `image_gen` 工具。[参考 Skill 文件](https://github.com/openai/skills/blob/main/skills/.system/imagegen/SKILL.md)所在仓库已标为弃用目录。 | 使用带 Image Gen 能力的 Codex；复制 `SKILL.md` 到 DeepSeek、Qwen 等 Agent 并不会获得图像生成工具。其他 Agent 应对接自己的图像模型/API，并保持本项目的素材审批规则。 |
| `minimax-h3` | 当前维护者机器上的是 Codex 私有 MCP 插件，没有已核验的公开安装包。 | 不要依赖该私有插件作为项目必需项。可自行配置 MiniMax API，或评估 MiniMax 公开的 [`h3-video` Skill](https://github.com/MiniMax-AI/cli/tree/main/cli/skill/h3-video)；它不是本机插件的等价复制品。付费提交前必须自行实现确认、防重复扣费和任务对账。 |
| `reverse-video-prompts` | 项目当前测试版本只存在于本地；没有找到文件与行为均一致且许可证清楚的公开上游。 | 这是可选能力，可以不安装。若改用同名或近似社区 Skill，先核对许可证、输出格式和平台适配，不要把近似项目当成原版本。 |

## 其他 Agent 能否使用

DeepSeek、豆包、Qwen、WorkBuddy 等 Agent 可以读取本仓库的方法、规则和模板，但是否能直接调用 Skill 取决于它们是否支持 `SKILL.md` 目录、工具调用和本地命令。最少需要人工或适配层完成三件事：

1. 先配置 Node.js、FFmpeg、Chrome/Chromium 与 HyperFrames 环境。
2. 把所选 Skill 的完整目录安装到该 Agent 能发现的位置，而不是只复制 `SKILL.md` 文件名。
3. 为 `imagegen`、MiniMax H3、配音等能力配置该 Agent 实际可调用的工具/API；指令文件本身不包含账号、模型权重或远程服务权限。

无论使用哪个 Agent，项目中的四项确认、制作方案批准、配音限制、素材许可和渲染前检查都不会因更换 Agent 而自动失效。

## 安全与许可证边界

- 安装第三方 Skill 前先阅读仓库内容、固定提交和许可证；不要自动执行陌生仓库脚本。
- 本仓库只登记渠道，不重新授权第三方 Skill、模型、API、素材或生成结果。
- `NOASSERTION` 表示本项目没有足够依据替第三方作出许可证结论，不表示“无限制使用”。
- 模型/API 的商用范围由各自条款决定。项目中“仅配音不可用于商业用途”的说明，不会覆盖 MiniMax H3、Remotion、素材或其他服务的独立条款。
