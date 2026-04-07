import functools
import logging

logger = logging.getLogger(__name__)

# ── Log helpers ────────────────────────────────────────────────────────────────


def format_agent_response(response):
    """
    Formats the agent response into content, tool calls
    and invalid tool calls to monitor agent workflow
    """
    response_dict = response.dict()
    return {
        "content": response_dict.get("content", ""),
        "tool_calls": response_dict.get("tool_calls", []),
        "invalid_tool_calls": response_dict.get("invalid_tool_calls", [])
    }


def tool_tracing(func):
    """
    Captures and logs the input and outputs of tool call
    To use this, import function and add @tool_tracing to
    the tool directly
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        config = kwargs.get("config")
        user_id = "unknown_user"
        if isinstance(config, dict) or hasattr(config, "get"):
            user_id = config.get("metadata", {}).get("user_id", "unknown_user")
        
        logger.info(f"USER_ID: {user_id} | TOOL_START | {func.__name__} | Args: {args} Kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"USER_ID: {user_id} | TOOL_SUCCESS | {func.__name__} | Result: {result}")
            return result
        except Exception as e:
            logger.error(f"USER_ID: {user_id} | TOOL_ERROR | {func.__name__} | Error: {str(e)}")
            raise e
    return wrapper
