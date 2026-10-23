"""
Visualizer Agent - Transform SQL Data to Recharts Format
Analyzes SQL query results and generates chart configurations using LLM.
"""

import os
import logging
from typing import List, Dict, Any, Literal
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Chart configuration schema
class ChartConfig(BaseModel):
    """Configuration for Recharts visualization."""
    type: Literal["bar", "line", "pie", "area"] = Field(
        ...,
        description="Type of chart to display"
    )
    title: str = Field(
        ...,
        description="Descriptive title for the chart"
    )
    xAxisKey: str = Field(
        ...,
        description="Key from data to use for X-axis (or category for pie charts)"
    )
    dataKey: str = Field(
        ...,
        description="Key from data to use for Y-axis values (or values for pie charts)"
    )
    data: List[Dict[str, Any]] = Field(
        ...,
        description="The actual data array to visualize"
    )


class VisualizerAgent:
    """
    Visualizer agent that transforms SQL results into chart configurations.
    Uses LLM to analyze data structure and determine optimal visualization.
    """
    
    def __init__(self):
        """Initialize the visualizer with LLM."""
        try:
            # Get API key
            self.api_key = os.getenv("OPENAI_API_KEY")
            
            if not self.api_key or not (self.api_key.startswith("sk-") or self.api_key.startswith("sk-proj-")):
                raise ValueError("Missing or invalid OpenAI API Key")
            
            # Initialize LLM (GPT-4o for intelligent chart selection)
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                openai_api_key=self.api_key
            )
            
            logger.info("Visualizer Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Visualizer Agent: {str(e)}")
            raise
    
    def generate_chart_config(self, data: List[dict], query: str = "") -> Dict[str, Any]:
        """
        Generate a Recharts-compatible chart configuration from SQL data.
        
        Args:
            data: List of dictionaries from SQL query results
            query: Original SQL query (optional, helps with context)
            
        Returns:
            Dictionary with chart configuration
        """
        try:
            logger.info(f"Generating chart config for {len(data)} data points")
            
            # Validate input
            if not data or not isinstance(data, list):
                return self._create_error_config("No data provided for visualization")
            
            if len(data) == 0:
                return self._create_error_config("Empty dataset - no data to visualize")
            
            # Analyze data structure
            sample_row = data[0]
            keys = list(sample_row.keys())
            
            logger.info(f"Data keys: {keys}")
            
            # Create analysis prompt for LLM
            analysis_prompt = f"""Analyze this SQL query result and determine the best chart configuration.

Query: {query if query else "Not provided"}

Data structure (first row):
{sample_row}

Available keys: {keys}
Number of rows: {len(data)}

Determine:
1. Best chart type (bar, line, pie, or area)
2. Appropriate title for the chart
3. Which key should be the X-axis (or category for pie)
4. Which key should be the data/value key (Y-axis)

Guidelines:
- Use 'bar' for categorical comparisons (e.g., sales by region, count by category)
- Use 'line' for time series or trends (e.g., revenue over time)
- Use 'pie' for part-to-whole relationships (e.g., market share, distribution)
- Use 'area' for cumulative trends over time
- For X-axis: choose categorical or time-based keys (strings, dates)
- For data key: choose numeric values (counts, amounts, totals)

Respond with a chart configuration."""

            # Use LLM with structured output
            router = self.llm.with_structured_output(ChartConfig)
            
            # Get chart configuration from LLM
            config = router.invoke(analysis_prompt)
            
            # Return as dictionary with actual data
            result = {
                "type": config.type,
                "title": config.title,
                "xAxisKey": config.xAxisKey,
                "dataKey": config.dataKey,
                "data": data  # Use actual SQL data
            }
            
            logger.info(f"Generated chart config: {config.type} - {config.title}")
            
            return result
            
        except Exception as e:
            logger.error(f"Chart config generation failed: {str(e)}", exc_info=True)
            return self._create_error_config(f"Error generating chart: {str(e)}")
    
    def _create_error_config(self, error_message: str) -> Dict[str, Any]:
        """Create a fallback error configuration."""
        return {
            "type": "bar",
            "title": "Visualization Error",
            "xAxisKey": "error",
            "dataKey": "value",
            "data": [{"error": error_message, "value": 0}]
        }
    
    def visualize_sql_result(self, sql_result: str, query: str = "") -> Dict[str, Any]:
        """
        Attempt to parse SQL result and create visualization.
        
        Args:
            sql_result: String result from SQL agent
            query: Original query
            
        Returns:
            Chart configuration or None if not visualizable
        """
        try:
            # Try to detect if result contains structured data
            # This is a heuristic - in practice, SQL agent should return structured data
            
            # For now, return None if it's just text
            # In production, SQL agent should return {"answer": str, "data": List[dict]}
            logger.info("SQL result is text-only, not visualizable")
            return None
            
        except Exception as e:
            logger.error(f"Visualization attempt failed: {str(e)}")
            return None


# Backward compatibility function
def visualizer_node(state):
    """
    LangGraph node wrapper for visualizer.
    Maintains backward compatibility.
    """
    query = state.get("query")
    data = state.get("data", {})
    
    # Check if we have visualizable data
    if not data or not isinstance(data, dict):
        return {"visual_artifact": ""}
    
    # Extract data array if present
    data_array = data.get("results", [])
    
    if not data_array:
        return {"visual_artifact": ""}
    
    try:
        visualizer = VisualizerAgent()
        chart_config = visualizer.generate_chart_config(data_array, query)
        
        # Return as JSON string for visual_artifact
        import json
        return {"visual_artifact": json.dumps(chart_config)}
        
    except Exception as e:
        logger.error(f"Visualizer node failed: {str(e)}")
        return {"visual_artifact": ""}
