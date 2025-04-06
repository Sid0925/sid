import dash
from dash import html
import os

# Create Dash app
app = dash.Dash(__name__)
server = app.server  # Needed for Render deployment

app.layout = html.Div([
    html.H1("Hello from Render! 🌐"),
    html.P("Your Dash app is now LIVE.")
])

if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
