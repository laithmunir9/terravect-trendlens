"""Pure Plotly figures, independent of Streamlit and network access."""
from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go

from analysis import align_annual

COLORS = ['#087f83', '#bb5b29']


def style_chart(fig: go.Figure, start: int, end: int, ylabel: str):
    step = max(1, math.ceil((end - start) / 5))
    ticks = sorted(set(range(start, end + 1, step)) | {end})
    fig.update_layout(
        height=400, hovermode='x unified',
        margin=dict(l=20, r=20, b=90, t=30),
        font=dict(family='Inter, Arial, sans-serif', color='#385360', size=12),
        paper_bgcolor='white', plot_bgcolor='white',
        legend=dict(orientation='h', yanchor='top', y=-0.22, x=0, font=dict(size=11)),
        xaxis=dict(title=None, type='linear', range=[start - .5, end + .5],
                   tickmode='array', tickvals=ticks, tickformat='d', automargin=True,
                   showgrid=False),
        yaxis=dict(title=ylabel, automargin=True, zeroline=False, gridcolor='#e9eff2'),
        template='plotly_white',
    )
    return fig


def build_chart(annual: pd.DataFrame, info: dict | None, name: str,
                start: int, end: int) -> go.Figure:
    if start > end:
        raise ValueError('Start year must not exceed end year.')
    # Include missing years as NaN, so observed annual lines never bridge gaps.
    selected = annual[annual['year'].between(start, end)]
    display = selected.set_index('year').reindex(range(start, end + 1))
    fig = go.Figure(go.Scatter(
        x=display.index.tolist(), y=display['value'].tolist(), mode='lines+markers',
        name='Annual mean', connectgaps=False, line=dict(width=2.5, color='#007C91'),
        marker=dict(size=6), hovertemplate='%{x}: %{y:.2f} °C<extra>Annual mean</extra>'))
    if info is not None:
        fig.add_trace(go.Scatter(
            x=info['fitted']['year'].tolist(), y=info['fitted']['value'].tolist(),
            mode='lines', name='OLS fit (unadjusted)',
            line=dict(dash='dash', width=2, color='#D97706'),
            hovertemplate='%{y:.2f} °C<extra>OLS fit</extra>'))
    return style_chart(fig, start, end, 'Annual mean temperature (°C)')


def comparison_data(first: pd.DataFrame, second: pd.DataFrame,
                    start: int, end: int) -> pd.DataFrame:
    """Centered values use each point's mean of the exact same complete years."""
    left, right = align_annual(first[first.year.between(start, end)],
                               second[second.year.between(start, end)])
    result = pd.DataFrame({'year': left.year, 'first_temperature_c': left.value,
                           'second_temperature_c': right.value})
    for prefix in ('first', 'second'):
        values = result[f'{prefix}_temperature_c']
        result[f'{prefix}_departure_c'] = values - values.mean()
    return result


def build_comparison_chart(first: pd.DataFrame, second: pd.DataFrame,
                           names: tuple[str, str], start: int, end: int,
                           relative: bool = True) -> go.Figure:
    if start > end:
        raise ValueError('Start year must not exceed end year.')
    data = comparison_data(first, second, start, end)
    display = data.set_index('year').reindex(range(start, end + 1))
    fig = go.Figure()
    for i, prefix in enumerate(('first', 'second')):
        suffix = 'departure_c' if relative else 'temperature_c'
        fig.add_trace(go.Scatter(
            x=display.index.tolist(), y=display[f'{prefix}_{suffix}'].tolist(),
            name=names[i], mode='lines+markers', connectgaps=False,
            line=dict(color=COLORS[i], width=2.5, dash='solid' if i == 0 else 'dot'),
            marker=dict(size=6, symbol='circle' if i == 0 else 'diamond'),
            hovertemplate='%{x}: %{y:+.2f} °C<extra>%{fullData.name}</extra>'))
    if relative:
        fig.add_hline(y=0, line_width=1, line_color='#91a7b3', line_dash='dash')
    return style_chart(fig, start, end,
                       'Departure from own period mean (°C)' if relative else 'Annual mean temperature (°C)')
