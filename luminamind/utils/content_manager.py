import tiktoken
import logging

logger = logging.getLogger(__name__)

def count_tokens(text: str, model_name: str = "gpt-4") -> int:
    """
    Count the number of tokens in a string using tiktoken.
    
    Args:
        text: The text to count tokens for.
        model_name: The model name to use for encoding. Defaults to "gpt-4".
        
    Returns:
        The number of tokens.
    """
    if not text:
        return 0
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
        
    return len(encoding.encode(text))
