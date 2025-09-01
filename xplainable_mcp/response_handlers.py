"""
Response handling utilities for MCP server.

This module provides wrappers to handle common response patterns from
backends that may return None instead of empty collections.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, TypeVar, Union
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def handle_none_as_empty_list(func: Callable[..., Optional[List[T]]]) -> Callable[..., List[T]]:
    """
    Decorator to handle functions that might return None instead of empty list.
    
    This is common with local/development backends that may not fully implement
    all endpoints or return inconsistent response formats.
    
    Args:
        func: Function that returns Optional[List[T]]
        
    Returns:
        Function that always returns List[T], treating None as []
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> List[T]:
        try:
            result = func(*args, **kwargs)
            
            if result is None:
                logger.warning(f"{func.__name__} returned None, treating as empty list")
                return []
            
            return result
            
        except TypeError as e:
            if "'NoneType' object is not iterable" in str(e):
                logger.warning(f"{func.__name__} failed with NoneType iteration, treating as empty list")
                return []
            else:
                raise
        except Exception:
            # Re-raise other exceptions unchanged
            raise
    
    return wrapper


def handle_none_as_default(default_value: T) -> Callable[[Callable[..., Optional[T]]], Callable[..., T]]:
    """
    Decorator to handle functions that might return None, replacing with a default value.
    
    Args:
        default_value: Value to return if the function returns None
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., Optional[T]]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                result = func(*args, **kwargs)
                
                if result is None:
                    logger.warning(f"{func.__name__} returned None, using default value: {default_value}")
                    return default_value
                
                return result
                
            except Exception:
                # Re-raise exceptions unchanged
                raise
        
        return wrapper
    return decorator


def safe_model_dump_list(items: Optional[List[Any]], tool_name: str = "unknown") -> List[Dict[str, Any]]:
    """
    Safely convert a list of Pydantic models to dictionaries, handling None responses.
    
    Args:
        items: List of Pydantic models, or None
        tool_name: Name of the tool for logging purposes
        
    Returns:
        List of dictionaries from model_dump(), empty list if None
    """
    if items is None:
        logger.warning(f"{tool_name}: Backend returned None, treating as empty list")
        return []
    
    try:
        return [item.model_dump() for item in items]
    except AttributeError as e:
        logger.error(f"{tool_name}: Items don't have model_dump method: {e}")
        # Try to convert to dict anyway
        return [dict(item) if hasattr(item, '__dict__') else item for item in items]
    except TypeError as e:
        if "'NoneType' object is not iterable" in str(e):
            logger.warning(f"{tool_name}: Got NoneType iteration error, treating as empty list")
            return []
        else:
            logger.error(f"{tool_name}: TypeError converting models to dicts: {e}")
            raise
    except Exception as e:
        logger.error(f"{tool_name}: Error converting models to dicts: {e}")
        raise


def safe_client_call(client_func: Callable, tool_name: str, *args, **kwargs) -> Any:
    """
    Safely call a client method, handling common backend issues.
    
    Args:
        client_func: The client method to call
        tool_name: Name of the tool for logging
        *args: Positional arguments to pass to the client method
        **kwargs: Keyword arguments to pass to the client method
        
    Returns:
        The result from the client method, or appropriate fallback
    """
    try:
        return client_func(*args, **kwargs)
    except TypeError as e:
        if "'NoneType' object is not iterable" in str(e):
            logger.warning(f"{tool_name}: Client method failed with NoneType iteration, likely backend returned None")
            return None
        else:
            raise
    except Exception:
        # Re-raise other exceptions unchanged
        raise


def safe_model_dump(item: Optional[Any], tool_name: str = "unknown") -> Optional[Dict[str, Any]]:
    """
    Safely convert a single Pydantic model to dictionary, handling None responses.
    
    Args:
        item: Pydantic model, or None
        tool_name: Name of the tool for logging purposes
        
    Returns:
        Dictionary from model_dump(), or None if input is None
    """
    if item is None:
        logger.warning(f"{tool_name}: Backend returned None")
        return None
    
    try:
        return item.model_dump()
    except AttributeError as e:
        logger.error(f"{tool_name}: Item doesn't have model_dump method: {e}")
        # Try to convert to dict anyway
        return dict(item) if hasattr(item, '__dict__') else item
    except Exception as e:
        logger.error(f"{tool_name}: Error converting model to dict: {e}")
        raise


class BackendResponseError(Exception):
    """Exception raised when backend returns unexpected response format."""
    pass


def validate_backend_response(
    response: Any, 
    expected_type: type, 
    tool_name: str,
    allow_none: bool = False
) -> Any:
    """
    Validate that backend response matches expected type.
    
    Args:
        response: The response from backend
        expected_type: Expected type (e.g., list, dict)
        tool_name: Name of the tool for logging
        allow_none: Whether None is acceptable
        
    Returns:
        The response if valid
        
    Raises:
        BackendResponseError: If response type is unexpected
    """
    if response is None:
        if allow_none:
            return None
        else:
            logger.warning(f"{tool_name}: Backend returned None when {expected_type.__name__} expected")
            if expected_type == list:
                return []
            elif expected_type == dict:
                return {}
            else:
                raise BackendResponseError(
                    f"{tool_name}: Backend returned None, expected {expected_type.__name__}"
                )
    
    if not isinstance(response, expected_type):
        logger.warning(
            f"{tool_name}: Backend returned {type(response).__name__}, expected {expected_type.__name__}"
        )
        # Try to convert if possible
        if expected_type == list and hasattr(response, '__iter__') and not isinstance(response, str):
            return list(response)
        elif expected_type == dict and hasattr(response, '__dict__'):
            return dict(response)
        else:
            raise BackendResponseError(
                f"{tool_name}: Cannot convert {type(response).__name__} to {expected_type.__name__}"
            )
    
    return response


# Convenience functions for common patterns
def safe_list_response(response: Any, tool_name: str) -> List[Any]:
    """Safely handle a list response, converting None to empty list."""
    return validate_backend_response(response, list, tool_name, allow_none=False)


def safe_dict_response(response: Any, tool_name: str) -> Dict[str, Any]:
    """Safely handle a dict response, converting None to empty dict."""
    return validate_backend_response(response, dict, tool_name, allow_none=False)


# Example usage patterns for documentation
if __name__ == "__main__":
    # Example 1: Using decorator
    @handle_none_as_empty_list
    def example_list_function() -> Optional[List[str]]:
        return None  # This would normally cause issues
    
    result = example_list_function()  # Returns [] instead of None
    print(f"Decorator result: {result}")
    
    # Example 2: Using safe conversion
    none_response = None
    safe_result = safe_model_dump_list(none_response, "example_tool")
    print(f"Safe conversion result: {safe_result}")
    
    # Example 3: Using validation
    weird_response = "not a list"
    try:
        validated = validate_backend_response(weird_response, list, "example")
        print(f"Validated result: {validated}")
    except BackendResponseError as e:
        print(f"Validation error: {e}")