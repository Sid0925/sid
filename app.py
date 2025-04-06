import dash
from dash import html
import os

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Hello from Railway 🚂"),
    html.P("Your Dash app is now live!")
])

server = app.server  # Needed for Railway/Heroku-style deployment

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8050)))
