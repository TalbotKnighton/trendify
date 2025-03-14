"""Interactive histogram visualization with interactive legend features."""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, MATCH, ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, Any

# Debug Configuration
PYTHON_DEBUG = True
MIN_BINS = 1

def debug_log(message: str) -> None:
    """Python-side debug logging."""
    if PYTHON_DEBUG:
        print(f"[PY] {message}")

def calculate_histogram_statistics(series: pd.Series, num_bins: int = 20) -> Dict[str, Any]:
    """Calculate statistics for a histogram series."""
    try:
        # Drop NA values
        clean_series = series.dropna()
        
        if len(clean_series) < 2:
            return {
                "samples": len(clean_series),
                "missing": len(series) - len(clean_series),
                "mean": "N/A" if len(clean_series) == 0 else f"{clean_series.mean():.3f}",
                "bins": num_bins
            }

        stats_dict = {
            "samples": len(clean_series),
            "missing": len(series) - len(clean_series),
            "mean": f"{clean_series.mean():.3f}",
            "median": f"{clean_series.median():.3f}",
            "std_dev": f"{clean_series.std():.3f}",
            "min": f"{clean_series.min():.3f}",
            "max": f"{clean_series.max():.3f}",
            "bins": num_bins,
            "bin_width": f"{(clean_series.max() - clean_series.min()) / num_bins:.3f}" if clean_series.max() != clean_series.min() else "N/A"
        }
        
        # Add skewness and kurtosis if enough data points
        if len(clean_series) > 3:
            try:
                stats_dict["skewness"] = f"{clean_series.skew():.3f}"
                stats_dict["kurtosis"] = f"{clean_series.kurtosis():.3f}"
            except:
                pass
            
        return stats_dict
    except Exception as e:
        return {"error": str(e), "bins": num_bins}

# Create sample data
df = pd.DataFrame({
    'A': np.random.normal(0, 1, 1000),
    'B': np.random.normal(2, 1.5, 1000),
    'C': np.random.exponential(2, 1000),
    'D': np.random.gamma(2, 2, 1000),
    'Category': np.random.choice(['X', 'Y', 'Z'], 1000)
})

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Styles
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

# Define the layout
app.layout = html.Div([
    html.H1("Interactive Histogram Visualization"),
    
    # Control panel for column selection
    html.Div([
        html.Div([
            html.H3("Select Columns for Histograms"),
            dcc.Dropdown(
                id='histogram-columns',
                options=[{'label': col, 'value': col} for col in df.columns if col != 'Category'],
                value=[],
                multi=True,
                style=dropdown_style
            ),
        ], style={'width': '45%', 'display': 'inline-block', 'margin': '5px'}),
        
    ]),
    
    # Graph and custom legend
    html.Div([
        html.Div([
            html.H3("Histogram Settings"),
            dcc.Checklist(
                id='histogram-settings',
                options=[
                    {'label': ' Show KDE (density curve)', 'value': 'kde'},
                    {'label': ' Normalize histograms', 'value': 'normalize'},
                    {'label': ' Show rug plot', 'value': 'rug'}
                ],
                value=['kde'],
                style={'display': 'block', 'gap': '10px'},
                inputStyle={'marginRight': '5px'},
                labelStyle={'display': 'block', 'marginBottom': '10px'}
            ),
            html.Div([
                html.Label("Global Number of Bins:"),
                dcc.Slider(
                    id='bins-slider',
                    min=MIN_BINS,
                    max=100,
                    step=1,
                    value=20,
                    marks={i: str(i) for i in [1, 20, 40, 60, 80, 100]},
                )
            ], style={'marginTop': '15px'}),
            html.Div([
                html.Label("Lock all bins to global setting:", 
                        style={'display': 'inline-block', 'marginRight': '10px'}),
                dcc.Checklist(
                    id='global-bins-toggle',
                    options=[{'label': '', 'value': 'enabled'}],
                    value=['enabled'],  # Enabled by default
                    inline=True,
                    inputStyle={'marginRight': '5px'}
                )
            ], style={'marginTop': '15px', 'marginBottom': '5px'}),
        ], style={'width': '20%', 'display': 'inline-block', 'margin': '5px'}),
        # Main plot
        html.Div([
            dcc.Graph(
                id='histogram-plot',
                style={'height': '700px'}
            ),
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
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
    dcc.Store(id='active-series'),
    dcc.Store(id='bins-settings'),
    dcc.Store(id='global-bins-active', data=True),  # True by default# Add this to your layout
dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0)  # Just a trigger
])

# Update whether global bins control is active based on toggle
@app.callback(
    Output('global-bins-active', 'data'),
    [Input('global-bins-toggle', 'value')]
)
def update_global_bins_state(toggle_value):
    """Update whether global bins control is active based on toggle."""
    return 'enabled' in toggle_value if toggle_value else False

# # Initialize series-colors and statistics when columns are selected
# @app.callback(
#     [Output('series-colors', 'data'),
#      Output('series-data', 'data')],
#     [Input('histogram-columns', 'value'),
#      Input('bins-settings', 'data')],
#     [State('series-colors', 'data')]
# )
# def initialize_series_data(selected_cols, bins_settings, existing_colors):
#     """Initialize color data and statistics for selected columns."""
#     debug_log("Initializing series data")
#     color_data = existing_colors or {}
#     series_stats = {}
#     bins_settings = bins_settings or {}
    
#     if not selected_cols:
#         return color_data, series_stats
    
#     for col in selected_cols:
#         series_name = f'Histogram of {col}'
        
#         # Assign a color if not already assigned
#         if series_name not in color_data:
#             color_data[series_name] = COLORS[len(color_data) % len(COLORS)]
        
#         # Get bin count (default 20)
#         num_bins = bins_settings.get(series_name, 20)
        
#         # Calculate statistics with the current bin count
#         stats = calculate_histogram_statistics(df[col], num_bins)
#         series_stats[series_name] = stats
    
#     # Keep only the colors for selected columns
#     color_data = {k: v for k, v in color_data.items() 
#                  if any(f'Histogram of {x}' == k for x in selected_cols)}
    
#     return color_data, series_stats


# Update custom legend with bin controls
@app.callback(
    Output('custom-legend', 'children'),
    [Input('histogram-columns', 'value'),
     Input('series-colors', 'data'),
     Input('bins-settings', 'data')]
)
def update_legend_with_bin_controls(selected_cols, color_data, bins_settings):
    """Update custom legend with interactive elements including bin controls."""
    legend_items = []
    bins_settings = bins_settings or {}
    
    if not selected_cols or not color_data:
        return legend_items
    
    for col in selected_cols:
        series_name = f'Histogram of {col}'
        color = color_data.get(series_name, COLORS[0])
        
        # Get bin count for this series (default: 20 bins)
        bin_count = bins_settings.get(series_name, 20)
        
        legend_items.append(html.Div([
            # Color button
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
            # Series name
            html.Span(
                series_name,
                style={
                    'cursor': 'default',
                    'userSelect': 'none',
                    'display': 'inline-block',
                    'marginRight': '10px'
                }
            ),
            # Bin control
            html.Div([
                html.Label("Bins:", style={'fontSize': '11px', 'marginRight': '5px'}),
                dcc.Input(
                    id={'type': 'bin-input', 'index': series_name},
                    type="number",
                    min=5,
                    max=100,
                    step=1,
                    value=bin_count,
                    style={'width': '50px', 'fontSize': '11px'},
                    debounce=False,  # Process changes immediately
                    persistence=True  # Remember values
                )
            ], style={'display': 'inline-block'})
        ],
        className='legend-item',
        id={'type': 'legend-item', 'index': series_name},
        **{
            'data-series': series_name,
            'style': {
                'margin': '10px',
                'padding': '5px',
                'borderRadius': '3px',
                'display': 'flex',
                'alignItems': 'center'
            }
        }))
    
    return legend_items

@app.callback(
    [Output('color-picker-panel', 'style'),
     Output('active-series', 'data')],
    [Input({'type': 'color-button', 'index': ALL}, 'n_clicks'),
     Input('close-color-picker', 'n_clicks')],
    [State({'type': 'color-button', 'index': ALL}, 'id'),
     State('color-picker-panel', 'style')]
)
def toggle_color_picker(button_clicks, close_clicks, button_ids, current_style):
    """Show/hide color picker when clicking color buttons."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dict(current_style, display='none'), None
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    # Close on close button click
    if 'close-color-picker' in triggered_id:
        debug_log("Closing color picker")
        return dict(current_style, display='none'), None
    
    # Open on color button click
    if 'color-button' in triggered_id and button_clicks and any(button_clicks):
        try:
            # Find which button was clicked
            button_idx = next((i for i, clicks in enumerate(button_clicks) if clicks), None)
            if button_idx is not None:
                series_name = button_ids[button_idx]['index']
                debug_log(f"Opening color picker for {series_name}")
                return dict(current_style, display='block'), series_name
        except Exception as e:
            debug_log(f"Error in toggle_color_picker: {e}")
    
    return dict(current_style, display='none'), None

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
    if 'color-option' not in triggered_id or not any(click for click in color_clicks if click):
        return dash.no_update
    
    try:
        # Find which color was clicked
        color_idx = next((i for i, clicks in enumerate(color_clicks) if clicks), None)
        if color_idx is not None:
            current_colors[active_series] = COLORS[color_idx]
            debug_log(f"Updated color for {active_series} to {COLORS[color_idx]}")
            return current_colors
    except Exception as e:
        debug_log(f"Error in update_series_color: {e}")
    
    return dash.no_update

@app.callback(
    [Output('color-picker-panel', 'style', allow_duplicate=True),
     Output('active-series', 'data', allow_duplicate=True)],
    [Input({'type': 'color-option', 'index': ALL}, 'n_clicks')],
    [State('color-picker-panel', 'style')],
    prevent_initial_call=True
)
def close_color_picker_after_selection(color_clicks, current_style):
    """Close the color picker after a color is selected."""
    if any(click for click in color_clicks if click):
        return dict(current_style, display='none'), None
    return dash.no_update, dash.no_update

@app.callback(
    Output('histogram-plot', 'figure'),
    [Input('histogram-columns', 'value'),
     Input('histogram-settings', 'value'),
     Input('series-colors', 'data'),
     Input('bins-settings', 'data')]
)
def update_histogram(selected_cols, settings, color_data, bins_settings):
    """Update the histogram based on selected columns and settings."""
    debug_log("Updating histogram plot")
    fig = go.Figure()
    
    if not selected_cols or not color_data:
        fig.add_annotation(
            text="Please select columns for the histogram",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    normalize = 'normalize' in settings
    show_kde = 'kde' in settings
    show_rug = 'rug' in settings
    bins_settings = bins_settings or {}
    
    for col in selected_cols:
        series_name = f'Histogram of {col}'
        color = color_data.get(series_name)
        if not color:  # Skip if no color assigned
            continue
        
        # Get bins setting for this series (default: 20)
        num_bins = bins_settings.get(series_name, 20)
        
        # Clean the data
        data = df[col].dropna()
        
        # Add histogram with precisely num_bins bins
        histnorm = 'probability' if normalize else None
        
        # Calculate bin range directly
        min_val, max_val = min(data), max(data)
        bin_width = (max_val - min_val) / num_bins if max_val > min_val else 1
        
        # Use xbins to control exactly how many bins are displayed
        fig.add_trace(go.Histogram(
            x=data,
            name=series_name,
            histnorm=histnorm,
            marker_color=color,
            opacity=0.7,
            showlegend=False,
            xbins=dict(
                start=min_val,
                end=max_val,
                size=bin_width
            ),
            autobinx=False  # Disable autobinning
        ))
        
        # Add KDE if requested
        if show_kde and len(data) > 1:
            try:
                # Calculate KDE values
                from scipy import stats as scipy_stats
                
                # Make sure we have enough unique values for KDE
                if len(np.unique(data)) > 5:
                    kde = scipy_stats.gaussian_kde(data)
                    x_range = np.linspace(min(data), max(data), 200)
                    y_range = kde(x_range)
                    
                    # Scale KDE to match histogram height
                    if normalize:
                        # Scale for normalized histogram
                        y_range = y_range / np.trapz(y_range, x_range) 
                    else:
                        # Scale for count histogram
                        hist, edges = np.histogram(data, bins=num_bins)
                        max_hist_height = np.max(hist)
                        max_kde_height = np.max(y_range)
                        scale_factor = max_hist_height / max_kde_height if max_kde_height > 0 else 1
                        y_range = y_range * scale_factor
                    
                    fig.add_trace(go.Scatter(
                        x=x_range,
                        y=y_range,
                        mode='lines',
                        name=f'KDE of {col}',
                        line=dict(color=color, width=2),
                        showlegend=False
                    ))
            except Exception as e:
                debug_log(f"Error computing KDE: {e}")
        
        # Add rug plot if requested
        if show_rug:
            try:
                # Create a small y value for the rug
                min_y = 0
                if normalize:
                    # Position below x-axis for normalized histogram
                    min_y = -0.02
                
                fig.add_trace(go.Scatter(
                    x=data,
                    y=[min_y] * len(data),
                    mode='markers',
                    marker=dict(
                        symbol='line-ns',
                        size=10,
                        color=color,
                        opacity=0.5
                    ),
                    showlegend=False,
                    hoverinfo='x'
                ))
            except Exception as e:
                debug_log(f"Error adding rug plot: {e}")
    
    # Display histograms using overlay mode
    fig.update_layout(
        barmode='overlay',
        title='Interactive Histogram Visualization',
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,  # Using custom legend
        xaxis=dict(
            title='Value',
            showgrid=True,
            gridwidth=1,
            gridcolor='LightGray',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='LightGray'
        ),
        yaxis=dict(
            title='Frequency' if not normalize else 'Probability',
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
    
    debug_log("Histogram plot updated")
    return fig

app.clientside_callback(
    """
    function(children, series_data) {
        if (!children) return window.dash_clientside.no_update;
        
        const JS_DEBUG = true;
        
        function debugLog(message) {
            if (JS_DEBUG) console.log('[JS]', message);
        }
        
        // Global reference to track which element is being hovered
        window.activeHoverLegendItem = window.activeHoverLegendItem || null;
        
        function updateStatsPanel() {
            // If no item is active, don't update
            if (!window.activeHoverLegendItem) return;
            
            const panel = document.getElementById('series-info-panel');
            if (!panel) return;
            
            const series = window.activeHoverLegendItem.getAttribute('data-series');
            
            // If panel is visible, update its content
            if (panel.style.display === 'block' && series_data && series_data[series]) {
                let statsHtml = "<div style='padding:10px;'>";
                statsHtml += `<h4 style='margin-top:0;'>Statistics: ${series}</h4>`;
                statsHtml += "<table style='border-collapse:collapse;'>";
                
                const stats = series_data[series];
                for (const [key, value] of Object.entries(stats)) {
                    statsHtml += `<tr>
                        <td style='padding:3px; font-weight:bold;'>${key}</td>
                        <td style='padding:3px;'>${value}</td>
                    </tr>`;
                }
                
                statsHtml += "</table></div>";
                panel.innerHTML = statsHtml;
            }
        }
        
        function setupHoverHandlers() {
            debugLog('Setting up hover handlers');
            const items = document.getElementsByClassName('legend-item');
            const panel = document.getElementById('series-info-panel');
            
            Array.from(items).forEach(item => {
                item.onmouseenter = (e) => {
                    const series = item.getAttribute('data-series');
                    debugLog(`Hover enter: ${series}`);
                    
                    // Store reference to the hovered item
                    window.activeHoverLegendItem = item;
                    
                    // Generate HTML content for statistics
                    let statsHtml = "<div style='padding:10px;'>";
                    
                    if (series_data && series_data[series]) {
                        statsHtml += `<h4 style='margin-top:0;'>Statistics: ${series}</h4>`;
                        statsHtml += "<table style='border-collapse:collapse;'>";
                        
                        const stats = series_data[series];
                        for (const [key, value] of Object.entries(stats)) {
                            statsHtml += `<tr>
                                <td style='padding:3px; font-weight:bold;'>${key}</td>
                                <td style='padding:3px;'>${value}</td>
                            </tr>`;
                        }
                        
                        statsHtml += "</table>";
                    } else {
                        statsHtml += "<p>No statistics available for this series.</p>";
                    }
                    
                    statsHtml += "</div>";
                    panel.innerHTML = statsHtml;
                    
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
                    window.activeHoverLegendItem = null;
                    panel.style.display = 'none';
                };
            });
        }
        
        // Update panel content if needed
        updateStatsPanel();
        
        // Allow time for DOM to update
        setTimeout(setupHoverHandlers, 100);
        
        return window.dash_clientside.no_update;
    }
    """,
    Output('custom-legend', 'data-update'),
    [Input('custom-legend', 'children'),
     Input('series-data', 'data')]
)
# # Remove the existing update_bin_settings callback and replace with this:
# @app.callback(
#     Output('series-data', 'data'),
#     [Input('bins-settings', 'data'),
#      Input('histogram-columns', 'value')],
#     [State('series-data', 'data')]
# )
# def update_statistics_on_bin_change(bins_settings, selected_cols, current_stats):
#     """Update statistics whenever bin settings change."""
#     ctx = dash.callback_context
#     if not ctx.triggered:
#         return current_stats or {}
    
#     if not selected_cols:
#         return current_stats or {}
    
#     bins_settings = bins_settings or {}
#     stats = current_stats or {}
    
#     # Update statistics for all selected columns with current bin settings
#     for col in selected_cols:
#         series_name = f'Histogram of {col}'
#         num_bins = bins_settings.get(series_name, 20)  # Default to 20 bins
#         updated_stats = calculate_histogram_statistics(df[col], num_bins)
#         stats[series_name] = updated_stats
    
#     # Remove stats for unselected columns
#     for series_name in list(stats.keys()):
#         if not any(f'Histogram of {col}' == series_name for col in selected_cols):
#             del stats[series_name]
    
#     return stats
# Replace the existing initialize_series_data callback with this one:

@app.callback(
    [Output('series-colors', 'data'),
     Output('series-data', 'data')],
    [Input('histogram-columns', 'value'),
     Input('bins-settings', 'data')],
    [State('series-colors', 'data')]
)
def initialize_and_update_series_data(selected_cols, bins_settings, existing_colors):
    """Initialize color data and update statistics for selected columns."""
    ctx = dash.callback_context
    debug_log(f"Series data update triggered by: {ctx.triggered[0]['prop_id'] if ctx.triggered else 'none'}")
    
    color_data = existing_colors or {}
    series_stats = {}
    bins_settings = bins_settings or {}
    
    if not selected_cols:
        return color_data, series_stats
    
    for col in selected_cols:
        series_name = f'Histogram of {col}'
        
        # Assign a color if not already assigned
        if series_name not in color_data:
            color_data[series_name] = COLORS[len(color_data) % len(COLORS)]
        
        # Get bin count (default 20)
        num_bins = bins_settings.get(series_name, 20)
        
        # Calculate statistics with the current bin count
        stats = calculate_histogram_statistics(df[col], num_bins)
        series_stats[series_name] = stats
    
    # Keep only the colors for selected columns
    color_data = {k: v for k, v in color_data.items() 
                 if any(f'Histogram of {x}' == k for x in selected_cols)}
    
    return color_data, series_stats
@app.callback(
    Output('bins-settings', 'data'),
    [Input({'type': 'bin-input', 'index': ALL}, 'value'),
     Input('bins-slider', 'value'),
     Input('histogram-columns', 'value')],
    [State({'type': 'bin-input', 'index': ALL}, 'id'),
     State('bins-settings', 'data'),
     State('global-bins-active', 'data')]
)
def update_all_bin_settings(bin_values, slider_value, selected_cols, bin_ids, current_settings, global_active):
    """Master callback that handles ALL bin settings updates."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_settings or {}
        
    settings = current_settings or {}
    triggered_id = ctx.triggered[0]['prop_id']
    
    debug_log(f"Bin settings update triggered by: {triggered_id}")
    
    # When columns change, initialize bin settings for new columns
    if 'histogram-columns.value' in triggered_id:
        if selected_cols:
            for col in selected_cols:
                series_name = f'Histogram of {col}'
                # Only set if not already set
                if series_name not in settings:
                    settings[series_name] = slider_value
        
        # Clean up any series that are no longer selected
        to_remove = []
        for series_name in settings:
            if not any(f'Histogram of {col}' == series_name for col in selected_cols):
                to_remove.append(series_name)
        
        for series_name in to_remove:
            del settings[series_name]
    
    # Handle global slider update
    elif 'bins-slider.value' in triggered_id and global_active:
        if selected_cols:
            for col in selected_cols:
                series_name = f'Histogram of {col}'
                settings[series_name] = slider_value
            debug_log(f"Updated all bins to {slider_value} from global slider")
    
    # Handle individual bin input updates
    elif 'bin-input' in triggered_id:
        for i, value in enumerate(bin_values):
            if value is not None:
                try:
                    # Handle both numeric and string inputs
                    if isinstance(value, str):
                        if value.strip():  # Non-empty string
                            num_value = int(float(value))
                        else:
                            continue
                    else:
                        num_value = int(value)
                        
                    if num_value >= MIN_BINS:
                        series_name = bin_ids[i]['index']
                        settings[series_name] = num_value
                        debug_log(f"Updated bin for {series_name} to {num_value}")
                    
                except (ValueError, TypeError) as e:
                    debug_log(f"Error converting bin value: {e}")
                    pass
    
    return settings
# Add this clientside callback to handle both typing and arrow clicks
app.clientside_callback(
    """
    function(bins_settings) {
        // This function just initializes our input handlers once
        if (!window.binsInputsInitialized) {
            // Wait for DOM to be ready
            setTimeout(() => {
                // Find all bin inputs
                const binInputs = document.querySelectorAll('input[id*="bin-input"]');
                
                // Add event listeners to each input
                binInputs.forEach(input => {
                    // Extract the series name from the id attribute
                    const idMatch = input.id.match(/"index":"([^"]+)"/);
                    if (!idMatch) return;
                    
                    const seriesName = idMatch[1];
                    
                    // Handle input events (works for both typing and arrows)
                    input.addEventListener('input', function(e) {
                        const value = parseInt(this.value);
                        if (!isNaN(value) && value >= 5) {
                            // Directly update the bins-settings store
                            const existingSettings = JSON.parse(
                                document.getElementById('bins-settings').getAttribute('data-dash-store') || '{}'
                            );
                            
                            existingSettings[seriesName] = value;
                            
                            // This will trigger the Dash callback
                            document.getElementById('bins-settings')
                                .setAttribute('data-dash-store', JSON.stringify(existingSettings));
                                
                            // Create and dispatch a custom event to notify Dash
                            const event = new CustomEvent('bins-settings-updated');
                            document.dispatchEvent(event);
                        }
                    });
                });
                
                window.binsInputsInitialized = true;
            }, 500); // Wait for components to render
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output('custom-legend', 'data-update', allow_duplicate=True),
    [Input('bins-settings', 'data')],
    prevent_initial_call=True
)
# Add this to monitor and update from the clientside
app.clientside_callback(
    """
    function(n_intervals) {
        const customEvent = new CustomEvent('_dash-update-component', {
            detail: {
                output: 'bins-settings.data',
                changedPropIds: ['custom-event.n_events']
            }
        });
        
        document.addEventListener('bins-settings-updated', function() {
            // Get current settings from the store
            const storeEl = document.getElementById('bins-settings');
            const data = JSON.parse(storeEl.getAttribute('data-dash-store') || '{}');
            
            // Trigger update in Dash
            window.dash_clientside._callback.setProps({
                'bins-settings.data': data
            });
        });
        
        return window.dash_clientside.no_update;
    }
    """,
    Output('custom-legend', 'data-update', allow_duplicate=True),
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=True
)
# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, port=8051)