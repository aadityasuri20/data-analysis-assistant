import json

import matplotlib.pyplot as plt
import pandas as pd
from google.genai import types


PROMPTS = {
    "V1": "Choose an operation and column that answer the question.",
    "V2": """
You are planning an analysis of a used-car dataset. Use exact column names.
Use mean or median only for numeric columns. If the required column is absent,
return unsupported. If the question depends on an unclear metric, return
clarify and include a specific question for the user.
""",
    "V3": """
Plan the calculation for Pandas. Interpret the question using the schema,
then select one supported operation. Pandas will calculate the result.

Examples:
"Which fuel type appears most often?"
{"operation":"most_common","column":"fuel","message":""}

"Compare median prices by transmission."
{"operation":"median_by_group","column":"selling_price",
 "group_by":"transmission","message":""}

"Which car is best?"
{"operation":"clarify","message":"Do you mean lowest price or lowest kilometres driven?"}

"What's the average engine size?"
{"operation":"unsupported","message":"The dataset has no engine size column."}

Treat year as the car's model year. Use exact column names. Return clarify
for ambiguous criteria and unsupported for missing fields or operations.
""",
}

NUMERIC_OPERATIONS = {"mean", "median", "median_by_group"}
OPERATIONS = NUMERIC_OPERATIONS | {
    "row_count", "missing_values", "duplicate_count",
    "count_by", "most_common", "clarify", "unsupported",
}


def gemini_text(client, model, prompt, structured=False):
    config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json" if structured else None,
    )
    response = client.models.generate_content(
        model=model, contents=prompt, config=config
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    return response.text


def make_plan(df, question, client, model, version="V3"):
    schema = {column: str(dtype) for column, dtype in df.dtypes.items()}
    prompt = f"""
{PROMPTS[version]}

Columns and types: {json.dumps(schema)}
Question: {json.dumps(question)}
Available operations: {", ".join(sorted(OPERATIONS))}

Return one JSON object with operation, column, group_by, and message.
Leave unused fields blank or omit them. Use column for the field to count
or summarize. Use group_by only with median_by_group. Use message for
clarify and unsupported.
"""
    plan = json.loads(gemini_text(client, model, prompt, structured=True))
    if not isinstance(plan, dict):
        raise ValueError("Gemini returned an invalid analysis plan.")
    return plan


def calculate(df, plan):
    operation = plan.get("operation")
    column = plan.get("column")
    group_by = plan.get("group_by")

    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise ValueError("The analysis plan contains an unsupported operation.")

    if operation in {"clarify", "unsupported"}:
        return str(plan.get("message") or "Please rephrase your question.")

    if operation == "row_count":
        return int(len(df))
    if operation == "duplicate_count":
        return int(df.duplicated().sum())
    if operation == "missing_values":
        return df.isna().sum().rename("Missing values")

    if not isinstance(column, str) or column not in df.columns:
        raise ValueError(f"The requested column is unavailable: {column}")
    if operation in NUMERIC_OPERATIONS and not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"{column} must be numeric for this operation.")

    if operation == "mean":
        return float(df[column].mean())
    if operation == "median":
        return float(df[column].median())
    if operation == "median_by_group":
        if not isinstance(group_by, str) or group_by not in df.columns:
            raise ValueError(f"The grouping column is unavailable: {group_by}")
        return df.groupby(group_by)[column].median().dropna().sort_index()

    counts = df[column].value_counts()
    if operation == "most_common":
        if counts.empty:
            return counts
        return counts[counts.eq(counts.max())]
    return counts


def explain_result(question, plan, result, client, model):
    operation = plan["operation"]
    if operation in {"clarify", "unsupported"}:
        return result
    if isinstance(result, pd.Series):
        if result.empty:
            return "There are no values available for that analysis."
        evidence = result.head(20).to_string()
        if len(result) > 20:
            evidence += f"\nShowing 20 of {len(result)} groups."
    else:
        if pd.isna(result):
            return "There are no numeric values available for that calculation."
        evidence = f"{result:,.2f}" if isinstance(result, float) else str(result)

    prompt = f"""
Answer the user's question in one or two sentences using only the Pandas result.
Keep the numbers faithful to the result and do not assume a currency.
If several categories tie for first, mention the tie.

Question: {json.dumps(question)}
Analysis plan: {json.dumps(plan)}
Pandas result:
{evidence}
"""
    return gemini_text(client, model, prompt)


def make_chart(plan, result):
    operation = plan.get("operation")
    if operation not in {"count_by", "median_by_group"} or result.empty:
        return None

    if operation == "median_by_group" and plan.get("group_by") == "year":
        ax = result.plot(kind="line", marker="o", figsize=(9, 4))
        ax.set(xlabel="Model year", ylabel=f"Median {plan['column']}")
    else:
        chart_data = result.sort_values(ascending=False).head(15)
        ax = chart_data.plot(kind="bar", color="steelblue", figsize=(9, 4))
        label = "Record count" if operation == "count_by" else f"Median {plan['column']}"
        ax.set(ylabel=label)
        if len(result) > 15:
            ax.set_title("Top 15 groups")
        ax.tick_params(axis="x", labelrotation=35)

    figure = ax.get_figure()
    figure.tight_layout()
    return figure
