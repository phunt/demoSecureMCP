"""Calculator MCP tool for demonstrating operations requiring write scope"""

from typing import List, Literal, Union, Optional
from decimal import Decimal, InvalidOperation
import math

from fastmcp import Context
from pydantic import BaseModel, Field, field_validator

from src.core.logging import get_logger


logger = get_logger(__name__)


class CalculatorRequest(BaseModel):
    """Request model for calculator tool"""
    operation: Literal["add", "subtract", "multiply", "divide", "power", "sqrt", "factorial"] = Field(
        ...,
        description="Mathematical operation to perform"
    )
    operands: List[Union[int, float]] = Field(
        ...,
        description="Numbers to operate on (most operations require 2, sqrt/factorial require 1)"
    )
    precision: Optional[int] = Field(
        None,
        description="Decimal precision for the result"
    )
    
    @field_validator('operands')
    @classmethod
    def validate_operands(cls, v: List[Union[int, float]], info) -> List[Union[int, float]]:
        """Validate operand count based on operation"""
        operation = info.data.get('operation')
        
        if operation in ['sqrt', 'factorial']:
            if len(v) != 1:
                raise ValueError(f"{operation} requires exactly 1 operand")
        elif operation in ['add', 'subtract', 'multiply', 'divide', 'power']:
            if len(v) < 2:
                raise ValueError(f"{operation} requires at least 2 operands")
        
        return v


class CalculatorResponse(BaseModel):
    """Response model for calculator tool"""
    operation: str = Field(..., description="Operation performed")
    operands: List[Union[int, float]] = Field(..., description="Input operands")
    result: Union[int, float] = Field(..., description="Calculation result")
    formula: str = Field(..., description="Mathematical formula used")
    precision_applied: Optional[int] = Field(None, description="Decimal precision applied")


async def calculator_tool(request: CalculatorRequest, ctx: Context) -> CalculatorResponse:
    """
    Perform mathematical calculations with various operations.
    
    This tool demonstrates operations that modify state (requiring write scope).
    Supports basic arithmetic, power operations, square root, and factorial.
    
    Args:
        request: Calculator request with operation and operands
        ctx: FastMCP context for logging and progress
        
    Returns:
        CalculatorResponse with result and calculation details
    """
    await ctx.info(f"Performing {request.operation} operation on {len(request.operands)} operands")
    
    # Convert to Decimal for precision
    decimals = [Decimal(str(x)) for x in request.operands]
    
    try:
        # Perform operation
        if request.operation == "add":
            result = sum(decimals)
            formula = " + ".join(str(x) for x in request.operands)
            
        elif request.operation == "subtract":
            result = decimals[0]
            for d in decimals[1:]:
                result -= d
            formula = " - ".join(str(x) for x in request.operands)
            
        elif request.operation == "multiply":
            result = decimals[0]
            for d in decimals[1:]:
                result *= d
            formula = " × ".join(str(x) for x in request.operands)
            
        elif request.operation == "divide":
            result = decimals[0]
            for d in decimals[1:]:
                if d == 0:
                    await ctx.error("Division by zero attempted")
                    raise ValueError("Division by zero")
                result /= d
            formula = " ÷ ".join(str(x) for x in request.operands)
            
        elif request.operation == "power":
            result = float(request.operands[0]) ** float(request.operands[1])
            formula = f"{request.operands[0]} ^ {request.operands[1]}"
            
        elif request.operation == "sqrt":
            if request.operands[0] < 0:
                await ctx.error("Square root of negative number attempted")
                raise ValueError("Cannot calculate square root of negative number")
            result = math.sqrt(float(request.operands[0]))
            formula = f"√{request.operands[0]}"
            
        elif request.operation == "factorial":
            n = int(request.operands[0])
            if n < 0:
                await ctx.error("Factorial of negative number attempted")
                raise ValueError("Cannot calculate factorial of negative number")
            if n > 170:
                await ctx.warning("Large factorial may cause overflow")
            result = math.factorial(n)
            formula = f"{n}!"
        
        # Apply precision if requested
        if request.precision is not None and isinstance(result, (float, Decimal)):
            result = round(float(result), request.precision)
            await ctx.debug(f"Applied precision: {request.precision} decimal places")
        else:
            result = float(result) if isinstance(result, Decimal) else result
        
        await ctx.info(f"Calculation successful: {formula} = {result}")
        
        return CalculatorResponse(
            operation=request.operation,
            operands=request.operands,
            result=result,
            formula=formula,
            precision_applied=request.precision
        )
        
    except (ValueError, InvalidOperation, OverflowError) as e:
        await ctx.error(f"Calculation failed: {str(e)}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error in calculation: {str(e)}")
        raise 