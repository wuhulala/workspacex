# Artifact 表单优化说明

## 优化内容总结

本次优化主要针对各种 Artifact 类型的表单设计和处理流程进行了改进，主要包括以下内容：

1. **ArxivArtifact 优化**：
   - 支持直接输入 arXiv ID 或完整 URL
   - 添加 URL 解析功能，自动提取 arXiv ID
   - 增强错误处理和验证机制

2. **PDF 处理能力增强**：
   - 创建专门的 PDFArtifact 类
   - 支持本地文件和 URL 两种输入方式
   - 增强错误处理和超时控制

3. **Web 页面处理**：
   - 创建 WebPagesArtifact 类处理单个网页
   - 创建 WebPageCollection 类处理多个网页集合
   - 支持 HTML 内容和处理后的文本内容

4. **表单定义系统**：
   - 创建统一的表单定义类
   - 为每种 Artifact 类型定义专门的表单
   - 支持字段验证、依赖关系和高级选项

5. **工厂类系统**：
   - 创建 ArtifactFactory 用于统一创建各类 Artifact
   - 支持根据表单数据自动创建相应的 Artifact 实例
   - 提供统一的处理接口

## 使用方法

### 创建 arXiv 论文 Artifact

```python
from workspacex import ArtifactType
from workspacex.artifacts.factory import ArtifactFactory

# 方法一：直接使用 arXiv ID
form_data = {
    "arxiv_id_or_url": "2307.09288"
}

# 方法二：使用完整 URL
form_data = {
    "arxiv_id_or_url": "https://arxiv.org/abs/2307.09288"
}

# 创建 Artifact
arxiv_artifact = ArtifactFactory.create_artifact(ArtifactType.ARXIV, form_data)

# 处理 Artifact
await ArtifactFactory.process_artifact(arxiv_artifact)
```

### 创建 PDF Artifact

```python
from workspacex import ArtifactType
from workspacex.artifacts.factory import ArtifactFactory

# 方法一：从 URL 创建
form_data = {
    "source_type": "url",
    "url": "https://example.com/document.pdf"
}

# 方法二：从本地文件创建
form_data = {
    "source_type": "file",
    "file_path": "/path/to/local/file.pdf"
}

# 创建 Artifact
pdf_artifact = ArtifactFactory.create_artifact(ArtifactType.PDF, form_data)

# 处理 Artifact
await ArtifactFactory.process_artifact(pdf_artifact)
```

### 创建 Web 页面 Artifact

```python
from workspacex import ArtifactType
from workspacex.artifacts.factory import ArtifactFactory

# 创建单个网页 Artifact
form_data = {
    "url": "https://example.com",
    "title": "Example Website"  # 可选
}

web_artifact = ArtifactFactory.create_artifact(ArtifactType.WEB_PAGES, form_data)

# 创建网页集合
form_data = {
    "urls": "https://example.com\nhttps://example.org",
    "collection_name": "Example Collection"
}

collection = ArtifactFactory.create_artifact(ArtifactType.WEB_PAGES, form_data)

# 处理 Artifact
await ArtifactFactory.process_artifact(web_artifact)
await ArtifactFactory.process_artifact(collection)
```

### 使用表单定义

```python
from workspacex import ArtifactType
from workspacex.artifacts.form_definitions import get_form_definition

# 获取特定类型的表单定义
form_def = get_form_definition(ArtifactType.ARXIV)

# 查看表单信息
print(f"表单标题: {form_def.title}")
print(f"表单描述: {form_def.description}")

# 查看字段信息
for field in form_def.fields:
    print(f"字段: {field.name} ({field.label})")
    print(f"  类型: {field.type}")
    print(f"  描述: {field.description}")
    if field.validation and field.validation.required:
        print("  必填字段")
```

## 扩展方法

如果需要添加新的 Artifact 类型，请按照以下步骤操作：

1. 在 `ArtifactType` 枚举中添加新类型
2. 创建新的 Artifact 类，继承自 `Artifact` 基类
3. 在 `form_definitions.py` 中为新类型创建表单定义
4. 在 `ArtifactFactory` 中注册新类型并实现创建方法

例如，添加一个新的 `CSVArtifact` 类型：

```python
# 1. 在 ArtifactType 中添加
class ArtifactType(Enum):
    # 现有类型...
    CSV = "CSV"

# 2. 创建新的 Artifact 类
class CSVArtifact(Artifact):
    def __init__(self, file_path: str, **kwargs):
        artifact_id = f"csv_{Path(file_path).stem}"
        metadata = {"file_path": file_path}
        super().__init__(artifact_id=artifact_id, content="", artifact_type=ArtifactType.CSV, metadata=metadata, **kwargs)
        
    # 实现必要的方法...

# 3. 创建表单定义
CSV_FORM = ArtifactFormDefinition(
    artifact_type=ArtifactType.CSV,
    title="CSV Data",
    description="Create an artifact from a CSV file",
    fields=[
        FormField(
            name="file_path",
            label="CSV File",
            type=FormFieldType.FILE,
            description="Upload a CSV file",
            validation=FormFieldValidation(required=True),
            order=1
        )
    ],
    submit_label="Process CSV",
    success_message="CSV file processed successfully"
)

# 4. 注册到工厂类
ArtifactFactory.register_artifact_class(ArtifactType.CSV, CSVArtifact)
```

## 运行示例

可以运行 `artifact_examples.py` 脚本来查看各种 Artifact 的创建和处理示例：

```bash
python -m workspacex.examples.artifact_examples
```

该脚本包含了创建各种类型 Artifact 的示例，以及一个交互式示例，可以根据用户输入创建 Artifact。
