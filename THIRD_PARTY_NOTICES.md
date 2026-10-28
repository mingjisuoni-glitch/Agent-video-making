# 第三方工具、模型与服务

本仓库提供制作方法、一个 HyperFrames 样例和配音接口，**不附带** Qwen3-TTS 模型权重、火山引擎账号或 API 凭据，也不附带音色试听、第三方字体、视频素材和成片。样例通过 `npm install` 另行取得钉住版本的 HyperFrames 与 GSAP。下载者须遵守各依赖的许可、服务协议、音色授权和计费规则。本仓库的[配音非商业限制](LICENSE.md)是额外的项目授权边界，不能用第三方允许商用的条款覆盖。

| 项目 | 本仓库如何使用 | 官方资料与授权核对 |
| --- | --- | --- |
| HyperFrames 0.8.210 | `examples/hello-video` 的开发与渲染依赖，安装进 `node_modules`，不把其源码复制进本仓库。 | [官方仓库](https://github.com/heygen-com/hyperframes)与[文档索引](https://hyperframes.mintlify.app/llms.txt)。npm 元数据和官方仓库标注 Apache-2.0；升级时重新核对。 |
| GSAP 3.14.2 | 样例的确定性动画运行时，安装进 `node_modules`。 | [GSAP 官网](https://gsap.com)和[标准许可](https://gsap.com/standard-license/)。npm 元数据明确不是 Apache/MIT，而是 GSAP 的 Standard “no charge” license；分发和使用须遵守该条款。 |
| Qwen3-TTS | `voice/` 可调用使用者本机安装的 `qwen-tts` 和自行下载的 CustomVoice 模型；本仓库不分发模型、预置音频或依赖包。 | [官方代码仓库](https://github.com/QwenLM/Qwen3-TTS)与[0.6B CustomVoice 模型页](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)。该模型页当前标注 Apache-2.0；改用其他模型时以对应模型页为准。 |
| 火山引擎语音 API | `voice/` 通过用户自己的账号和密钥请求语音合成；合成文本会发送给服务端，真实调用可能计费。 | [HTTP V3 接口文档](https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3?lang=zh)与[计费说明](https://docs.volcengine.com/docs/doubao-voice/billing-overview?lang=zh)。具体服务协议、音色权限与价格以用户实际开通的资源为准。 |

可选 Agent Skills 同样不随本仓库再分发。其固定来源、安装渠道与许可证状态记录在 [`skills/manifest.json`](skills/manifest.json) 和 [`docs/skill-sources.md`](docs/skill-sources.md)。其中 `NOASSERTION` 表示未作许可证断言，不代表允许复制或商用。

使用自行添加的声音、参考音频、字体或画面素材时，应确认有权使用并按原始许可保留署名或其他要求。配音服务与模型的授权范围不等于对任何人物声音或身份的使用许可。
