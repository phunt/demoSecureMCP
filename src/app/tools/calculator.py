"""Calculator tool for MCP server

Performs basic arithmetic calculations.
"""

from typing import List, Literal, Optional
from fastmcp import Context
from pydantic import BaseModel, Field
import math


class CalculatorRequest(BaseModel):
    """Request model for calculator tool"""
    operation: Literal["add", "subtract", "multiply", "divide", "power", "sqrt", "factorial"]
    operands: List[float] = Field(..., min_items=1, max_items=10)
    precision: Optional[int] = Field(None, ge=0, le=10)


class CalculatorResponse(BaseModel):
    """Response model for calculator tool"""
    result: float
    operation: str
    operands: List[float]
    precision: Optional[int] = None


async def calculator_tool(request: CalculatorRequest, ctx: Optional[Context] = None) -> CalculatorResponse:
    """
    Perform mathematical calculations.
    
    Args:
        request: CalculatorRequest with operation and operands
        ctx: FastMCP context (optional)
        
    Returns:
        CalculatorResponse with calculation result
    """
    result = 0.0
    
    # Perform calculation based on operation
    if request.operation == "add":
        result = sum(request.operands)
    elif request.operation == "subtract":
        if len(request.operands) < 2:
            raise ValueError("Subtract requires at least 2 operands")
        result = request.operands[0]
        for operand in request.operands[1:]:
            result -= operand
    elif request.operation == "multiply":
        result = 1.0
        for operand in request.operands:
            result *= operand
    elif request.operation == "divide":
        if len(request.operands) < 2:
            raise ValueError("Divide requires at least 2 operands")
        result = request.operands[0]
        for operand in request.operands[1:]:
            if operand == 0:
                raise ValueError("Division by zero")
            result /= operand
    elif request.operation == "power":
        if len(request.operands) != 2:
            raise ValueError("Power requires exactly 2 operands")
        result = pow(request.operands[0], request.operands[1])
    elif request.operation == "sqrt":
        if len(request.operands) != 1:
            raise ValueError("Square root requires exactly 1 operand")
        if request.operands[0] < 0:
            raise ValueError("Cannot calculate square root of negative number")
        result = math.sqrt(request.operands[0])
    elif request.operation == "factorial":
        if len(request.operands) != 1:
            raise ValueError("Factorial requires exactly 1 operand")
        operand = request.operands[0]
        if operand < 0 or operand != int(operand):
            raise ValueError("Factorial requires a non-negative integer")
        result = float(math.factorial(int(operand)))
    
    # Apply precision if requested
    if request.precision is not None:
        result = round(result, request.precision)
    
    return CalculatorResponse(
        result=result,
        operation=request.operation,
        operands=request.operands,
        precision=request.precision
    ) 