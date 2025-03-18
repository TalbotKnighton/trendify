"""
Code snippet showing improved tag selection for PlotlyDashboardGenerator
to replace the existing tab-based navigation
"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# This would replace the _create_app_layout method in your class
def _create_app_layout_with_dropdown(self, title: str, tab_contents: List[Dict]) -> html.Div:
    """Create the main application layout with dropdown selection instead of tabs."""
    if not tab_contents:
        return html.Div([
            html.H1(title),
            html.Div("No data products found to visualize.")
        ])
    
    # Create dropdown options from tab_contents
    dropdown_options = [
        {'label': tab['label'], 'value': tab['value']} 
        for tab in tab_contents
    ]
    
    # Create divs for each tag's content
    content_divs = []
    for tab in tab_contents:
        content_divs.append(
            html.Div(
                tab['content'],
                id=f"content-{tab['value']}",
                style={'display': 'none'}
            )
        )
    
    return html.Div([
        html.H1(title),
        html.Div([
            html.Label("Select Tag:"),
            dcc.Dropdown(
                id='tag-selector',
                options=dropdown_options,
                value=tab_contents[0]['value'],
                clearable=False,
                style={'width': '100%'}
            ),
        ], style={'width': '30%', 'margin': '10px 0'}),
        html.Div(id='tag-content-container', children=content_divs),
        
        # Stores
        dcc.Store(id='active-tag', data=tab_contents[0]['value']),
    ])

# This would replace the callback in _register_callbacks
def tag_selection_callback(self):
    """Register callback for tag selection dropdown."""
    @self.app.callback(
        [Output('active-tag', 'data')] + 
        [Output(f'content-{tag}', 'style') for tag in self.tag_data.keys()],
        [Input('tag-selector', 'value')]
    )
    def switch_tag(tag_value):
        styles = []
        for tag in self.tag_data.keys():
            if tag == tag_value:
                styles.append({'display': 'block'})
            else:
                styles.append({'display': 'none'})
        return [tag_value] + styles