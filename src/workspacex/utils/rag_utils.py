import os
import time
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
import logging
from langfuse.langchain import CallbackHandler



def call_llm(prompt: str, model_name: str = None, llm_config: dict[str, Any] = {}) -> str:
    langfuse_handler = CallbackHandler()

    if os.environ.get('LLM_API_KEY') is None:
        raise ValueError("LLM_API_KEY is not set")
    if os.environ.get('LLM_BASE_URL') is None:
        raise ValueError("LLM_BASE_URL is not set")
    
    try:
        start_time = time.time()
        llm_model = get_llm_model(model_name, llm_config)
        response = llm_model.invoke(
            [{"role": "user", "content": prompt}],
                                    config=RunnableConfig(callbacks=[langfuse_handler]))
        use_time = time.time() - start_time
        logging.info(f"LLM response[{len(prompt)} chars -> use {use_time:.2f} s] result is: {response.content} 🤖")
        return response.content
    except Exception as e:    
        logging.error(f"Failed to call LLM: {e}")
        raise ValueError(f"Failed to call LLM model: {e}")
    


async def call_llm_async(prompt: str, model_name: str = None, llm_config=None) -> str:
    if llm_config is None:
        llm_config = {}
    langfuse_handler = CallbackHandler()

    if os.environ.get('LLM_API_KEY') is None:
        raise ValueError("LLM_API_KEY is not set")
    if os.environ.get('LLM_BASE_URL') is None:
        raise ValueError("LLM_BASE_URL is not set")
    
    try:
        start_time = time.time()
        llm_model = get_llm_model(model_name, llm_config)
        response = await llm_model.ainvoke(
            [{"role": "user", "content": prompt}],
                                    config=RunnableConfig(callbacks=[langfuse_handler]))
        use_time = time.time() - start_time
        logging.info(f"LLM response[{len(prompt)} chars -> use {use_time:.2f} s] result is: {response.content} 🤖")
        return response.content
    except Exception as e:    
        logging.error(f"Failed to call LLM: {e}")
        raise ValueError(f"Failed to call LLM model: {e}")

def get_llm_model(model_name: str = None, llm_config=None) -> ChatOpenAI:
    if llm_config is None:
        llm_config = {}
    if os.environ.get('LLM_API_KEY') is None:
        raise ValueError("LLM_API_KEY is not set")
    if os.environ.get('LLM_BASE_URL') is None:
        raise ValueError("LLM_BASE_URL is not set")
    
    return ChatOpenAI(
        api_key=os.environ.get('LLM_API_KEY'),
        base_url=os.environ.get('LLM_BASE_URL'),
        model=model_name if model_name else os.environ.get('LLM_MODEL'),
        timeout=llm_config.get('timeout', 20),
        max_retries=llm_config.get('max_retries', 2),
        max_tokens=llm_config.get('max_tokens', 4096),
        temperature=llm_config.get('temperature', 0.5),
        frequency_penalty=llm_config.get('frequency_penalty', 0),
        presence_penalty=llm_config.get('presence_penalty', 0)
    )