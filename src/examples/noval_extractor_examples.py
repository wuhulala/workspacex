import os
from workspacex.extractor import noval_extractor


noval_file_path = os.path.join(os.path.dirname(__file__), "data", "noval.txt")

artifacts = noval_extractor.extract(noval_file_path)

print(len(artifacts))

for artifact in artifacts:
    print(artifact.artifact_id)
    print(artifact.content[:100])
    print(artifact.metadata)
    print("-" * 100)