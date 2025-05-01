> [!IMPORTANT]
> **此项目还在不断完善中，目前只能实现一些简单的、特定的功能。**
> 具体请参见下文。

<div align="center">
<img src="icon.png" alt="插件图标" width="18%">
<h1>EasiControl</h1>


[![星标](https://img.shields.io/github/stars/Yersmagit/cw-easi-control?style=for-the-badge&color=orange&label=星标)](https://github.com/Yersmagit/cw-easi-control)
[![开源许可](https://img.shields.io/badge/license-MIT-darkgreen.svg?label=开源许可证&style=for-the-badge)](https://github.com/Yersmagit/cw-easi-control)
[![下载量](https://img.shields.io/github/downloads/Yersmagit/cw-easi-control/total.svg?label=下载量&color=green&style=for-the-badge)](https://github.com/Yersmagit/cw-easi-control)

</div>

## 介绍

EasiControl 是一个 ClassWidgets 插件，可以方便地实现 ClassWidgets 的自动化控制。


### 截图
![截图1](none)

### 特性

#### 已实现：
- 配合插件 [LX-Music-Lyrics-Plugin](https://github.com/laoshuikaixue/cw-LX-music-lyrics-plugin) 自动改变您的 ClassWidgets 小组件类型
- 特定活动时显示特定的小组件
- ...

#### 待实现：
- 高度自定义执行特定事件的条件
- 高度自定义特定条件下执行的事件
- ...

## 使用

> [!WARNING]
> **本插件运行具有较高逻辑性，请不要随意更改目录文件内容！**

你可以在下载插件后，打开`main.py`，在文件开头找到并修改如下常量以实现自定义。
```python
# --常量定义--

# 用于显示特定小组件的课程名称，如"课间", "暂无课程", "自习"
LESSON_TRIGGERS = ["Subject_1", "Subiect_2", "Subiect_3"]  # 可扩展的触发文本列表
# 在上述特定课程切换的小组件名称。当课程为 LESSON_TRIGGERS 中的课程时，显示目标组件；否则，显示原始组件
WIDGET_TARGET_PAIR = ("example-1.ui", "example-2.ui")  # (原始组件，目标组件)
```

将来，我们会给此内容添加图形交互界面。

## 其它
### 许可证
本插件采用了 MIT 许可证，详情请查看 [LICENSE](LICENSE) 文件。
Copyright © 2025 Yersmagit.

### 鸣谢

#### 贡献者
Thanks goes to these wonderful people:
[![Contributors](http://contrib.nn.ci/api?repo=Yersmagit/cw-easi-control)](https://github.com/Yersmagit/cw-easi-control/graphs/contributors)

#### 使用的资源

- [资源1](https://example.com)
- [资源2](https://example.com)
