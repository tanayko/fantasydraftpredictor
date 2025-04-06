import math

from autogen import UserProxyAgent

from agent_interface import BaseAgent
from user_proxy import prompt_agent

# Define simple calculation tools
def calculate_basic(operation: str, a: float, b: float) -> float:
    """
    Perform a basic mathematical operation on two numbers.
    
    Args:
        operation: The operation to perform ("add", "subtract", "multiply", "divide")
        a: First number
        b: Second number
        
    Returns:
        The result of the calculation
    
    Example:
        result = calculate_basic("add", 5, 3)  # Returns 8
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")

def calculate_scientific(operation: str, value: float, **kwargs) -> float:
    """
    Perform scientific calculations on a number.
    
    Args:
        operation: The operation to perform ("sqrt", "power", "log", "sin", "cos", "tan")
        value: The input value
        **kwargs: Additional parameters depending on the operation:
            - For "power": exponent (float)
            - For "log": base (float, default is natural log if not specified)
    
    Returns:
        The result of the calculation
    
    Example:
        sqrt_result = calculate_scientific("sqrt", 16)  # Returns 4.0
        power_result = calculate_scientific("power", 2, exponent=3)  # Returns 8.0
    """
    if operation == "sqrt":
        if value < 0:
            raise ValueError("Cannot calculate square root of a negative number")
        return math.sqrt(value)
    elif operation == "power":
        exponent = kwargs.get("exponent", 2)
        return math.pow(value, exponent)
    elif operation == "log":
        base = kwargs.get("base", None)
        if value <= 0:
            raise ValueError("Cannot calculate logarithm of zero or negative number")
        if base is None:
            return math.log(value)  # Natural log
        else:
            return math.log(value, base)
    elif operation == "sin":
        return math.sin(value)
    elif operation == "cos":
        return math.cos(value)
    elif operation == "tan":
        return math.tan(value)
    else:
        raise ValueError(f"Unknown operation: {operation}")

# Create the calculator agent
system_prompt = """You are a helpful Calculator Assistant. You can use tools to perform various calculations.
When a user requests a calculation, you should:
1. Understand what type of calculation they need
2. Choose the appropriate tool for the job
3. Provide a clear explanation of the result
Be precise in your calculations and explain your process when needed."""

# Create the agent
calculator_agent = BaseAgent(
    name="Calculator",
    system_prompt=system_prompt,
    tools=[calculate_basic, calculate_scientific],
).create_agent()

prompt_agent(calculator_agent, "Calculate the square root of 16")