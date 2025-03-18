"""
Additional selection mechanisms for handling large numbers of tags in Trendify dashboards.
These components can be integrated into the PlotlyDashboardGenerator class.
"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import re

class TagSelectionMethods:
    """Various tag selection UI components for Plotly Dash"""
    
    @staticmethod
    def create_searchable_dropdown(tag_options, default_value):
        """
        Create a searchable dropdown for tag selection
        
        Args:
            tag_options (list): List of tag options in {'label': '...', 'value': '...'} format
            default_value (str): Default tag value to select
            
        Returns:
            html.Div: Dropdown component with search functionality
        """
        return html.Div([
            html.Label("Search and select tag:"),
            dcc.Dropdown(
                id='tag-selector',
                options=tag_options,
                value=default_value,
                clearable=False,
                searchable=True,
                style={'width': '100%'}
            )
        ], style={'width': '40%', 'margin': '10px 0'})
    
    @staticmethod
    def create_radio_with_search_filter(tag_options, default_value):
        """
        Create radio buttons with a search filter above
        
        Args:
            tag_options (list): List of tag options in {'label': '...', 'value': '...'} format
            default_value (str): Default tag value to select
            
        Returns:
            html.Div: Search filter and radio button component
        """
        return html.Div([
            html.Label("Filter tags:"),
            dcc.Input(
                id='tag-search-input',
                type='text',
                placeholder='Type to filter tags...',
                style={'width': '100%', 'marginBottom': '10px'}
            ),
            html.Div([
                dcc.RadioItems(
                    id='tag-selector',
                    options=tag_options,
                    value=default_value,
                    labelStyle={'display': 'block', 'margin': '5px 0'}
                )
            ], id='filtered-radio-container', style={'maxHeight': '300px', 'overflowY': 'auto'})
        ], style={'width': '30%', 'margin': '10px 0'})
    
    @staticmethod
    def create_category_based_selection(tag_options, default_value):
        """
        Create a two-level selection for tags that can be organized by category
        Assumes tag names might follow a pattern like 'category/tag_name'
        
        Args:
            tag_options (list): List of tag options in {'label': '...', 'value': '...'} format
            default_value (str): Default tag value to select
            
        Returns:
            html.Div: Two-level selection component
        """
        # Try to extract categories from tag names (e.g., 'category/tag_name')
        categories = set()
        for opt in tag_options:
            parts = opt['label'].split('/')
            if len(parts) > 1:
                categories.add(parts[0])
            else:
                categories.add('General')
        
        categories = sorted(list(categories))
        
        # Default category
        default_category = next((parts[0] for opt in tag_options 
                               if opt['value'] == default_value 
                               and len(parts := opt['label'].split('/')) > 1), 
                              'General')
        
        return html.Div([
            html.Div([
                html.Label("Category:"),
                dcc.Dropdown(
                    id='category-selector',
                    options=[{'label': cat, 'value': cat} for cat in categories],
                    value=default_category,
                    clearable=False,
                    style={'width': '100%'}
                )
            ], style={'marginBottom': '10px'}),
            html.Div([
                html.Label("Tag:"),
                dcc.Dropdown(
                    id='tag-selector',
                    # Options will be populated by callback
                    value=default_value,
                    clearable=False,
                    style={'width': '100%'}
                )
            ])
        ], style={'width': '40%', 'margin': '10px 0'})

    @staticmethod
    def register_category_callbacks(app, tag_options):
        """Register callbacks for the category-based selection"""
        @app.callback(
            Output('tag-selector', 'options'),
            [Input('category-selector', 'value')]
        )
        def update_tag_options(selected_category):
            filtered_options = []
            for opt in tag_options:
                parts = opt['label'].split('/')
                if len(parts) > 1 and parts[0] == selected_category:
                    # Show only the tag part in the dropdown
                    filtered_options.append({
                        'label': parts[1], 
                        'value': opt['value']
                    })
                elif len(parts) == 1 and selected_category == 'General':
                    filtered_options.append(opt)
            return filtered_options
    
    @staticmethod
    def register_search_filter_callbacks(app, tag_options):
        """Register callbacks for the search filter with radio buttons"""
        @app.callback(
            Output('filtered-radio-container', 'children'),
            [Input('tag-search-input', 'value')],
            [State('tag-selector', 'value')]
        )
        def filter_radio_options(search_text, current_value):
            if not search_text:
                return dcc.RadioItems(
                    id='tag-selector',
                    options=tag_options,
                    value=current_value,
                    labelStyle={'display': 'block', 'margin': '5px 0'}
                )
            
            # Filter options based on search text
            filtered_options = [
                opt for opt in tag_options
                if search_text.lower() in opt['label'].lower()
            ]
            
            return dcc.RadioItems(
                id='tag-selector',
                options=filtered_options,
                value=current_value if any(opt['value'] == current_value for opt in filtered_options) else None,
                labelStyle={'display': 'block', 'margin': '5px 0'}
            )


# Example of how to use these components in the PlotlyDashboardGenerator class
def create_sidebar_with_tag_tree(tag_options, default_value):
    """Create a sidebar with a hierarchical tag tree for larger applications"""
    
    # Organize tags into a tree structure
    tag_tree = {}
    for opt in tag_options:
        parts = opt['label'].split('/')
        if len(parts) == 1:
            category = 'General'
            tag = parts[0]
        else:
            category = parts[0]
            tag = '/'.join(parts[1:])  # Join remaining parts as the tag
        
        if category not in tag_tree:
            tag_tree[category] = []
        
        tag_tree[category].append({
            'label': tag,
            'value': opt['value']
        })
    
    # Sort categories and tags
    categories = sorted(tag_tree.keys())
    
    # Create the sidebar
    return html.Div([
        html.H3("Tags"),
        html.Hr(),
        html.Div([
            html.Div([
                html.Details([
                    html.Summary(category),
                    html.Div([
                        html.Div([
                            dcc.RadioItems(
                                id={'type': 'tag-radio', 'category': category},
                                options=tag_tree[category],
                                value=None,
                                labelStyle={'display': 'block', 'margin': '5px 0', 'paddingLeft': '20px'}
                            )
                        ])
                    ])
                ], open=category == next((parts[0] for opt in tag_options 
                                        if opt['value'] == default_value 
                                        and len(parts := opt['label'].split('/')) > 1), 
                                       'General'))
            ]) for category in categories
        ]),
        # Hidden input to store the selected tag
        dcc.Input(id='tag-selector', value=default_value, type='hidden')
    ], style={'width': '250px', 'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRight': '1px solid #ddd',
              'height': '100vh', 'position': 'fixed', 'overflowY': 'auto'})

def register_tag_tree_callbacks(app, tag_options):
    """Register callbacks for the sidebar tag tree"""
    
    # Create a list of Output objects, one for each category
    categories = set()
    for opt in tag_options:
        parts = opt['label'].split('/')
        if len(parts) > 1:
            categories.add(parts[0])
        else:
            categories.add('General')
    
    categories = sorted(list(categories))
    
    @app.callback(
        Output('tag-selector', 'value'),
        [Input({'type': 'tag-radio', 'category': cat}, 'value') for cat in categories]
    )
    def update_selected_tag(*values):
        # Find the first non-None value (the selected tag)
        for val in values:
            if val is not None:
                return val
        
        # Default to the first tag if nothing is selected
        return tag_options[0]['value'] if tag_options else None