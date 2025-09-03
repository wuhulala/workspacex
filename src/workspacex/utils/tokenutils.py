import tiktoken



def num_tokens(input_message: str) -> int:
    return len(tiktoken.get_encoding("cl100k_base").encode(input_message))