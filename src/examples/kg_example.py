
"""
Acknowledgement: This example is inspired by the LightRAG project.
Thanks to the authors for their excellent work on knowledge graph (KG) construction in RAG scenarios and for open-sourcing their implementation 🙏
@2025-08-14

Official citation (please cite if used in academic or product contexts):
@article{guo2024lightrag,
title={LightRAG: Simple and Fast Retrieval-Augmented Generation},
author={Zirui Guo and Lianghao Xia and Yanhua Yu and Tu Ao and Chao Huang},
year={2024},
eprint={2410.05779},
archivePrefix={arXiv},
primaryClass={cs.IR}
}

pip install lightrag-hku==1.4.6
"""

import asyncio
# setup_logger("lightrag", level="DEBUG")
import logging
import os
import traceback

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.ollama import ollama_embed
from lightrag.utils import EmbeddingFunc

from workspacex import WorkSpace
from workspacex.utils.logger import logger
from workspacex.utils.rag_utils import call_llm_async

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
WORKING_DIR = "./rag_storage"
import shutil



def delete_working_dir(dir_path: str) -> None:
    """
    Delete the specified working directory and all its contents.

    Args:
        dir_path (str): The path to the directory to be deleted.

    Returns:
        None
    """
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            logger.info(f"🗑️ Successfully deleted directory: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to delete directory {dir_path}: {e}")
    else:
        logger.warning(f"Directory does not exist: {dir_path}")

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)


async def llm_model_func(
        prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await call_llm_async(
        prompt=prompt,
        system_prompt=system_prompt,
        llm_config={
            "timeout": 30,
            "max_tokens": 4096,
            "temperature": 0,
            "extra_body": {
                "top_k": 20,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        }
    )
    # return await openai_complete_if_cache(
    #     os.getenv("LLM_MODEL"),
    #     prompt,
    #     timeout=30,
    #     system_prompt=system_prompt,
    #     history_messages=history_messages,
    #     api_key=os.getenv("LLM_API_KEY"),
    #     base_url=os.getenv("LLM_BASE_URL"),
    #     **kwargs
    # )


async def custom_embedding_func(texts: list[str]) -> np.ndarray:
    return await ollama_embed(
        texts,
        embed_model=os.getenv("WORKSPACEX_EMBEDDING_MODEL"),
        host=os.getenv("WORKSPACEX_EMBEDDING_API_BASE_URL")
    )


async def initialize_rag(workspace_id):
    rag = LightRAG(
        working_dir=WORKING_DIR,
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.getenv("WORKSPACEX_EMBEDDING_DIMENSIONS", "1024")),
            func=custom_embedding_func
        ),
        workspace=workspace_id,
        llm_model_func=llm_model_func,
        llm_model_max_async=1
    )
    # IMPORTANT: Both initialization calls are required!
    await rag.initialize_storages()  # Initialize storage backends
    await initialize_pipeline_status()  # Initialize processing pipeline
    return rag


async def main():
    try:

        ws_id = "novel_example_workspace_v9"
        delete_working_dir(WORKING_DIR + "/" + ws_id)
        ws = WorkSpace.from_local_storages(ws_id)
        logger.info(f"Workspace: {ws} initialized")
        # Initialize RAG instance
        rag = await initialize_rag(ws_id)
        logger.info(f"rag initialized..")

        for artifact in ws.artifacts:
            if artifact.sublist:
                for sub_artifact in artifact.sublist:
                    content = ws.get_file_content_by_artifact_id(sub_artifact.artifact_id, artifact.artifact_id)
                    logger.info(f"Inserting artifact: {sub_artifact.artifact_id}")
                    await rag.ainsert(content, ids=sub_artifact.artifact_id)

        # Perform hybrid search
        mode = "hybrid"
        logger.info(
            await rag.aquery(
                "韩长老和叶凡的恩怨情仇",
                param=QueryParam(mode=mode)
            )
        )

    except Exception as e:
        logger.error(f"An error occurred: {e}, trace is {traceback.format_exc()}")
    finally:
        if rag:
            await rag.finalize_storages()


if __name__ == "__main__":
    asyncio.run(main())
