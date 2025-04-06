import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

# Sample data
df = pd.DataFrame({
    "Category": ["A", "B", "C", "D"],
    "Values": [30, 80, 45, 60]
})

# Create a bar chart
fig = px.bar(df, x="Category", y="Values", title="Sample Bar Chart")

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # Expose the server for deployment platforms like Render

# App layout
app.layout = html.Div(children=[
    html.H1(children='Hello Dash!', style={'textAlign': 'center'}),

    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])

# Run the server (only locally)
if __name__ == "__main__":
    app.run(debug=True)
