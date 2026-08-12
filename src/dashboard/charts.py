from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _view_specific_yaxis_range(plot_df: pd.DataFrame, view: str) -> list[float]:
    view_df = plot_df[plot_df["view"] == view].copy()
    if view_df.empty or "exposure_weight" not in view_df.columns:
        return [-0.05, 0.05]

    values = pd.to_numeric(view_df["exposure_weight"], errors="coerce").dropna()
    if values.empty:
        return [-0.05, 0.05]

    min_value = float(values.min())
    max_value = float(values.max())
    positive_span = max(max_value, 0.01)
    negative_span = max(abs(min_value), 0.01)
    positive_padding = max(positive_span * 0.25, 0.03)
    negative_padding = max(negative_span * 0.25, 0.02)

    if view == "Short":
        upper = max(0.0, max_value) + positive_padding * 0.5
        lower = min_value - negative_padding
        return [lower, upper]

    if view == "Long":
        lower = min(0.0, min_value) - negative_padding * 0.35
        upper = max_value + positive_padding
        return [lower, upper]

    lower = min(0.0, min_value) - negative_padding * 0.35
    return [lower, max_value + positive_padding]


def _visibility_map_with_legend(trace_order: list[tuple[str, str]], active_view: str) -> list[bool | str]:
    visibility: list[bool | str] = []
    for view, _ in trace_order:
        if active_view == "All":
            visibility.append(True)
        elif view == active_view:
            visibility.append(True)
        else:
            visibility.append("legendonly")
    return visibility


def _require_columns(df: pd.DataFrame, columns: list[str], message: str):
    if df.empty:
        return message
    missing = [column for column in columns if column not in df.columns]
    if missing:
        return f"{message} Missing columns: {', '.join(missing)}."
    return None


def asset_allocation_chart(df: pd.DataFrame):
    error = _require_columns(df, ["asset_class", "final_value_usd_m"], "Unable to build asset allocation chart.")
    if error:
        return error
    return px.pie(df, values="final_value_usd_m", names="asset_class", title="Asset Allocation")


def asset_class_value_trend_chart(df: pd.DataFrame):
    error = _require_columns(df, ["date", "asset_class", "value_usd_m"], "Unable to build asset class value trend chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["value_usd_m"] = pd.to_numeric(chart_df["value_usd_m"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "value_usd_m"]).sort_values("date")
    if chart_df.empty:
        return "Asset class trend data is unavailable."
    return px.line(chart_df, x="date", y="value_usd_m", color="asset_class", title="Asset Class Value Trend")


def asset_class_exposure_filter_chart(exposure_history_df: pd.DataFrame):
    required_columns = [
        "date",
        "asset_class",
        "position_side",
        "net_weight",
    ]
    error = _require_columns(
        exposure_history_df,
        required_columns,
        "Unable to build asset class exposure chart.",
    )
    if error:
        return error

    chart_df = exposure_history_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["net_weight"] = pd.to_numeric(chart_df["net_weight"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "asset_class", "position_side", "net_weight"])
    if chart_df.empty:
        return "Asset class exposure history is unavailable."

    chart_df["position_side"] = chart_df["position_side"].astype(str).str.lower()
    long_df = (
        chart_df.loc[chart_df["position_side"] == "long"]
        .groupby(["date", "asset_class"], as_index=False)["net_weight"]
        .sum()
        .rename(columns={"net_weight": "exposure_weight"})
    )
    long_df["view"] = "Long"

    short_df = (
        chart_df.loc[chart_df["position_side"] == "short"]
        .groupby(["date", "asset_class"], as_index=False)["net_weight"]
        .sum()
        .rename(columns={"net_weight": "exposure_weight"})
    )
    short_df["view"] = "Short"

    all_df = (
        pd.concat([long_df, short_df], ignore_index=True)
        .groupby(["date", "asset_class"], as_index=False)["exposure_weight"]
        .sum()
    )
    all_df["view"] = "All"

    plot_df = pd.concat([all_df, long_df, short_df], ignore_index=True)
    if plot_df.empty:
        return "Asset class exposure history is unavailable."

    trace_order: list[tuple[str, str]] = []
    for view in ["All", "Long", "Short"]:
        asset_classes = (
            plot_df.loc[plot_df["view"] == view, "asset_class"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        for asset_class in sorted(asset_classes):
            trace_order.append((view, asset_class))

    figure = go.Figure()
    for view, asset_class in trace_order:
        series_df = plot_df[(plot_df["view"] == view) & (plot_df["asset_class"] == asset_class)].sort_values("date")
        line_style = "solid" if view != "Short" else "dash"
        figure.add_trace(
            go.Scatter(
                x=series_df["date"],
                y=series_df["exposure_weight"],
                mode="lines",
                name=asset_class,
                legendgroup=asset_class,
                line=dict(width=2.5, dash=line_style),
                visible=True if view == "All" else "legendonly",
                showlegend=view == "All",
                hovertemplate="%{x|%Y-%m}<br>%{fullData.name}: %{y:.1%}<extra></extra>",
            )
        )

    visibility_map: dict[str, list[bool | str]] = {}
    for active_view in ["All", "Long", "Short"]:
        visibility_map[active_view] = _visibility_map_with_legend(trace_order, active_view)

    yaxis_ranges = {
        view: _view_specific_yaxis_range(plot_df, view)
        for view in ["All", "Long", "Short"]
    }

    figure.update_layout(
        title="Asset Class Net Exposure Trend (% NAV)",
        xaxis_title="Date",
        yaxis_title="Exposure % NAV",
        yaxis_tickformat=".0%",
        yaxis=dict(range=yaxis_ranges["All"]),
        legend_title="Asset Class",
        hovermode="x unified",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
                "yanchor": "top",
                "buttons": [
                    {
                        "label": label,
                        "method": "update",
                        "args": [
                            {"visible": visibility_map[label]},
                            {
                                "title": f"Asset Class Net Exposure Trend (% NAV) - {label}",
                                "yaxis.range": yaxis_ranges[label],
                            },
                        ],
                    }
                    for label in ["All", "Long", "Short"]
                ],
            }
        ],
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.5)
    return figure


def dimension_exposure_filter_chart(
    exposure_history_df: pd.DataFrame,
    dimension_column: str,
    title: str,
):
    required_columns = ["date", dimension_column, "position_side", "net_weight"]
    error = _require_columns(
        exposure_history_df,
        required_columns,
        f"Unable to build {title.lower()}.",
    )
    if error:
        return error

    chart_df = exposure_history_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["net_weight"] = pd.to_numeric(chart_df["net_weight"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", dimension_column, "position_side", "net_weight"])
    if chart_df.empty:
        return f"{title} is unavailable."

    chart_df["position_side"] = chart_df["position_side"].astype(str).str.lower()

    long_df = (
        chart_df.loc[chart_df["position_side"] == "long"]
        .groupby(["date", dimension_column], as_index=False)["net_weight"]
        .sum()
        .rename(columns={"net_weight": "exposure_weight"})
    )
    long_df["view"] = "Long"

    short_df = (
        chart_df.loc[chart_df["position_side"] == "short"]
        .groupby(["date", dimension_column], as_index=False)["net_weight"]
        .sum()
        .rename(columns={"net_weight": "exposure_weight"})
    )
    short_df["view"] = "Short"

    all_df = (
        pd.concat([long_df, short_df], ignore_index=True)
        .groupby(["date", dimension_column], as_index=False)["exposure_weight"]
        .sum()
    )
    all_df["view"] = "All"
    plot_df = pd.concat([all_df, long_df, short_df], ignore_index=True)
    if plot_df.empty:
        return f"{title} is unavailable."

    latest_slice = (
        plot_df.sort_values("date")
        .groupby(["view", dimension_column])
        .tail(1)
        .sort_values("exposure_weight", ascending=False)
    )

    top_categories: list[str] = []
    for view in ["All", "Long", "Short"]:
        top_categories.extend(
            latest_slice.loc[latest_slice["view"] == view, dimension_column]
            .astype(str)
            .head(8)
            .tolist()
        )
    top_categories = sorted(set(top_categories))
    plot_df = plot_df[plot_df[dimension_column].astype(str).isin(top_categories)]

    trace_order: list[tuple[str, str]] = []
    for view in ["All", "Long", "Short"]:
        categories = (
            plot_df.loc[plot_df["view"] == view, dimension_column]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        for category in sorted(categories):
            trace_order.append((view, category))

    figure = go.Figure()
    for view, category in trace_order:
        series_df = plot_df[
            (plot_df["view"] == view) & (plot_df[dimension_column].astype(str) == category)
        ].sort_values("date")
        line_style = "solid" if view != "Short" else "dash"
        figure.add_trace(
            go.Scatter(
                x=series_df["date"],
                y=series_df["exposure_weight"],
                mode="lines",
                name=category,
                legendgroup=category,
                line=dict(width=2.5, dash=line_style),
                visible=True if view == "All" else "legendonly",
                showlegend=view == "All",
                hovertemplate="%{x|%Y-%m}<br>%{fullData.name}: %{y:.1%}<extra></extra>",
            )
        )

    visibility_map = {
        active_view: _visibility_map_with_legend(trace_order, active_view)
        for active_view in ["All", "Long", "Short"]
    }
    yaxis_ranges = {
        view: _view_specific_yaxis_range(plot_df, view)
        for view in ["All", "Long", "Short"]
    }
    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Exposure % NAV",
        yaxis_tickformat=".0%",
        yaxis=dict(range=yaxis_ranges["All"]),
        legend_title=dimension_column.replace("_", " ").title(),
        hovermode="x unified",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
                "yanchor": "top",
                "buttons": [
                    {
                        "label": label,
                        "method": "update",
                        "args": [
                            {"visible": visibility_map[label]},
                            {
                                "title": f"{title} - {label}",
                                "yaxis.range": yaxis_ranges[label],
                            },
                        ],
                    }
                    for label in ["All", "Long", "Short"]
                ],
            }
        ],
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.5)
    return figure


def dimension_net_exposure_trend_chart(
    exposure_history_df: pd.DataFrame,
    dimension_column: str,
    title: str,
):
    required_columns = ["date", dimension_column, "position_side", "net_weight"]
    error = _require_columns(
        exposure_history_df,
        required_columns,
        f"Unable to build {title.lower()}.",
    )
    if error:
        return error

    chart_df = exposure_history_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["net_weight"] = pd.to_numeric(chart_df["net_weight"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", dimension_column, "position_side", "net_weight"])
    if chart_df.empty:
        return f"{title} is unavailable."
    net_df = (
        chart_df.groupby(["date", dimension_column], as_index=False)["net_weight"]
        .sum()
        .rename(columns={"net_weight": "exposure_weight"})
    )
    if net_df.empty:
        return f"{title} is unavailable."

    latest_slice = (
        net_df.sort_values("date")
        .groupby(dimension_column)
        .tail(1)
        .assign(abs_exposure=lambda df: df["exposure_weight"].abs())
        .sort_values("abs_exposure", ascending=False)
    )
    top_categories = latest_slice[dimension_column].astype(str).head(8).tolist()
    net_df = net_df[net_df[dimension_column].astype(str).isin(top_categories)]
    if net_df.empty:
        return f"{title} is unavailable."

    figure = px.line(
        net_df.sort_values("date"),
        x="date",
        y="exposure_weight",
        color=dimension_column,
        title=title,
    )
    figure.update_layout(
        xaxis_title="Date",
        yaxis_title="Exposure % NAV",
        yaxis_tickformat=".0%",
        hovermode="x unified",
        legend_title=dimension_column.replace("_", " ").title(),
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.5)
    return figure


def asset_class_long_short_trend_chart(exposure_df: pd.DataFrame):
    required = ["date", "category_label", "long_exposure", "short_exposure"]
    error = _require_columns(exposure_df, required, "Unable to build asset class long/short trend chart.")
    if error:
        return error

    chart_df = exposure_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    for column in ["long_exposure", "short_exposure"]:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "category_label", "long_exposure", "short_exposure"]).sort_values("date")
    if chart_df.empty:
        return "Asset class exposure trend is unavailable."

    categories = chart_df["category_label"].dropna().astype(str).unique().tolist()
    figure = go.Figure()
    trace_order: list[tuple[str, str]] = []
    for category in categories:
        category_df = chart_df[chart_df["category_label"] == category].sort_values("date")
        figure.add_trace(
            go.Scatter(
                x=category_df["date"],
                y=category_df["long_exposure"],
                mode="lines",
                name=f"{category} (Long)",
                legendgroup=category,
                line=dict(width=2.5),
                visible=True,
                hovertemplate="%{x|%Y-%m}<br>%{fullData.name}: %{y:.1%}<extra></extra>",
            )
        )
        trace_order.append(("Long", category))
        figure.add_trace(
            go.Scatter(
                x=category_df["date"],
                y=category_df["short_exposure"],
                mode="lines",
                name=f"{category} (Short)",
                legendgroup=category,
                line=dict(width=2.0, dash="dash"),
                visible=True,
                hovertemplate="%{x|%Y-%m}<br>%{fullData.name}: %{y:.1%}<extra></extra>",
            )
        )
        trace_order.append(("Short", category))

    visibility_map = {
        "All": [True] * len(trace_order),
        "Long": [trace_type == "Long" for trace_type, _ in trace_order],
        "Short": [trace_type == "Short" for trace_type, _ in trace_order],
    }

    all_values = pd.concat(
        [
            pd.to_numeric(chart_df["long_exposure"], errors="coerce"),
            pd.to_numeric(chart_df["short_exposure"], errors="coerce"),
        ],
        ignore_index=True,
    ).dropna()
    max_abs = float(all_values.abs().max()) if not all_values.empty else 0.05
    y_limit = max(max_abs * 1.15, 0.05)

    figure.update_layout(
        title="Asset Class Exposure",
        xaxis_title="Date",
        yaxis_title="Exposure % NAV",
        yaxis_tickformat=".0%",
        yaxis=dict(range=[-y_limit, y_limit]),
        hovermode="x unified",
        legend_title="Asset Class",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 1.0,
                "xanchor": "right",
                "y": 1.18,
                "yanchor": "top",
                "buttons": [
                    {
                        "label": label,
                        "method": "update",
                        "args": [
                            {"visible": visibility_map[label]},
                            {"title": f"Asset Class Exposure - {label}"},
                        ],
                    }
                    for label in ["All", "Long", "Short"]
                ],
            }
        ],
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.5)
    return figure


def asset_class_snapshot_bars(snapshot_df: pd.DataFrame, value_column: str, title: str):
    required = ["category_label", "long_exposure", "short_exposure"]
    if value_column == "net_exposure":
        required = ["category_label", "net_exposure"]
    error = _require_columns(snapshot_df, required, f"Unable to build {title.lower()}.")
    if error:
        return error

    chart_df = snapshot_df.copy()
    if value_column == "net_exposure":
        chart_df["net_exposure"] = pd.to_numeric(chart_df["net_exposure"], errors="coerce")
        chart_df = (
            chart_df.dropna(subset=["category_label", "net_exposure"])
            .assign(abs_exposure=lambda df: df["net_exposure"].abs())
            .sort_values("abs_exposure", ascending=True)
        )
        if chart_df.empty:
            return f"{title} is unavailable."
        figure = px.bar(
            chart_df,
            x="net_exposure",
            y="category_label",
            orientation="h",
            title=title,
        )
        figure.update_layout(
            xaxis_title="Exposure % NAV",
            yaxis_title="Asset Class",
            xaxis_tickformat=".1%",
        )
        figure.add_vline(x=0, line_width=1, line_color="#8b8f9b", opacity=0.6)
        return figure

    for column in ["long_exposure", "short_exposure"]:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df = chart_df.dropna(subset=["category_label"]).copy()
    chart_df["net_exposure"] = pd.to_numeric(chart_df.get("net_exposure"), errors="coerce")
    chart_df = (
        chart_df.assign(abs_net=lambda df: df["net_exposure"].abs().fillna(0.0))
        .sort_values("abs_net", ascending=True)
    )
    if chart_df.empty:
        return f"{title} is unavailable."

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=chart_df["long_exposure"],
            y=chart_df["category_label"],
            orientation="h",
            name="Long",
        )
    )
    figure.add_trace(
        go.Bar(
            x=chart_df["short_exposure"],
            y=chart_df["category_label"],
            orientation="h",
            name="Short",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Exposure % NAV",
        yaxis_title="Asset Class",
        xaxis_tickformat=".1%",
        barmode="overlay",
    )
    figure.add_vline(x=0, line_width=1, line_color="#8b8f9b", opacity=0.6)
    return figure


def asset_class_snapshot_change_bars(change_df: pd.DataFrame, title: str):
    required = ["category_label", "long_change", "short_change", "net_change"]
    error = _require_columns(change_df, required, f"Unable to build {title.lower()}.")
    if error:
        return error

    chart_df = change_df.copy()
    for column in ["long_change", "short_change", "net_change"]:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df = chart_df.dropna(subset=["category_label", "long_change", "short_change", "net_change"])
    if chart_df.empty:
        return f"{title} is unavailable."

    chart_df = (
        chart_df.assign(abs_change=lambda df: df["net_change"].abs())
        .sort_values("abs_change", ascending=True)
    )

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=chart_df["long_change"],
            y=chart_df["category_label"],
            orientation="h",
            name="Long change",
        )
    )
    figure.add_trace(
        go.Bar(
            x=chart_df["short_change"],
            y=chart_df["category_label"],
            orientation="h",
            name="Short change",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Month-on-Month Change in Exposure % NAV",
        yaxis_title="Asset Class",
        xaxis_tickformat=".1%",
        barmode="overlay",
    )
    figure.add_vline(x=0, line_width=1, line_color="#8b8f9b", opacity=0.6)
    return figure


def asset_class_category_evolution_chart(category_df: pd.DataFrame, title: str):
    required = ["date", "long_exposure", "short_exposure", "net_exposure"]
    error = _require_columns(category_df, required, f"Unable to build {title.lower()}.")
    if error:
        return error
    chart_df = category_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    for column in ["long_exposure", "short_exposure", "net_exposure"]:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "long_exposure", "short_exposure", "net_exposure"]).sort_values("date")
    if chart_df.empty:
        return f"{title} is unavailable."

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["long_exposure"],
            mode="lines",
            name="Long",
            fill="tozeroy",
            line=dict(width=2.5),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["short_exposure"],
            mode="lines",
            name="Short",
            line=dict(width=2.0, dash="dash"),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["net_exposure"],
            mode="lines",
            name="Net",
            line=dict(width=2.5),
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Exposure % NAV",
        yaxis_tickformat=".0%",
        hovermode="x unified",
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.6)
    return figure


def asset_class_monthly_change_chart(change_df: pd.DataFrame, title: str):
    required = ["date", "long_change", "short_change"]
    error = _require_columns(change_df, required, f"Unable to build {title.lower()}.")
    if error:
        return error
    chart_df = change_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    for column in ["long_change", "short_change"]:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "long_change", "short_change"]).sort_values("date")
    if chart_df.empty:
        return f"{title} is unavailable."

    figure = go.Figure()
    figure.add_trace(go.Bar(x=chart_df["date"], y=chart_df["long_change"], name="Long contribution"))
    figure.add_trace(go.Bar(x=chart_df["date"], y=chart_df["short_change"], name="Short contribution"))
    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Monthly Change in Exposure % NAV",
        yaxis_tickformat=".1%",
        barmode="overlay",
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.6)
    return figure


def asset_class_by_month_chart(df: pd.DataFrame):
    error = _require_columns(df, ["date", "asset_class", "value_usd_m"], "Unable to build asset class by month chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["value_usd_m"] = pd.to_numeric(chart_df["value_usd_m"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "value_usd_m"]).sort_values("date")
    if chart_df.empty:
        return "Monthly asset class data is unavailable."
    latest_date = chart_df["date"].max()
    latest_df = chart_df[chart_df["date"] == latest_date]
    return px.bar(latest_df.sort_values("value_usd_m", ascending=False), x="asset_class", y="value_usd_m", title=f"Asset Class Exposure as of {latest_date.date()}")


def liquid_vs_illiquid_chart(df: pd.DataFrame):
    if df.empty:
        return "Liquid versus illiquid allocation is unavailable."
    working_df = df.copy()
    if "liquidity_bucket" in working_df.columns and "final_value_usd_m" in working_df.columns:
        working_df["liquidity_group"] = working_df["liquidity_bucket"].astype(str).apply(
            lambda value: "Liquid" if "liquid" in value.casefold() or value.casefold() == "cash" else "Illiquid"
        )
        grouped = working_df.groupby("liquidity_group", as_index=False)["final_value_usd_m"].sum()
        return px.pie(grouped, names="liquidity_group", values="final_value_usd_m", title="Liquid vs Illiquid Exposure")
    if {"asset_class", "final_value_usd_m"}.issubset(working_df.columns):
        liquid_mask = working_df["asset_class"].astype(str).str.contains("Public|Cash|Fixed Income|Hedge", case=False, na=False)
        grouped = pd.DataFrame(
            [
                {"liquidity_group": "Liquid", "final_value_usd_m": float(working_df.loc[liquid_mask, "final_value_usd_m"].sum())},
                {"liquidity_group": "Illiquid", "final_value_usd_m": float(working_df.loc[~liquid_mask, "final_value_usd_m"].sum())},
            ]
        )
        return px.pie(grouped, names="liquidity_group", values="final_value_usd_m", title="Liquid vs Illiquid Exposure")
    return "Liquid versus illiquid allocation is unavailable."


def portfolio_value_trend_chart(monthly_summary_df: pd.DataFrame):
    error = _require_columns(monthly_summary_df, ["date", "total_aum_usd_m"], "Unable to build portfolio value trend chart.")
    if error:
        return error
    chart_df = monthly_summary_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "total_aum_usd_m"])
    return px.line(chart_df.sort_values("date"), x="date", y="total_aum_usd_m", title="Portfolio Value Trend")


def cumulative_return_chart(monthly_summary_df: pd.DataFrame):
    error = _require_columns(monthly_summary_df, ["date", "total_aum_usd_m"], "Unable to build cumulative return chart.")
    if error:
        return error
    chart_df = monthly_summary_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "total_aum_usd_m"]).sort_values("date")
    chart_df["monthly_return"] = chart_df["total_aum_usd_m"].pct_change()
    chart_df = chart_df.dropna(subset=["monthly_return"])
    if chart_df.empty:
        return "Not enough monthly history to calculate cumulative returns."
    chart_df["cumulative_index"] = (1 + chart_df["monthly_return"]).cumprod()
    return px.line(chart_df, x="date", y="cumulative_index", title="Cumulative Return Index")


def monthly_return_chart(monthly_summary_df: pd.DataFrame):
    error = _require_columns(monthly_summary_df, ["date", "total_aum_usd_m"], "Unable to build monthly return chart.")
    if error:
        return error
    chart_df = monthly_summary_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "total_aum_usd_m"]).sort_values("date")
    chart_df["monthly_return"] = chart_df["total_aum_usd_m"].pct_change()
    chart_df = chart_df.dropna(subset=["monthly_return"])
    if chart_df.empty:
        return "Not enough monthly history to calculate monthly returns."
    return px.bar(chart_df, x="date", y="monthly_return", title="Monthly Returns")


def portfolio_return_bars_cumulative_line_chart(monthly_summary_df: pd.DataFrame):
    error = _require_columns(
        monthly_summary_df,
        ["date", "total_aum_usd_m"],
        "Unable to build portfolio performance chart.",
    )
    if error:
        return error
    chart_df = monthly_summary_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["total_aum_usd_m"] = pd.to_numeric(chart_df["total_aum_usd_m"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "total_aum_usd_m"]).sort_values("date")
    chart_df["monthly_return"] = chart_df["total_aum_usd_m"].pct_change()
    chart_df = chart_df.dropna(subset=["monthly_return"])
    if chart_df.empty:
        return "Not enough monthly history to calculate portfolio performance."
    chart_df["cumulative_index"] = (1 + chart_df["monthly_return"]).cumprod()

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_bar(
        x=chart_df["date"],
        y=chart_df["monthly_return"],
        name="Monthly Return",
        marker_color="#6b7c8f",
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["cumulative_index"],
            name="Cumulative Return Index",
            line=dict(color="#1f4e79", width=3),
        ),
        secondary_y=True,
    )
    figure.update_layout(
        title="Portfolio Monthly Return and Cumulative Return",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        bargap=0.15,
    )
    figure.update_yaxes(title_text="Monthly Return", tickformat=".1%", secondary_y=False)
    figure.update_yaxes(title_text="Cumulative Index", secondary_y=True)
    return figure


def asset_class_allocation_over_time_chart(df: pd.DataFrame):
    error = _require_columns(
        df,
        ["date", "asset_class", "value_usd_m"],
        "Unable to build asset class allocation trend chart.",
    )
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["value_usd_m"] = pd.to_numeric(chart_df["value_usd_m"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "value_usd_m", "asset_class"]).sort_values("date")
    if chart_df.empty:
        return "Asset class allocation history is unavailable."
    totals = chart_df.groupby("date")["value_usd_m"].transform("sum")
    chart_df["allocation_weight"] = chart_df["value_usd_m"] / totals
    return px.area(
        chart_df,
        x="date",
        y="allocation_weight",
        color="asset_class",
        title="Asset Class Allocation Over Time",
    )


def private_nav_trend_chart(private_monthly_df: pd.DataFrame):
    error = _require_columns(private_monthly_df, ["date", "fund_name", "nav_usd_m"], "Unable to build private NAV trend chart.")
    if error:
        return error
    chart_df = private_monthly_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "nav_usd_m"])
    top_funds = (
        chart_df.sort_values("date")
        .groupby("fund_name")
        .tail(1)
        .sort_values("nav_usd_m", ascending=False)
        .head(8)["fund_name"]
        .tolist()
    )
    chart_df = chart_df[chart_df["fund_name"].isin(top_funds)]
    return px.line(chart_df.sort_values("date"), x="date", y="nav_usd_m", color="fund_name", title="Private Fund NAV Trend")


def private_total_nav_trend_chart(df: pd.DataFrame):
    error = _require_columns(df, ["date", "nav_usd_m"], "Unable to build total private NAV trend chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["nav_usd_m"] = pd.to_numeric(chart_df["nav_usd_m"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "nav_usd_m"]).sort_values("date")
    if chart_df.empty:
        return "Total private NAV history is unavailable."
    return px.line(chart_df, x="date", y="nav_usd_m", title="Total Private NAV Trend")


def private_dimension_bar_chart(df: pd.DataFrame, category_column: str, value_column: str, title: str):
    error = _require_columns(df, [category_column, value_column], f"Unable to build {title.lower()}.")
    if error:
        return error
    chart_df = df.copy()
    chart_df[value_column] = pd.to_numeric(chart_df[value_column], errors="coerce")
    chart_df = chart_df.dropna(subset=[category_column, value_column]).sort_values(value_column, ascending=True)
    if chart_df.empty:
        return f"{title} is unavailable."
    return px.bar(chart_df, x=value_column, y=category_column, orientation="h", title=title)


def private_statement_lag_chart(df: pd.DataFrame):
    error = _require_columns(df, ["fund_name", "statement_lag_days"], "Unable to build private statement lag chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["statement_lag_days"] = pd.to_numeric(chart_df["statement_lag_days"], errors="coerce")
    chart_df = chart_df.dropna(subset=["fund_name", "statement_lag_days"]).sort_values("statement_lag_days")
    if chart_df.empty:
        return "Private statement lag view is unavailable."
    if chart_df["statement_lag_days"].nunique() <= 1:
        lag_days = int(chart_df["statement_lag_days"].iloc[0])
        return f"All currently tracked private funds have the same statement lag of {lag_days} days, so a lag comparison chart would not add information."
    return px.bar(chart_df, x="statement_lag_days", y="fund_name", orientation="h", title="Statement Lag by Fund")


def public_private_split_chart(df: pd.DataFrame):
    error = _require_columns(df, ["label", "value"], "Unable to build public vs private split chart.")
    if error:
        return error
    return px.pie(df, names="label", values="value", title="Public vs Private Exposure")


def top_holdings_chart(holdings_df: pd.DataFrame):
    error = _require_columns(holdings_df, ["holding_name", "final_value_usd_m"], "Unable to build top holdings chart.")
    if error:
        return error
    chart_df = holdings_df.sort_values("final_value_usd_m", ascending=False).head(10)
    return px.bar(chart_df, x="holding_name", y="final_value_usd_m", title="Top Holdings by Value")


def public_holdings_chart(df: pd.DataFrame):
    return top_holdings_chart(df)


def geography_exposure_chart(df: pd.DataFrame):
    region_column = "region"
    if "region" not in df.columns and "region_taxonomy" in df.columns:
        region_column = "region_taxonomy"
    error = _require_columns(df, [region_column, "final_value_usd_m"], "Unable to build geography exposure chart.")
    if error:
        return error
    return px.pie(df, names=region_column, values="final_value_usd_m", title="Geography Exposure")


def region_exposure_chart(df: pd.DataFrame):
    return geography_exposure_chart(df)


def currency_exposure_chart(df: pd.DataFrame):
    error = _require_columns(df, ["currency", "final_value_usd_m"], "Unable to build currency exposure chart.")
    if error:
        return error
    return px.bar(df, x="currency", y="final_value_usd_m", title="Currency Exposure")


def usd_vs_non_usd_chart(df: pd.DataFrame):
    error = _require_columns(df, ["currency", "final_value_usd_m"], "Unable to build USD versus non-USD chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["currency_group"] = chart_df["currency"].astype(str).str.upper().apply(lambda value: "USD" if value == "USD" else "Non-USD")
    grouped = chart_df.groupby("currency_group", as_index=False)["final_value_usd_m"].sum()
    return px.pie(grouped, names="currency_group", values="final_value_usd_m", title="USD vs Non-USD Exposure")


def private_fund_nav_chart(df: pd.DataFrame):
    error = _require_columns(df, ["fund_name", "current_nav_usd_m"], "Unable to build private fund NAV chart.")
    if error:
        return error
    chart_df = df.sort_values("current_nav_usd_m", ascending=False).head(15)
    return px.bar(chart_df, x="fund_name", y="current_nav_usd_m", title="Private Fund NAV by Fund")


def public_market_value_trend_chart(df: pd.DataFrame):
    error = _require_columns(df, ["date", "value_usd_m"], "Unable to build public market value trend chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["value_usd_m"] = pd.to_numeric(chart_df["value_usd_m"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "value_usd_m"]).sort_values("date")
    if chart_df.empty:
        return "Public market value history is unavailable."
    return px.line(chart_df, x="date", y="value_usd_m", title="Public Market Value Trend")


def public_proxy_performance_chart(df: pd.DataFrame):
    error = _require_columns(df, ["date", "ticker", "close"], "Unable to build public proxy performance chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["close"] = pd.to_numeric(chart_df["close"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "ticker", "close"]).sort_values(["ticker", "date"])
    if chart_df.empty:
        return "Public proxy performance history is unavailable."
    top_tickers = (
        chart_df.groupby("ticker")
        .tail(1)
        .sort_values("close", ascending=False)
        .head(8)["ticker"]
        .tolist()
    )
    chart_df = chart_df[chart_df["ticker"].isin(top_tickers)]
    chart_df["normalized_index"] = chart_df["close"] / chart_df.groupby("ticker")["close"].transform("first")
    return px.line(chart_df, x="date", y="normalized_index", color="ticker", title="Public Proxy Performance Index")


def public_proxy_basket_chart(df: pd.DataFrame):
    error = _require_columns(
        df,
        ["date", "monthly_return", "cumulative_index"],
        "Unable to build public proxy basket chart.",
    )
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["monthly_return"] = pd.to_numeric(chart_df["monthly_return"], errors="coerce")
    chart_df["cumulative_index"] = pd.to_numeric(chart_df["cumulative_index"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "monthly_return", "cumulative_index"]).sort_values("date")
    if chart_df.empty:
        return "Public proxy basket history is unavailable."

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Bar(
            x=chart_df["date"],
            y=chart_df["monthly_return"],
            name="Monthly Return",
            hovertemplate="%{x|%Y-%m}<br>Monthly Return: %{y:.2%}<extra></extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["cumulative_index"],
            mode="lines",
            name="Cumulative Index",
            line=dict(width=2.5),
            hovertemplate="%{x|%Y-%m}<br>Cumulative Index: %{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    figure.update_layout(
        title="Public Proxy Basket Return Trend",
        hovermode="x unified",
        barmode="relative",
    )
    figure.update_xaxes(title_text="Date")
    figure.update_yaxes(title_text="Monthly Return", tickformat=".1%", secondary_y=False)
    figure.update_yaxes(title_text="Cumulative Index", secondary_y=True)
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.5, secondary_y=False)
    return figure


def public_proxy_drawdown_timeseries_chart(df: pd.DataFrame):
    error = _require_columns(df, ["date", "drawdown"], "Unable to build public proxy drawdown chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df["drawdown"] = pd.to_numeric(chart_df["drawdown"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date", "drawdown"]).sort_values("date")
    if chart_df.empty:
        return "Public proxy drawdown history is unavailable."
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["drawdown"],
            mode="lines",
            fill="tozeroy",
            name="Drawdown",
            hovertemplate="%{x|%Y-%m}<br>Drawdown: %{y:.2%}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Public Proxy Basket Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown",
        yaxis_tickformat=".0%",
        hovermode="x unified",
    )
    figure.add_hline(y=0, line_width=1, line_color="#8b8f9b", opacity=0.5)
    return figure


def sector_exposure_chart(df: pd.DataFrame):
    if df.empty:
        return "Sector exposure is unavailable."
    if {"gics_sector", "final_value_usd_m"}.issubset(df.columns):
        chart_df = (
            df.groupby("gics_sector", as_index=False)["final_value_usd_m"]
            .sum()
            .sort_values("final_value_usd_m", ascending=False)
        )
        return px.bar(chart_df, x="gics_sector", y="final_value_usd_m", title="Sector Exposure")
    if {"sub_asset_class", "final_value_usd_m"}.issubset(df.columns):
        chart_df = df.groupby("sub_asset_class", as_index=False)["final_value_usd_m"].sum().sort_values("final_value_usd_m", ascending=False)
        return px.bar(chart_df, x="sub_asset_class", y="final_value_usd_m", title="Sector and Style Exposure")
    return "Sector exposure requires enriched public equity classification data."


def market_cap_exposure_chart(df: pd.DataFrame):
    if df.empty:
        return "Market cap exposure is unavailable."
    market_cap_column = "market_cap_bucket" if "market_cap_bucket" in df.columns else "current_market_cap_bucket"
    if {market_cap_column, "final_value_usd_m"}.issubset(df.columns):
        chart_df = (
            df.groupby(market_cap_column, as_index=False)["final_value_usd_m"]
            .sum()
            .sort_values("final_value_usd_m", ascending=False)
        )
        return px.bar(chart_df, x=market_cap_column, y="final_value_usd_m", title="Market Cap Exposure")
    return "Market cap exposure requires enriched holding classification data."


def classified_signed_exposure_chart(df: pd.DataFrame, category_column: str, title: str):
    if df.empty:
        return f"{title} is unavailable."
    if category_column not in df.columns:
        return f"{title} is unavailable."

    chart_df = df.copy()
    value_column = "current_delta_adjusted_exposure_usd_m" if "current_delta_adjusted_exposure_usd_m" in chart_df.columns else "current_exposure_usd_m"
    if value_column not in chart_df.columns:
        value_column = "final_value_usd_m" if "final_value_usd_m" in chart_df.columns else None
    if value_column is None:
        return f"{title} is unavailable."

    chart_df[value_column] = pd.to_numeric(chart_df[value_column], errors="coerce")
    if "position_side_current" in chart_df.columns:
        short_mask = chart_df["position_side_current"].astype(str).str.casefold().eq("short")
        chart_df.loc[short_mask, value_column] = -chart_df.loc[short_mask, value_column].abs()
        chart_df.loc[~short_mask, value_column] = chart_df.loc[~short_mask, value_column].abs()
    chart_df = chart_df.dropna(subset=[category_column, value_column]).copy()
    if chart_df.empty:
        return f"{title} is unavailable."

    chart_df[category_column] = chart_df[category_column].fillna("Unknown").astype(str)
    grouped = (
        chart_df.groupby(category_column, as_index=False)[value_column]
        .sum()
        .rename(columns={value_column: "signed_exposure_usd_m"})
    )
    grouped["abs_exposure"] = grouped["signed_exposure_usd_m"].abs()
    grouped = grouped.sort_values("abs_exposure", ascending=False).head(12).sort_values("signed_exposure_usd_m")
    if grouped.empty:
        return f"{title} is unavailable."

    figure = px.bar(
        grouped,
        x="signed_exposure_usd_m",
        y=category_column,
        orientation="h",
        title=title,
    )
    figure.update_layout(
        xaxis_title="Signed Exposure (USD m)",
        yaxis_title=category_column.replace("_", " ").title(),
    )
    figure.add_vline(x=0, line_width=1, line_color="#8b8f9b", opacity=0.6)
    return figure


def nav_by_fund_chart(private_positions_df: pd.DataFrame):
    return private_fund_nav_chart(private_positions_df)


def commitment_vs_unfunded_chart(private_positions_df: pd.DataFrame):
    error = _require_columns(
        private_positions_df,
        ["fund_name", "commitment_usd_m", "unfunded_commitment_usd_m"],
        "Unable to build commitment versus unfunded chart.",
    )
    if error:
        return error
    chart_df = private_positions_df[["fund_name", "commitment_usd_m", "unfunded_commitment_usd_m"]].copy()
    chart_df = chart_df.melt(
        id_vars="fund_name",
        value_vars=["commitment_usd_m", "unfunded_commitment_usd_m"],
        var_name="metric",
        value_name="value_usd_m",
    )
    label_map = {
        "commitment_usd_m": "Total Commitment",
        "unfunded_commitment_usd_m": "Unfunded Commitment",
    }
    chart_df["metric"] = chart_df["metric"].map(label_map)
    return px.bar(
        chart_df,
        x="fund_name",
        y="value_usd_m",
        color="metric",
        barmode="group",
        title="Commitment vs Unfunded by Fund",
    )


def paid_in_vs_unfunded_stacked_chart(private_positions_df: pd.DataFrame):
    error = _require_columns(
        private_positions_df,
        ["fund_name", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"],
        "Unable to build paid-in versus unfunded chart.",
    )
    if error:
        return error
    chart_df = private_positions_df[["fund_name", "paid_in_capital_usd_m", "unfunded_commitment_usd_m"]].copy()
    chart_df = chart_df.melt(
        id_vars="fund_name",
        value_vars=["paid_in_capital_usd_m", "unfunded_commitment_usd_m"],
        var_name="metric",
        value_name="value_usd_m",
    )
    label_map = {
        "paid_in_capital_usd_m": "Paid-in Capital",
        "unfunded_commitment_usd_m": "Unfunded Commitment",
    }
    chart_df["metric"] = chart_df["metric"].map(label_map)
    return px.bar(
        chart_df,
        x="fund_name",
        y="value_usd_m",
        color="metric",
        barmode="stack",
        title="Paid-in vs Unfunded Commitment",
    )


def paid_in_vs_unfunded_chart(df: pd.DataFrame):
    return paid_in_vs_unfunded_stacked_chart(df)


def cash_balance_chart(df: pd.DataFrame):
    error = _require_columns(df, ["account_name", "balance_usd_m"], "Unable to build cash balance chart.")
    if error:
        return error
    return px.bar(df, x="account_name", y="balance_usd_m", color="currency", title="Cash & Liquidity Balances")


def cash_by_account_chart(cash_df: pd.DataFrame):
    return cash_balance_chart(cash_df)


def cash_by_currency_chart(cash_df: pd.DataFrame):
    error = _require_columns(cash_df, ["currency", "balance_usd_m"], "Unable to build cash by currency chart.")
    if error:
        return error
    chart_df = cash_df.groupby("currency", as_index=False)["balance_usd_m"].sum().sort_values("balance_usd_m", ascending=False)
    return px.bar(chart_df, x="currency", y="balance_usd_m", title="Cash by Currency")


def document_status_chart(df: pd.DataFrame):
    error = _require_columns(
        df,
        ["validation_review_status"],
        "Unable to build document status chart.",
    )
    if error:
        return error
    counts = df["validation_review_status"].value_counts().rename_axis("status").reset_index(name="count")
    return px.bar(counts, x="status", y="count", color="status", title="Document Processing Status")


def review_status_chart(df: pd.DataFrame):
    error = _require_columns(df, ["review_status"], "Unable to build review status chart.")
    if error:
        return error
    counts = df["review_status"].value_counts().rename_axis("status").reset_index(name="count")
    return px.bar(counts, x="status", y="count", color="status", title="Review Queue Status")


def capital_call_timeline_chart(df: pd.DataFrame):
    error = _require_columns(df, ["fund_name", "due_date", "amount_due_usd_m"], "Unable to build capital call timeline.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["due_date"] = pd.to_datetime(chart_df["due_date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["due_date"])
    if chart_df.empty:
        return "No approved capital calls available for timeline display."
    return px.scatter(
        chart_df,
        x="due_date",
        y="amount_due_usd_m",
        color="fund_name",
        size="amount_due_usd_m",
        title="Upcoming Capital Calls",
    )


def capital_call_calendar_chart(capital_calls_df: pd.DataFrame):
    error = _require_columns(
        capital_calls_df,
        ["fund_name", "due_date", "amount_due_usd_m"],
        "Unable to build capital call calendar chart.",
    )
    if error:
        return error
    chart_df = capital_calls_df.copy()
    chart_df["due_date"] = pd.to_datetime(chart_df["due_date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["due_date"])
    if chart_df.empty:
        return "No approved capital calls are currently scheduled."
    return px.bar(
        chart_df.sort_values("due_date"),
        x="due_date",
        y="amount_due_usd_m",
        color="fund_name",
        title="Capital Call Calendar",
    )


def cashflow_chart(df: pd.DataFrame):
    error = _require_columns(
        df,
        ["cashflow_date", "expected_cash_inflow_usd_m", "fund_name"],
        "Unable to build cashflow chart.",
    )
    if error:
        return error
    chart_df = df.copy()
    chart_df["cashflow_date"] = pd.to_datetime(chart_df["cashflow_date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["cashflow_date"])
    if chart_df.empty:
        return "No private market cashflows available for charting."
    if chart_df["cashflow_date"].nunique() <= 1:
        chart_df["cashflow_event"] = (
            chart_df["fund_name"].astype(str)
            + " | "
            + chart_df["cashflow_date"].dt.strftime("%Y-%m-%d")
        )
        return px.bar(
            chart_df,
            x="cashflow_event",
            y="expected_cash_inflow_usd_m",
            color="fund_name",
            title="Expected Private Market Cashflows",
        )
    return px.bar(
        chart_df.sort_values("cashflow_date"),
        x="cashflow_date",
        y="expected_cash_inflow_usd_m",
        color="fund_name",
        title="Expected Private Market Cashflows",
    )


def private_market_cashflow_chart(cashflows_df: pd.DataFrame):
    error = _require_columns(
        cashflows_df,
        ["cashflow_date", "fund_name"],
        "Unable to build private market cashflow chart.",
    )
    if error:
        return error
    chart_df = cashflows_df.copy()
    chart_df["cashflow_date"] = pd.to_datetime(chart_df["cashflow_date"], errors="coerce")
    amount_column = None
    for candidate in ["expected_cash_inflow_usd_m", "net_distribution_usd_m", "gross_distribution_usd_m"]:
        if candidate in chart_df.columns:
            amount_column = candidate
            break
    if amount_column is None:
        return "No private market cashflow amount column is available."
    chart_df[amount_column] = pd.to_numeric(chart_df[amount_column], errors="coerce")
    chart_df = chart_df.dropna(subset=["cashflow_date", amount_column])
    if chart_df.empty:
        return "No private market cashflows available for charting."
    if chart_df["cashflow_date"].nunique() <= 1:
        if "cashflow_type" in chart_df.columns:
            chart_df["cashflow_event"] = (
                chart_df["fund_name"].astype(str)
                + " | "
                + chart_df["cashflow_type"].astype(str)
                + " | "
                + chart_df["cashflow_date"].dt.strftime("%Y-%m-%d")
            )
        else:
            chart_df["cashflow_event"] = (
                chart_df["fund_name"].astype(str)
                + " | "
                + chart_df["cashflow_date"].dt.strftime("%Y-%m-%d")
            )
        return px.bar(
            chart_df,
            x="cashflow_event",
            y=amount_column,
            color="cashflow_type" if "cashflow_type" in chart_df.columns else "fund_name",
            hover_data=["fund_name"] if "fund_name" in chart_df.columns else None,
            title="Expected Private Market Cashflows",
        )
    return px.bar(
        chart_df.sort_values("cashflow_date"),
        x="cashflow_date",
        y=amount_column,
        color="cashflow_type" if "cashflow_type" in chart_df.columns else "fund_name",
        hover_data=["fund_name"] if "fund_name" in chart_df.columns else None,
        title="Expected Private Market Cashflows",
    )


def distribution_timeline_chart(df: pd.DataFrame):
    if df.empty:
        return "Distribution timeline is unavailable."
    chart_df = df.copy()
    if "cashflow_type" in chart_df.columns:
        chart_df = chart_df[chart_df["cashflow_type"].astype(str).str.contains("distribution", case=False, na=False)]
    if chart_df.empty:
        return "No approved distributions are available in the current dataset."
    required = ["cashflow_date", "fund_name"]
    error = _require_columns(chart_df, required, "Unable to build distribution timeline.")
    if error:
        return error
    chart_df["cashflow_date"] = pd.to_datetime(chart_df["cashflow_date"], errors="coerce")
    amount_column = next(
        (column for column in ["expected_cash_inflow_usd_m", "net_distribution_usd_m", "gross_distribution_usd_m"] if column in chart_df.columns),
        None,
    )
    if amount_column is None:
        return "No distribution amount column is available."
    chart_df[amount_column] = pd.to_numeric(chart_df[amount_column], errors="coerce")
    chart_df = chart_df.dropna(subset=["cashflow_date", amount_column])
    if chart_df.empty:
        return "No approved distributions are available in the current dataset."

    projected = chart_df.get("liquidity_treatment", pd.Series("", index=chart_df.index)).astype(str).str.contains("projected", case=False, na=False)
    historical = chart_df.get("update_type", pd.Series("", index=chart_df.index)).astype(str).str.contains("historical", case=False, na=False)
    chart_df["Cashflow Status"] = "Booked"
    chart_df.loc[historical, "Cashflow Status"] = "Historical / Booked"
    chart_df.loc[projected, "Cashflow Status"] = "Projected"
    chart_df["Amount (USD m)"] = chart_df[amount_column]

    hover_columns = [
        column
        for column in ["fund_name", "Cashflow Status", "gross_distribution_usd_m", "net_distribution_usd_m", "expected_cash_inflow_usd_m"]
        if column in chart_df.columns
    ]
    figure = px.scatter(
        chart_df.sort_values("cashflow_date"),
        x="cashflow_date",
        y="Amount (USD m)",
        color="fund_name",
        symbol="Cashflow Status",
        size="Amount (USD m)",
        hover_data=hover_columns,
        title="Distribution Timeline",
        labels={"cashflow_date": "Expected / booked date", "fund_name": "Fund"},
    )
    figure.update_traces(marker={"line": {"width": 1, "color": "white"}}, selector={"mode": "markers"})
    figure.update_xaxes(type="date")
    return figure


def projected_distributions_by_fund_chart(df: pd.DataFrame):
    error = _require_columns(df, ["fund_name"], "Unable to build projected distributions by fund chart.")
    if error:
        return error
    amount_column = next(
        (column for column in ["expected_cash_inflow_usd_m", "net_distribution_usd_m", "gross_distribution_usd_m"] if column in df.columns),
        None,
    )
    if amount_column is None:
        return "No distribution amount column is available."

    chart_df = df.copy()
    chart_df[amount_column] = pd.to_numeric(chart_df[amount_column], errors="coerce")
    chart_df = (
        chart_df.dropna(subset=["fund_name", amount_column])
        .groupby("fund_name", as_index=False)[amount_column]
        .sum()
        .rename(columns={amount_column: "Projected Distribution (USD m)"})
        .sort_values("Projected Distribution (USD m)")
    )
    if chart_df.empty:
        return "No approved projected distributions are available."

    figure = px.bar(
        chart_df,
        x="Projected Distribution (USD m)",
        y="fund_name",
        orientation="h",
        text_auto=".2f",
        title="Projected Distributions by Fund",
        labels={"fund_name": "Fund"},
    )
    figure.update_traces(marker_color="#2563EB", textposition="outside", hovertemplate="%{y}<br>Projected distribution: USD %{x:.2f}m<extra></extra>")
    figure.update_layout(showlegend=False)
    return figure


def unfunded_commitments_by_fund_chart(private_positions_df: pd.DataFrame):
    error = _require_columns(
        private_positions_df,
        ["fund_name", "unfunded_commitment_usd_m"],
        "Unable to build unfunded commitments chart.",
    )
    if error:
        return error
    chart_df = private_positions_df.sort_values("unfunded_commitment_usd_m", ascending=False).head(15)
    return px.bar(chart_df, x="fund_name", y="unfunded_commitment_usd_m", title="Unfunded Commitments by Fund")


def liquidity_coverage_chart(cash_df: pd.DataFrame, capital_calls_df: pd.DataFrame):
    cash_error = _require_columns(cash_df, ["balance_usd_m"], "Unable to build liquidity coverage chart.")
    if cash_error and not capital_calls_df.empty:
        return cash_error
    cash_value = pd.to_numeric(cash_df.get("balance_usd_m", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    calls_value = pd.to_numeric(capital_calls_df.get("amount_due_usd_m", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    if cash_value == 0 and calls_value == 0:
        return "Liquidity coverage is unavailable because cash and approved capital call data are both empty."
    compare_df = pd.DataFrame(
        [
            {"metric": "Cash & Liquidity", "value_usd_m": cash_value},
            {"metric": "Upcoming Capital Calls", "value_usd_m": calls_value},
        ]
    )
    return px.bar(compare_df, x="metric", y="value_usd_m", color="metric", title="Liquidity Coverage vs Upcoming Calls")


def liquidity_horizon_coverage_chart(liquidity_horizon_df: pd.DataFrame):
    error = _require_columns(
        liquidity_horizon_df,
        ["Horizon", "Hard Coverage", "Soft Coverage"],
        "Unable to build liquidity horizon coverage chart.",
    )
    if error:
        return error
    chart_df = liquidity_horizon_df.copy()
    chart_df["Hard Coverage"] = pd.to_numeric(chart_df["Hard Coverage"], errors="coerce")
    chart_df["Soft Coverage"] = pd.to_numeric(chart_df["Soft Coverage"], errors="coerce")
    chart_df = chart_df.dropna(subset=["Horizon"], how="all")
    if chart_df.empty:
        return "Liquidity horizon coverage is unavailable."
    plot_df = chart_df.melt(
        id_vars="Horizon",
        value_vars=["Hard Coverage", "Soft Coverage"],
        var_name="Coverage Type",
        value_name="Coverage Ratio",
    )
    plot_df = plot_df.dropna(subset=["Coverage Ratio"])
    if plot_df.empty:
        return "Liquidity horizon coverage is unavailable."
    figure = px.bar(
        plot_df,
        x="Horizon",
        y="Coverage Ratio",
        color="Coverage Type",
        barmode="group",
        title="Coverage by Horizon",
    )
    figure.update_layout(yaxis_tickformat=".1f")
    figure.add_hline(y=1.0, line_width=1, line_color="#8b8f9b", opacity=0.5)
    return figure


def cash_purpose_chart(cash_df: pd.DataFrame):
    error = _require_columns(cash_df, ["purpose", "balance_usd_m"], "Unable to build cash purpose chart.")
    if error:
        return error
    chart_df = cash_df.copy()
    chart_df["balance_usd_m"] = pd.to_numeric(chart_df["balance_usd_m"], errors="coerce")
    chart_df = (
        chart_df.dropna(subset=["purpose", "balance_usd_m"])
        .groupby("purpose", as_index=False)["balance_usd_m"]
        .sum()
        .sort_values("balance_usd_m", ascending=False)
    )
    if chart_df.empty:
        return "Cash purpose view is unavailable."
    return px.bar(chart_df, x="purpose", y="balance_usd_m", title="Cash by Purpose")


def risk_metric_bar_chart(df: pd.DataFrame):
    error = _require_columns(df, ["ticker", "annualized_volatility"], "Unable to build risk metric bar chart.")
    if error:
        return error
    return px.bar(df.sort_values("annualized_volatility", ascending=False), x="ticker", y="annualized_volatility", title="Annualized Volatility by Ticker")


def drawdown_chart(df: pd.DataFrame):
    error = _require_columns(df, ["ticker", "max_drawdown"], "Unable to build drawdown chart.")
    if error:
        return error
    chart_df = df.copy().sort_values("max_drawdown")
    return px.bar(chart_df, x="ticker", y="max_drawdown", title="Max Drawdown by Proxy")


def correlation_heatmap(df: pd.DataFrame):
    if df.empty:
        return "Correlation matrix is unavailable."
    figure = go.Figure(
        data=go.Heatmap(
            z=df.values,
            x=list(df.columns),
            y=list(df.index),
            colorscale="RdBu",
            zmid=0,
        )
    )
    figure.update_layout(title="Correlation Heatmap")
    return figure


def stress_test_chart(df: pd.DataFrame):
    error = _require_columns(df, ["scenario", "stress_return"], "Unable to build stress test chart.")
    if error:
        return error
    scenario_df = df.groupby("scenario", as_index=False)["stress_return"].mean()
    return px.bar(scenario_df, x="scenario", y="stress_return", title="Average Stress Shock by Scenario")


def risk_dimension_chart(df: pd.DataFrame, category_column: str, value_column: str, title: str):
    error = _require_columns(df, [category_column, value_column], f"Unable to build {title.lower()}.")
    if error:
        return error
    chart_df = df.copy()
    chart_df[value_column] = pd.to_numeric(chart_df[value_column], errors="coerce")
    chart_df = chart_df.dropna(subset=[category_column, value_column]).sort_values(value_column)
    if chart_df.empty:
        return f"{title} is unavailable."
    return px.bar(chart_df, x=value_column, y=category_column, orientation="h", title=title)


def stress_scenario_impact_chart(df: pd.DataFrame):
    error = _require_columns(df, ["scenario", "scenario_impact_pct_nav"], "Unable to build stress scenario impact chart.")
    if error:
        return error
    chart_df = df.copy()
    chart_df["scenario_impact_pct_nav"] = pd.to_numeric(chart_df["scenario_impact_pct_nav"], errors="coerce")
    chart_df = chart_df.dropna(subset=["scenario", "scenario_impact_pct_nav"]).sort_values("scenario_impact_pct_nav")
    if chart_df.empty:
        return "Stress scenario impact view is unavailable."
    figure = px.bar(chart_df, x="scenario", y="scenario_impact_pct_nav", title="Stress Scenario Impact (% NAV)")
    figure.update_layout(yaxis_tickformat=".1%")
    return figure


def stress_scenario_breakdown_chart(df: pd.DataFrame, category_column: str, title: str):
    error = _require_columns(df, [category_column, "scenario_pnl_usd_m"], f"Unable to build {title.lower()}.")
    if error:
        return error
    chart_df = (
        df.copy()
        .groupby(category_column, as_index=False)["scenario_pnl_usd_m"]
        .sum()
        .sort_values("scenario_pnl_usd_m")
    )
    if chart_df.empty:
        return f"{title} is unavailable."
    return px.bar(chart_df, x="scenario_pnl_usd_m", y=category_column, orientation="h", title=title)
