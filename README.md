# 文件批量处理工具

## 项目概述

文件批量处理工具是一个用于批量处理文件的Python应用程序。该工具能够读取多种文件格式（如 `.docx`, `.xlsx`, `.pptx`, `.pdf`, 文本文件, 图片文件等），并通过火山接口模型提取文件的生成时间和主要内容，然后重命名文件为 `yyyymmdd_标题.扩展名` 格式。


## 安装依赖

在运行项目之前，请确保安装了所有必要的依赖库。你可以使用 `pip` 来安装这些依赖库。

```bash
pip install openai python-docx openpyxl python-pptx pymupdf pillow paddlepaddle paddleocr concurrent-futures
```

## 配置文件

项目需要一个配置文件 `pw.py` 来存储火山接口的 API 密钥、基础 URL 和模型名称。请按照以下步骤创建 `pw.py` 文件：

1. 在项目目录中创建一个名为 `pw.py` 的文件。
2. 在 `pw.py` 文件中添加以下内容：

```python
# pw.py

# 火山接口配置
API_KEY = "你的火山接口 API 密钥"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_NAME = "你的火山接口模型名称"
```

请将 `你的火山接口 API 密钥` 和 `你的火山接口模型名称` 替换为你自己的实际值。

## 使用说明

1. **启动应用程序**：
   - 运行 `main.py` 文件。

   ```bash
   python main.py
   ```

2. **选择文件夹**：
   - 点击“选择文件夹并处理文件”按钮。
   - 选择包含要处理的文件的文件夹。支持的文件格式包括 .docx, .xlsx, .pptx, .pdf, 文本文件, 以及图片文件（如 .jpg, .jpeg, .png, .bmp, .gif）。

3.**选择选项**：
  - 在选择文件夹后，会弹出一个选项窗口，询问是否进行 PDF 遍历和分割。
  - 勾选“遍历并分割PDF文件”选项，如果需要对 PDF 文件进行分割。
  - 点击“确认”按钮继续处理文件。

4. **查看进度**：
   - 进度条会显示文件处理的进度。
   - 处理完成后，会弹出一个消息框提示“文件处理已完成”。

5. **查看日志**：
   - 日志文件 `app.log` 会记录所有操作和错误信息。你可以通过查看日志文件来调试和监控应用程序的运行情况。

## 日志记录

日志文件 `app.log` 位于项目根目录下，记录了所有操作和错误信息。你可以通过查看日志文件来调试和监控应用程序的运行情况。

## 代码结构

项目的主要模块包括：

- `main.py`：主应用程序文件，负责用户界面和文件处理流程。
- `file_reader.py`：负责读取不同类型的文件内容。
- `pdf_processor.py`：负责 PDF 文件的遍历和分割。
- `pw.py`：存储火山接口的配置信息。

## 贡献指南

如果你希望为项目做出贡献，请遵循以下步骤：

1. **Fork** 项目仓库。
2. 创建一个新的分支 (`git checkout -b feature/AmazingFeature`)。
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)。
4. 推送到分支 (`git push origin feature/AmazingFeature`)。
5. 打开一个 Pull Request。

