import pandas as pd
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def analyze_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Takes raw SQL results (list of dicts) and returns a structured analysis summary.
    """
    if not data:
        return {"error": "No data returned from query."}

    try:
        df = pd.DataFrame(data)
        analysis = {}

        # Basic Stats
        analysis["row_count"] = len(df)
        analysis["columns"] = list(df.columns)

        # Infer content type based on columns present
        columns = [c.lower() for c in df.columns]

        # Financial Analysis
        if any(c in columns for c in ["amount", "cost", "revenue", "budget", "price"]):
            numeric_cols = df.select_dtypes(include=['number']).columns
            for col in numeric_cols:
                analysis[f"total_{col}"] = float(df[col].sum())
                analysis[f"avg_{col}"] = float(df[col].mean())
                analysis[f"max_{col}"] = float(df[col].max())

            # Grouping suggestions
            if "category" in columns:
                cat_col = [c for c in df.columns if c.lower() == "category"][0]
                amount_col = [c for c in numeric_cols if "amount" in c.lower() or "cost" in c.lower() or "revenue" in c.lower()][0]
                grouped = df.groupby(cat_col)[amount_col].sum().to_dict()
                analysis["by_category"] = grouped

        # Project Status Analysis
        if "status" in columns:
            status_col = [c for c in df.columns if c.lower() == "status"][0]
            status_counts = df[status_col].value_counts().to_dict()
            analysis["status_distribution"] = status_counts
            
            # Calculate completion rate if applicable
            total = sum(status_counts.values())
            completed = status_counts.get("Completed", 0) + status_counts.get("Done", 0)
            if total > 0:
                analysis["completion_rate"] = round((completed / total) * 100, 2)

        # Time/Date Analysis
        date_cols = [c for c in df.columns if "date" in c.lower() or "deadline" in c.lower()]
        if date_cols:
            date_col = date_cols[0]
            try:
                df[date_col] = pd.to_datetime(df[date_col])
                analysis[f"earliest_{date_col}"] = str(df[date_col].min())
                analysis[f"latest_{date_col}"] = str(df[date_col].max())
            except:
                pass

        # Return the top 5 rows as a sample for the LLM to see actual values
        analysis["sample_rows"] = df.head(5).to_dict(orient="records")

        return analysis

    except Exception as e:
        logger.error(f"Error in Insight Layer: {e}")
        return {"error": f"Analysis failed: {str(e)}", "raw_sample": data[:5]}
