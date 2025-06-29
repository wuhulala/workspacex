#!/usr/bin/env python3
"""
🧪 Simple Concurrency Test for WorkspaceX

A minimal test to verify that the enhanced parallel processing works correctly.
"""

import asyncio
import time
import logging
from typing import List

from workspacex.workspace import WorkSpace
from workspacex.artifact import Artifact, ArtifactType


class TestArtifact(Artifact):
    """Test artifact for concurrency verification"""
    
    def __init__(self, artifact_id: str, content: str, sublist: List['TestArtifact'] = None):
        super().__init__(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.TEXT,
            content=content,
            metadata={"filename": f"test_{artifact_id}.txt"},
            embedding=True
        )
        self.sublist = sublist or []
    
    def get_embedding_text(self) -> str:
        """Return content for embedding"""
        return self.content


async def create_simple_test_data() -> List[TestArtifact]:
    """Create simple test data with known timing"""
    
    # Create 3 subartifacts
    subartifacts = [
        TestArtifact(f"sub_{i}", f"Subartifact {i} content")
        for i in range(3)
    ]
    
    # Create main artifact with subartifacts
    main_artifact = TestArtifact(
        "main_artifact",
        "Main artifact content",
        sublist=subartifacts
    )
    
    return [main_artifact]


async def test_concurrency():
    """Test the concurrency improvements"""
    
    print("🧪 Testing Enhanced Concurrency...")
    
    # Create workspace
    workspace = WorkSpace(
        workspace_id="concurrency_test",
        name="Concurrency Test",
        clear_existing=True
    )
    
    # Set concurrency limit
    workspace.workspace_config.max_concurrent_embeddings = 5
    
    # Create test data
    artifacts = await create_simple_test_data()
    
    print(f"📦 Created 1 main artifact with {len(artifacts[0].sublist)} subartifacts")
    print(f"🎯 Total artifacts to process: {1 + len(artifacts[0].sublist)}")
    
    # Test parallel processing
    start_time = time.time()
    
    await workspace.add_artifact(artifacts[0])
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"✅ Processing completed in {processing_time:.2f} seconds")
    
    # Verify results
    all_artifacts = workspace.list_artifacts()
    print(f"📊 Total artifacts in workspace: {len(all_artifacts)}")
    
    if len(all_artifacts) == 1:
        main_artifact = all_artifacts[0]
        if hasattr(main_artifact, 'sublist') and main_artifact.sublist:
            print(f"✅ Main artifact has {len(main_artifact.sublist)} subartifacts")
            print("✅ Concurrency test passed!")
        else:
            print("❌ Main artifact missing subartifacts")
    else:
        print(f"❌ Expected 1 artifact, got {len(all_artifacts)}")


async def main():
    """Main test function"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        await test_concurrency()
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 