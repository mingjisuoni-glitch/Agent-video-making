# 20-second voiced demo

This example proves the repository's audio → pause-grouped captions → caption-boundary scenes → strict HyperFrames check path. Generated speech, captions, dependencies, and composition output are deliberately ignored by Git.

Prerequisites: Python package installed with `pip install -e .`, Node.js 22, `espeak-ng`, FFmpeg, and ffprobe.

```bash
bash examples/voiced-demo/scripts/build.sh
```

The script creates exactly 20 seconds of local narration, six pause groups, three scenes whose cuts fall on caption-group starts, and `examples/voiced-demo/generated/check-report.json`. It runs `hyperframes check --strict --json` but does not render an MP4.
