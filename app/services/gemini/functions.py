"""
Function Calling Handler for Gemini
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_FunctionRegistration = Dict[str, Any]


class FunctionCallHandler:
    """
    Handler for executing function calls from Gemini API responses.
    """

    def __init__(self):
        """Initialize function call handler"""
        self.functions: Dict[str, _FunctionRegistration] = {}

    def register_function(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a function that can be called by Gemini.

        Args:
            name: Function name
            func: Function to execute
            description: Function description
            parameters: Function parameters schema
        """
        self.functions[name] = {
            "function": func,
            "description": description,
            "parameters": parameters,
        }
        logger.info(f"Registered function: {name}")

    def get_function_declarations(self) -> List[Dict[str, Any]]:
        """
        Get function declarations for Gemini API.

        Returns:
            List of function declarations
        """
        declarations = []
        for name, func_info in self.functions.items():
            declaration = {
                "name": name,
                "description": func_info.get("description", ""),
                "parameters": func_info.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
            declarations.append(declaration)
        return declarations

    async def execute_function_call(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """
        Execute a function call.

        Args:
            function_name: Name of the function to call
            arguments: Function arguments

        Returns:
            Function result
        """
        if function_name not in self.functions:
            raise ValueError(f"Function not found: {function_name}")

        func_info = self.functions[function_name]
        func = func_info["function"]

        try:
            # Execute function (support both sync and async)
            if hasattr(func, "__call__"):
                import asyncio

                if asyncio.iscoroutinefunction(func):
                    result = await func(**arguments)
                else:
                    result = func(**arguments)
                return result
            else:
                raise ValueError(f"Invalid function: {function_name}")

        except Exception as e:
            logger.error(f"Function execution error for {function_name}: {e}")
            raise Exception(f"Function execution error: {str(e)}")

    def process_function_calls(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process function calls from Gemini response.

        Args:
            candidates: Response candidates from Gemini

        Returns:
            List of function call results
        """
        function_calls = []

        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            for part in parts:
                if "functionCall" in part:
                    function_call = part["functionCall"]
                    function_name = function_call.get("name", "")
                    arguments = function_call.get("args", {})

                    function_calls.append(
                        {"name": function_name, "arguments": arguments}
                    )

        return function_calls

    async def handle_function_calls(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Handle function calls and return results.

        Args:
            candidates: Response candidates from Gemini

        Returns:
            List of function call results
        """
        function_calls = self.process_function_calls(candidates)
        results = []

        for func_call in function_calls:
            function_name = func_call["name"]
            arguments = func_call["arguments"]

            try:
                result = await self.execute_function_call(function_name, arguments)
                results.append(
                    {
                        "functionCall": {"name": function_name, "args": arguments},
                        "functionResponse": {"name": function_name, "response": result},
                    }
                )
            except Exception as e:
                logger.error(f"Error handling function call {function_name}: {e}")
                results.append(
                    {
                        "functionCall": {"name": function_name, "args": arguments},
                        "functionResponse": {
                            "name": function_name,
                            "response": {"error": str(e)},
                        },
                    }
                )

        return results
