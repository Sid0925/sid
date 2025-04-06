<<<<<<< HEAD
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
=======
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
>>>>>>> b19bf6c6b7849bf92d2f04cd2fe77fec47f8b9bc
