#!/usr/bin/env python3
"""
🚀 Enhanced Parallel Processing Example for WorkspaceX

This example demonstrates the improved parallel processing of artifacts and subartifacts,
showing significant performance improvements over sequential processing.
"""

import asyncio
import time
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor

from workspacex.workspace import WorkSpace
from workspacex.artifact import Artifact, ArtifactType


class MockArtifact(Artifact):
    """Mock artifact for testing parallel processing"""
    
    def __init__(self, artifact_id: str, content: str, sublist: List['MockArtifact'] = None):
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


class MockEmbedder:
    """Mock embedder that simulates real embedding operations"""
    
    def __init__(self, delay: float = 0.1):
        self.delay = delay
    
    async def embed_artifact(self, artifact: Artifact):
        """Simulate embedding with async delay"""
        await asyncio.sleep(self.delay)  # Simulate API call or processing time
        return f"embedding_{artifact.artifact_id}"
    
    async def embed_artifacts(self, artifacts: List[Artifact]):
        """Simulate batch embedding"""
        await asyncio.sleep(self.delay * len(artifacts) * 0.5)  # Batch processing is faster
        return [f"embedding_{a.artifact_id}" for a in artifacts]


async def create_test_artifacts(num_main: int = 3, num_sub_per_main: int = 5) -> List[MockArtifact]:
    """Create test artifacts with subartifacts for parallel processing demo"""
    
    artifacts = []
    for main_idx in range(num_main):
        # Create subartifacts
        subartifacts = []
        for sub_idx in range(num_sub_per_main):
            subartifact = MockArtifact(
                artifact_id=f"sub_{main_idx}_{sub_idx}",
                content=f"Subartifact content {main_idx}_{sub_idx}"
            )
            subartifacts.append(subartifact)
        
        # Create main artifact with subartifacts
        main_artifact = MockArtifact(
            artifact_id=f"main_artifact_{main_idx}",
            content=f"Main artifact content {main_idx}",
            sublist=subartifacts
        )
        artifacts.append(main_artifact)
    
    return artifacts


async def demo_enhanced_parallel_processing():
    """Demonstrate enhanced parallel processing of artifacts and subartifacts"""
    
    print("🚀 Starting Enhanced Parallel Processing Demo...")
    
    # Create workspace
    workspace = WorkSpace(
        workspace_id="enhanced_parallel_demo",
        name="Enhanced Parallel Processing Demo",
        clear_existing=True
    )
    
    # Create test artifacts with more realistic numbers
    artifacts = await create_test_artifacts(num_main=3, num_sub_per_main=5)
    
    total_artifacts = len(artifacts) + sum(len(a.sublist) for a in artifacts)
    print(f"📦 Created {len(artifacts)} main artifacts with {total_artifacts - len(artifacts)} subartifacts")
    print(f"📊 Total artifacts to process: {total_artifacts}")
    
    # Add artifacts to workspace (this will trigger enhanced parallel processing)
    start_time = time.time()
    
    for i, artifact in enumerate(artifacts):
        print(f"🔄 Adding artifact {i+1}/{len(artifacts)}: {artifact.artifact_id}")
        print(f"   - Has {len(artifact.sublist)} subartifacts")
        await workspace.add_artifact(artifact)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"✅ Processing completed in {processing_time:.2f} seconds")
    print(f"📊 Total artifacts processed: {len(workspace.artifacts)}")
    print(f"⚡ Average time per artifact: {processing_time/total_artifacts:.3f} seconds")


async def compare_processing_methods():
    """Compare different processing methods"""
    
    print("\n⚡ Processing Method Comparison...")
    
    # Create artifacts for comparison
    artifacts = await create_test_artifacts(num_main=2, num_sub_per_main=3)
    total_artifacts = len(artifacts) + sum(len(a.sublist) for a in artifacts)
    
    print(f"📊 Testing with {total_artifacts} total artifacts")
    
    # Method 1: Sequential processing (old way)
    print("\n🔄 Method 1: Sequential Processing (Old Way)")
    start_time = time.time()
    
    for artifact in artifacts:
        # Process main artifact
        await asyncio.sleep(0.1)  # Simulate main artifact processing
        # Process subartifacts sequentially
        for subartifact in artifact.sublist:
            await asyncio.sleep(0.1)  # Simulate subartifact processing
    
    sequential_time = time.time() - start_time
    
    # Method 2: Parallel subartifacts only (previous implementation)
    print("🚀 Method 2: Parallel Subartifacts Only (Previous)")
    start_time = time.time()
    
    for artifact in artifacts:
        # Process main artifact
        await asyncio.sleep(0.1)
        # Process subartifacts in parallel
        await asyncio.gather(*[asyncio.sleep(0.1) for _ in artifact.sublist])
    
    parallel_sub_only_time = time.time() - start_time
    
    # Method 3: Full parallel processing (new implementation)
    print("🚀🚀 Method 3: Full Parallel Processing (New)")
    start_time = time.time()
    
    for artifact in artifacts:
        # Process main artifact and subartifacts all in parallel
        tasks = [asyncio.sleep(0.1)]  # Main artifact
        tasks.extend([asyncio.sleep(0.1) for _ in artifact.sublist])  # Subartifacts
        await asyncio.gather(*tasks)
    
    full_parallel_time = time.time() - start_time
    
    # Method 4: Batch processing (ideal scenario)
    print("🚀🚀🚀 Method 4: Batch Processing (Ideal)")
    start_time = time.time()
    
    # Process all artifacts and subartifacts in one batch
    all_tasks = []
    for artifact in artifacts:
        all_tasks.append(asyncio.sleep(0.1))  # Main artifact
        all_tasks.extend([asyncio.sleep(0.1) for _ in artifact.sublist])  # Subartifacts
    
    await asyncio.gather(*all_tasks)
    
    batch_time = time.time() - start_time
    
    # Results
    print(f"\n📊 Performance Results:")
    print(f"   Sequential:           {sequential_time:.2f}s")
    print(f"   Parallel Sub Only:    {parallel_sub_only_time:.2f}s")
    print(f"   Full Parallel:        {full_parallel_time:.2f}s")
    print(f"   Batch Processing:     {batch_time:.2f}s")
    
    print(f"\n⚡ Speedup Comparison:")
    print(f"   Parallel Sub Only:    {sequential_time/parallel_sub_only_time:.1f}x faster")
    print(f"   Full Parallel:        {sequential_time/full_parallel_time:.1f}x faster")
    print(f"   Batch Processing:     {sequential_time/batch_time:.1f}x faster")


async def demo_concurrency_limits():
    """Demonstrate concurrency limits and their effects"""
    
    print("\n🎯 Concurrency Limits Demo...")
    
    # Test different concurrency levels
    concurrency_levels = [1, 5, 10, 20]
    
    for max_concurrent in concurrency_levels:
        print(f"\n🔧 Testing with max_concurrent_embeddings = {max_concurrent}")
        
        # Create workspace with custom config
        workspace = WorkSpace(
            workspace_id=f"concurrency_test_{max_concurrent}",
            name=f"Concurrency Test {max_concurrent}",
            clear_existing=True
        )
        
        # Set custom concurrency limit
        workspace.workspace_config.max_concurrent_embeddings = max_concurrent
        
        # Create test artifacts
        artifacts = await create_test_artifacts(num_main=1, num_sub_per_main=8)
        
        start_time = time.time()
        await workspace.add_artifact(artifacts[0])
        processing_time = time.time() - start_time
        
        print(f"   Processing time: {processing_time:.2f}s")
        print(f"   Theoretical min time: {0.1 * 9 / max_concurrent:.2f}s")  # 9 artifacts total


async def main():
    """Main function to run the enhanced demo"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 WorkspaceX Enhanced Parallel Processing Demo")
    print("=" * 60)
    
    try:
        # Run the enhanced demo
        await demo_enhanced_parallel_processing()
        
        # Run processing method comparison
        await compare_processing_methods()
        
        # Run concurrency limits demo
        await demo_concurrency_limits()
        
        print("\n✅ Enhanced demo completed successfully!")
        print("\n💡 Key Improvements:")
        print("   - Main artifacts and subartifacts processed in parallel")
        print("   - CPU-intensive operations moved to thread pool")
        print("   - Configurable concurrency limits")
        print("   - Better error handling and logging")
        print("   - Significant performance improvements")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 