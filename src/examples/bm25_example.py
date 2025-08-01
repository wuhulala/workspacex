from workspacex.artifact import Artifact, ArtifactType
from workspacex.reranker.base import RerankConfig
from workspacex.reranker.bm25 import BM25RerankRunner

# 创建配置
config = RerankConfig(
    provider="bm25",
    base_url="",  # BM25 不需要 URL
    k1=1.2,      # 可选的 BM25 参数
    b=0.75       # 可选的 BM25 参数
)

# 创建重排序器
reranker = BM25RerankRunner(config)

# 运行重排序
documents = [
    Artifact(artifact_type=ArtifactType.TEXT, content="你好"),
    Artifact(artifact_type=ArtifactType.TEXT, content="我很好"),
    Artifact(artifact_type=ArtifactType.TEXT, content="谢谢你"),
    Artifact(artifact_type=ArtifactType.TEXT, content="很高兴遇到你"),
]

results = reranker.run("你好", documents, score_threshold=0)
for result in results:
    print(f"{result.artifact.content}: {result.score}")