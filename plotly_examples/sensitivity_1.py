"""Interactive multi-column scatter plot interface with statistics."""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, MATCH, ALL
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any

# # Debug Configuration
# PYTHON_DEBUG = True  # Controls Python-side logging
# JS_DEBUG_CONFIG = True  # This will be passed to JavaScript

# def debug_log(message: str) -> None:
#     """Python-side debug logging."""
#     if PYTHON_DEBUG:
#         print(f"[PY] {message}")
# Debug Configuration
PYTHON_DEBUG = True

def debug_log(message: str) -> None:
    """Python-side debug logging."""
    if PYTHON_DEBUG:
        print(f"[PY] {message}")

def calculate_statistics(series1: pd.Series, series2: pd.Series) -> Dict[str, Any]:
    """Calculate statistics for a pair of series."""
    try:
        # Drop NA values that exist in either series
        mask = ~(series1.isna() | series2.isna())
        clean_s1 = series1[mask]
        clean_s2 = series2[mask]
        
        if len(clean_s1) < 2:  # Need at least 2 points for most statistics
            return {
                "correlation": "N/A",
                "samples": len(clean_s1),
                "missing": len(series1) - len(clean_s1),
                "x_mean": f"{clean_s1.mean():.3f}" if len(clean_s1) > 0 else "N/A",
                "y_mean": f"{clean_s2.mean():.3f}" if len(clean_s2) > 0 else "N/A"
            }

        stats_dict = {
            "correlation": f"{clean_s1.corr(clean_s2):.3f}",
            "samples": len(clean_s1),
            "missing": len(series1) - len(clean_s1),
            "x_mean": f"{clean_s1.mean():.3f}",
            "y_mean": f"{clean_s2.mean():.3f}",
            "x_std": f"{clean_s1.std():.3f}",
            "y_std": f"{clean_s2.std():.3f}"
        }
        
        # Calculate linear regression
        slope, intercept = np.polyfit(clean_s1, clean_s2, 1)
        stats_dict["regression"] = f"y = {slope:.3f}x + {intercept:.3f}"
        
        return stats_dict
    except Exception as e:
        if PYTHON_DEBUG:
            print(f"[PY] Error calculating statistics: {e}")
        return {"error": str(e)}

# Create sample data
df1 = pd.DataFrame({
    'A': np.random.randn(100),
    'B': np.random.randn(100),
    'C': np.random.randn(100),
    'D': np.random.randn(100),
    'Category': np.random.choice(['X', 'Y', 'Z'], 100)
})

df2 = pd.DataFrame({
    'W': np.random.randn(100),
    'X': np.random.randn(100),
    'Y': np.random.randn(100),
    'Z': np.random.randn(100),
    'Group': np.random.choice(['P', 'Q', 'R'], 100)
})

# # Initialize the Dash app
# app = dash.Dash(__name__)
# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Styles with debug-friendly positioning
dropdown_style = {
    'width': '100%',
    'marginBottom': '20px',
    'zIndex': 999,
}

info_panel_style = {
    'position': 'fixed',  # Fixed positioning for hover panel
    'backgroundColor': 'white',
    'padding': '15px',
    'borderRadius': '5px',
    'boxShadow': '0 0 10px rgba(0,0,0,0.3)',
    'zIndex': 1000,
    'display': 'none',
    'minWidth': '200px',
    'maxWidth': '300px',
    'fontSize': '12px'
}

color_picker_style = {
    'position': 'fixed',
    'top': '50%',
    'left': '50%',
    'transform': 'translate(-50%, -50%)',
    'backgroundColor': 'white',
    'padding': '20px',
    'borderRadius': '5px',
    'boxShadow': '0 0 10px rgba(0,0,0,0.3)',
    'zIndex': 1001,
    'display': 'none'
}

# Available colors
COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
]

# JavaScript code for hover handling
hover_script = """
const JS_DEBUG = true;  // JavaScript debug flag

function debugLog(message) {
    if (JS_DEBUG) {
        console.log(`[JS] ${message}`);
    }
}

function initializeHoverHandlers() {
    debugLog('Initializing hover handlers');
    const legendItems = document.getElementsByClassName('legend-item');
    const infoPanel = document.getElementById('series-info-panel');
    
    function positionPanel(event, item) {
        const rect = item.getBoundingClientRect();
        const panel = infoPanel.getBoundingClientRect();
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };
        
        // Try positioning to the right first
        let left = rect.right + 10;
        if (left + panel.width > viewport.width) {
            // Fall back to left side if not enough space
            left = rect.left - panel.width - 10;
        }
        
        let top = rect.top;
        if (top + panel.height > viewport.height) {
            top = viewport.height - panel.height - 10;
        }
        
        debugLog(`Positioning panel at (${left}, ${top})`);
        
        infoPanel.style.left = `${left}px`;
        infoPanel.style.top = `${top}px`;
    }
    
    function handleMouseEnter(event) {
        const item = event.currentTarget;
        debugLog(`Mouse enter: ${item.getAttribute('data-series')}`);
        
        // Show panel and position it
        infoPanel.style.display = 'block';
        positionPanel(event, item);
    }
    
    function handleMouseLeave(event) {
        debugLog('Mouse leave');
        infoPanel.style.display = 'none';
    }
    
    // Attach handlers to all legend items
    Array.from(legendItems).forEach(item => {
        item.addEventListener('mouseenter', handleMouseEnter);
        item.addEventListener('mouseleave', handleMouseLeave);
    });
    
    debugLog(`Attached handlers to ${legendItems.length} items`);
}

// Initialize handlers when content updates
if (window.dash_clientside) {
    window.dash_clientside.clientside = {
        initializeHover: function(children) {
            if (!children) return window.dash_clientside.no_update;
            
            // Use setTimeout to ensure DOM is ready
            setTimeout(initializeHoverHandlers, 100);
            return window.dash_clientside.no_update;
        }
    };
}
"""

# Define the layout
app.layout = html.Div([
    html.H1("DataFrame Column Comparison"),
    
    # Add the hover handling script
    html.Script(hover_script),
    
    # Control panel for column selection
    html.Div([
        html.Div([
            html.H3("Select X-axis Columns (DataFrame 1)"),
            dcc.Dropdown(
                id='df1-columns',
                options=[{'label': col, 'value': col} for col in df1.columns if col != 'Category'],
                value=[],
                multi=True,
                style=dropdown_style
            ),
        ], style={'width': '45%', 'display': 'inline-block', 'margin': '5px'}),
        
        html.Div([
            html.H3("Select Y-axis Columns (DataFrame 2)"),
            dcc.Dropdown(
                id='df2-columns',
                options=[{'label': col, 'value': col} for col in df2.columns if col != 'Group'],
                value=[],
                multi=True,
                style=dropdown_style
            ),
        ], style={'width': '45%', 'display': 'inline-block', 'margin': '5px'}),
    ]),
    
    # Plot settings
    # html.Div([
    #     html.H3("Plot Settings", style={'marginBottom': '5px'}),
    #     dcc.Checklist(
    #         id='plot-settings',
    #         options=[
    #             {'label': ' Show trend lines', 'value': 'trend'},
    #             {'label': ' Show point labels', 'value': 'labels'}
    #         ],
    #         value=['trend'],
    #         style={'display': 'flex', 'gap': '20px'},
    #         inputStyle={'marginRight': '5px'},
    #         labelStyle={'display': 'flex', 'alignItems': 'center'}
    #     )
    # ], style={'margin': '10px'}),
    
    # Graph and custom legend
    html.Div([
        # Plot settings
        html.Div([
            html.H3("Plot Settings", style={'marginBottom': '5px'}),
            dcc.Checklist(
                id='plot-settings',
                options=[
                    {'label': ' Show trend lines', 'value': 'trend'},
                    {'label': ' Show point labels', 'value': 'labels'}
                ],
                value=['trend'],
                style={'display': 'block', 'gap': '10px'},  # Changed from 'flex' to 'block'
                inputStyle={'marginRight': '5px'},
                labelStyle={'display': 'block', 'marginBottom': '10px'}  # Added marginBottom and changed to block
            )
        ], style={'width': '10%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        # Main plot
        html.Div([
            dcc.Graph(
                id='scatter-plot',
                style={'height': '700px'}
            ),
        ], style={'width': '70%', 'display': 'inline-block'}),
        
        # Custom legend
        html.Div([
            html.H3("Series"),
            html.Div(id='custom-legend', style={
                'overflowY': 'auto',
                'maxHeight': '600px'
            })
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    
    ]),
    
    # Info panel (hidden by default)
    html.Div(id='series-info-panel', style=info_panel_style),
    
    # Color picker panel (hidden by default)
    html.Div([
        html.H3("Select Color"),
        html.Div(
            [html.Button(
                style={'backgroundColor': color, 'width': '30px', 'height': '30px', 'margin': '5px'},
                id={'type': 'color-option', 'index': i}
            ) for i, color in enumerate(COLORS)],
            style={'display': 'grid', 'gridTemplateColumns': 'repeat(5, 1fr)', 'gap': '5px'}
        ),
        html.Button("Close", id='close-color-picker', style={'marginTop': '10px'})
    ], id='color-picker-panel', style=color_picker_style),
    
    # Store components
    dcc.Store(id='series-colors'),
    dcc.Store(id='series-data'),
    dcc.Store(id='active-series')
])

app.clientside_callback(
    """
    function(children) {
        if (!children) return window.dash_clientside.no_update;
        
        const JS_DEBUG = true;
        
        function debugLog(message) {
            if (JS_DEBUG) console.log('[JS]', message);
        }
        
        function setupHoverHandlers() {
            debugLog('Setting up hover handlers');
            const items = document.getElementsByClassName('legend-item');
            const panel = document.getElementById('series-info-panel');
            
            Array.from(items).forEach(item => {
                item.onmouseenter = (e) => {
                    const series = item.getAttribute('data-series');
                    debugLog(`Hover enter: ${series}`);
                    
                    // Position the panel
                    const rect = item.getBoundingClientRect();
                    let left = rect.right + 10;
                    
                    // Check if panel would go off-screen
                    if (left + 300 > window.innerWidth) {  // 300px is max panel width
                        left = rect.left - 310;  // Position to left with 10px margin
                    }
                    
                    panel.style.left = left + 'px';
                    panel.style.top = rect.top + 'px';
                    panel.style.display = 'block';
                };
                
                item.onmouseleave = (e) => {
                    debugLog('Hover leave');
                    panel.style.display = 'none';
                };
            });
        }
        
        // Allow time for DOM to update
        setTimeout(setupHoverHandlers, 100);
        return window.dash_clientside.no_update;
    }
    """,
    Output('custom-legend', 'data-update'),
    Input('custom-legend', 'children')
)

@app.callback(
    [Output('custom-legend', 'children'),
     Output('series-colors', 'data'),
     Output('series-data', 'data')],
    [Input('df1-columns', 'value'),
     Input('df2-columns', 'value')],
    [State('series-colors', 'data')]
)
def update_legend(df1_cols, df2_cols, existing_colors):
    """Update custom legend with interactive elements."""
    debug_log("Updating legend")
    legend_items = []
    color_data = existing_colors or {}
    series_stats = {}
    
    if not df1_cols or not df2_cols:
        debug_log("No columns selected")
        return [], color_data, {}
    
    for x_col in df1_cols:
        for y_col in df2_cols:
            series_name = f'{x_col} vs {y_col}'
            debug_log(f"Processing series: {series_name}")
            
            if series_name not in color_data:
                color_data[series_name] = COLORS[len(color_data) % len(COLORS)]
            
            color = color_data[series_name]
            stats = calculate_statistics(df1[x_col], df2[y_col])
            series_stats[series_name] = stats
            
            legend_items.append(html.Div([
                html.Button(
                    style={
                        'backgroundColor': color,
                        'width': '20px',
                        'height': '20px',
                        'marginRight': '10px',
                        'verticalAlign': 'middle',
                        'cursor': 'pointer',
                        'border': '1px solid #ddd'
                    },
                    id={'type': 'color-button', 'index': series_name}
                ),
                html.Span(
                    series_name,
                    style={
                        'cursor': 'default',
                        'userSelect': 'none',
                        'display': 'inline-block'
                    }
                )
            ],
            className='legend-item',
            id={'type': 'legend-item', 'index': series_name},
            **{
                'data-series': series_name,
                'style': {
                    'margin': '10px',
                    'padding': '5px',
                    'borderRadius': '3px',
                }
            }))
    
    color_data = {k: v for k, v in color_data.items() 
                 if any(x in k for x in df1_cols) and any(y in k for y in df2_cols)}
    
    debug_log(f"Created {len(legend_items)} legend items")
    return legend_items, color_data, series_stats

@app.callback(
    [Output('series-info-panel', 'children'),
     Output('series-info-panel', 'style')],
    [Input({'type': 'legend-item', 'index': ALL}, 'mouseenter'),
     Input({'type': 'legend-item', 'index': ALL}, 'mouseleave')],
    [State('series-data', 'data'),
     State('series-info-panel', 'style')]
)
def update_info_panel(mouseenter, mouseleave, series_data, current_style):
    """Update the info panel content and visibility."""
    if not dash.callback_context.triggered:
        return dash.no_update, dash.no_update
        
    trigger = dash.callback_context.triggered[0]
    
    # Handle mouseleave
    if '.mouseleave' in trigger['prop_id']:
        return dash.no_update, dict(current_style, display='none')
    
    # Handle mouseenter
    if '.mouseenter' in trigger['prop_id']:
        try:
            series_name = eval(trigger['prop_id'].split('.')[0])['index']
            stats = series_data.get(series_name, {})
            
            content = html.Div([
                html.H4(f"Statistics: {series_name}", 
                       style={'marginTop': 0, 'marginBottom': '10px'}),
                html.Table([
                    html.Tr([
                        html.Td(k, style={'padding': '3px', 'fontWeight': 'bold'}),
                        html.Td(str(v), style={'padding': '3px'})
                    ]) for k, v in stats.items()
                ], style={'borderCollapse': 'collapse'})
            ])
            
            return content, dict(current_style, display='block')
            
        except Exception as e:
            debug_log(f"Error updating info panel: {e}")
            return dash.no_update, dash.no_update
    
    return dash.no_update, dash.no_update

# @app.callback(
#     [Output('color-picker-panel', 'style'),
#      Output('active-series', 'data')],
#     [Input({'type': 'color-button', 'index': ALL}, 'n_clicks'),
#      Input('close-color-picker', 'n_clicks')],
#     [State({'type': 'color-button', 'index': ALL}, 'id')]
# )
# def toggle_color_picker(button_clicks, close_clicks, button_ids):
#     """Show/hide color picker when clicking color buttons."""
#     ctx = dash.callback_context
#     if not ctx.triggered:
#         return dict(color_picker_style, display='none'), None
    
#     triggered_id = ctx.triggered[0]['prop_id']
    
#     if 'close-color-picker' in triggered_id or not any(button_clicks):
#         debug_log("Closing color picker")
#         return dict(color_picker_style, display='none'), None
    
#     if 'color-button' in triggered_id:
#         button_idx = next(i for i, c in enumerate(button_clicks) if c)
#         series_name = button_ids[button_idx]['index']
#         debug_log(f"Opening color picker for {series_name}")
#         return dict(color_picker_style, display='block'), series_name
    
#     return dict(color_picker_style, display='none'), None

# @app.callback(
#     Output('series-colors', 'data', allow_duplicate=True),
#     [Input({'type': 'color-option', 'index': ALL}, 'n_clicks')],
#     [State({'type': 'color-option', 'index': ALL}, 'id'),
#      State('active-series', 'data'),
#      State('series-colors', 'data')],
#     prevent_initial_call=True
# )
# def update_series_color(color_clicks, color_ids, active_series, current_colors):
#     """Update color when selecting from color picker."""
#     ctx = dash.callback_context
#     if not ctx.triggered or not active_series or not current_colors:
#         return dash.no_update
    
#     triggered_id = ctx.triggered[0]['prop_id']
#     if 'color-option' not in triggered_id:
#         return dash.no_update
    
#     color_idx = eval(triggered_id.split('.')[0])['index']
#     current_colors[active_series] = COLORS[color_idx]
#     debug_log(f"Updated color for {active_series}")
#     return current_colors

@app.callback(
    Output('scatter-plot', 'figure'),
    [Input('df1-columns', 'value'),
     Input('df2-columns', 'value'),
     Input('plot-settings', 'value'),
     Input('series-colors', 'data')]
)
def update_graph(df1_cols, df2_cols, settings, color_data):
    """Update the scatter plot based on selected columns."""
    debug_log("Updating scatter plot")
    fig = go.Figure()
    
    if not df1_cols or not df2_cols or not color_data:
        fig.add_annotation(
            text="Please select columns from both dataframes",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    for x_col in df1_cols:
        for y_col in df2_cols:
            series_name = f'{x_col} vs {y_col}'
            color = color_data.get(series_name)
            if not color:  # Skip if no color assigned
                continue
                
            # Add scatter plot
            fig.add_trace(go.Scatter(
                x=df1[x_col],
                y=df2[y_col],
                mode='markers',
                name=series_name,
                marker=dict(
                    color=color,
                    size=8,
                    opacity=0.6
                ),
                showlegend=False  # Using custom legend instead
            ))
            
            # Add trend line if requested
            if 'trend' in settings:
                mask = ~(df1[x_col].isna() | df2[y_col].isna())
                x = df1[x_col][mask]
                y = df2[y_col][mask]
                if len(x) > 1:
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    
                    fig.add_trace(go.Scatter(
                        x=[x.min(), x.max()],
                        y=[p(x.min()), p(x.max())],
                        mode='lines',
                        name=f'Trend: {series_name}',
                        line=dict(color=color, dash='dash'),
                        showlegend=False
                    ))
    
    fig.update_layout(
        title='Column Comparisons',
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,  # Using custom legend
        xaxis=dict(
            title='DataFrame 1 Columns',
            showgrid=True,
            gridwidth=1,
            gridcolor='LightGray',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='LightGray'
        ),
        yaxis=dict(
            title='DataFrame 2 Columns',
            showgrid=True,
            gridwidth=1,
            gridcolor='LightGray',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='LightGray'
        ),
        height=700,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    debug_log("Scatter plot updated")
    return fig

""""""

@app.callback(
    Output('series-colors', 'data', allow_duplicate=True),
    [Input({'type': 'color-option', 'index': ALL}, 'n_clicks')],
    [State({'type': 'color-option', 'index': ALL}, 'id'),
     State('active-series', 'data'),
     State('series-colors', 'data')],
    prevent_initial_call=True
)
def update_series_color(color_clicks, color_ids, active_series, current_colors):
    """Update color when selecting from color picker."""
    ctx = dash.callback_context
    if not ctx.triggered or not active_series or not current_colors:
        return dash.no_update
    
    triggered_id = ctx.triggered[0]['prop_id']
    if 'color-option' not in triggered_id:
        return dash.no_update
    
    color_idx = eval(triggered_id.split('.')[0])['index']
    current_colors[active_series] = COLORS[color_idx]
    debug_log(f"Updated color for {active_series} to {COLORS[color_idx]}")
    return current_colors

@app.callback(
    [Output('color-picker-panel', 'style'),
     Output('active-series', 'data')],
    [Input({'type': 'color-button', 'index': ALL}, 'n_clicks'),
     Input('close-color-picker', 'n_clicks'),
     Input({'type': 'color-option', 'index': ALL}, 'n_clicks')],  # Add this input
    [State({'type': 'color-button', 'index': ALL}, 'id'),
     State('color-picker-panel', 'style')]
)
def toggle_color_picker(button_clicks, close_clicks, color_option_clicks, button_ids, current_style):
    """Show/hide color picker when clicking color buttons."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dict(current_style, display='none'), None
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    # Close on color selection or close button click
    if 'color-option' in triggered_id or 'close-color-picker' in triggered_id:
        debug_log("Closing color picker after selection")
        return dict(current_style, display='none'), None
    
    # Open on color button click
    if 'color-button' in triggered_id and any(button_clicks):
        button_idx = next(i for i, c in enumerate(button_clicks) if c)
        series_name = button_ids[button_idx]['index']
        debug_log(f"Opening color picker for {series_name}")
        return dict(current_style, display='block'), series_name
    
    return dict(current_style, display='none'), None

# Update the legend immediately when colors change
@app.callback(
    Output('custom-legend', 'children', allow_duplicate=True),
    [Input('series-colors', 'data')],
    [State('df1-columns', 'value'),
     State('df2-columns', 'value'),
     State('series-data', 'data')],
    prevent_initial_call=True
)
def update_legend_colors(color_data, df1_cols, df2_cols, series_data):
    """Update legend when colors change."""
    if not color_data or not df1_cols or not df2_cols:
        return dash.no_update
    
    debug_log("Updating legend colors")
    legend_items = []
    
    for x_col in df1_cols:
        for y_col in df2_cols:
            series_name = f'{x_col} vs {y_col}'
            color = color_data.get(series_name)
            if not color:
                continue
            
            legend_items.append(html.Div([
                html.Button(
                    style={
                        'backgroundColor': color,
                        'width': '20px',
                        'height': '20px',
                        'marginRight': '10px',
                        'verticalAlign': 'middle',
                        'cursor': 'pointer',
                        'border': '1px solid #ddd'
                    },
                    id={'type': 'color-button', 'index': series_name}
                ),
                html.Span(
                    series_name,
                    style={
                        'cursor': 'default',
                        'userSelect': 'none',
                        'display': 'inline-block'
                    }
                )
            ],
            className='legend-item',
            id={'type': 'legend-item', 'index': series_name},
            **{
                'data-series': series_name,
                'style': {
                    'margin': '10px',
                    'padding': '5px',
                    'borderRadius': '3px',
                }
            }))
    
    return legend_items

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)