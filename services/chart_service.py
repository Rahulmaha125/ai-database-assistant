"""Automated charting service using Plotly with Matplotlib fallback."""

import sys
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ChartService:
    """Detects chart suitability and produces interactive visualizations."""

    @staticmethod
    def can_plot(df: pd.DataFrame) -> bool:
        """Determine if a DataFrame has suitable dimensions and column types for a chart."""
        if df is None or df.empty or len(df) <= 1 or len(df.columns) < 2:
            return False

        numeric_cols = df.select_dtypes(include=["number"]).columns
        return len(numeric_cols) > 0

    @classmethod
    def create_chart(cls, df: pd.DataFrame, title: str = "Query Results Chart") -> Optional[go.Figure]:
        """Create an interactive Plotly chart if data is suitable.

        Returns:
            plotly.graph_objects.Figure or None if data cannot be meaningfully plotted.
        """
        if not cls.can_plot(df):
            return None

        numeric_cols = list(df.select_dtypes(include=["number"]).columns)
        non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

        try:
            # Case 1: 1 categorical/date column + at least 1 numeric column
            if len(non_numeric_cols) >= 1 and len(numeric_cols) >= 1:
                x_col = non_numeric_cols[0]
                y_col = numeric_cols[0]

                # Check if x looks like a date/time or month
                is_time_series = "date" in x_col.lower() or "month" in x_col.lower() or "year" in x_col.lower()

                if is_time_series:
                    fig = px.line(
                        df,
                        x=x_col,
                        y=y_col,
                        title=title,
                        markers=True,
                        template="plotly_white",
                    )
                else:
                    # Bar chart (horizontal if many categories, vertical if <= 10)
                    if len(df) > 10:
                        fig = px.bar(
                            df.sort_values(by=y_col, ascending=True),
                            x=y_col,
                            y=x_col,
                            orientation="h",
                            title=title,
                            template="plotly_white",
                            color=y_col,
                            color_continuous_scale="Blues",
                        )
                    else:
                        fig = px.bar(
                            df,
                            x=x_col,
                            y=y_col,
                            title=title,
                            template="plotly_white",
                            color=y_col,
                            color_continuous_scale="Blues",
                        )

                fig.update_layout(
                    margin=dict(l=20, r=20, t=50, b=20),
                    xaxis_title=x_col.replace("_", " ").title(),
                    yaxis_title=y_col.replace("_", " ").title(),
                )
                return fig

            # Case 2: All columns are numeric, plot first numeric as X, second as Y
            if len(numeric_cols) >= 2:
                x_col = numeric_cols[0]
                y_col = numeric_cols[1]
                fig = px.scatter(
                    df,
                    x=x_col,
                    y=y_col,
                    title=title,
                    template="plotly_white",
                )
                fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
                return fig

        except Exception:
            return None

        return None
