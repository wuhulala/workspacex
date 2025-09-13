import tiktoken



def num_tokens(input_message: str) -> int:
    return len(tiktoken.get_encoding("cl100k_base").encode(input_message))

def num_tokens_from_messages(messages) -> int:
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.get_encoding("gpt2")
    if isinstance(messages, str):
        return len(encoding.encode(messages))

    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens -= 1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens