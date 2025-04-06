import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
import oandapyV20
from oandapyV20.endpoints.instruments import InstrumentsCandles
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ACCESS_TOKEN = os.getenv("OANDA_API_KEY")
client = oandapyV20.API(access_token=ACCESS_TOKEN)

# === CONFIG ===
DEFAULT_INSTRUMENT = "UK100_GBP"
DEFAULT_GRANULARITY = "M1"
COUNT = 5000

# === OU SIGNAL ===
def add_ou_signals(df: pd.DataFrame, z_thresh: float = 1.2, cooldown: int = 15) -> pd.DataFrame:
    df = df.copy()
    df['log_close'] = np.log(df['close'])
    df['log_close_shifted'] = df['log_close'].shift(1)

    ou_df = df.dropna(subset=['log_close', 'log_close_shifted']).copy()
    X = ou_df['log_close_shifted'].values.reshape(-1, 1)
    y = ou_df['log_close'].values
    lr = LinearRegression().fit(X, y)
    beta = lr.coef_[0]
    alpha = lr.intercept_
    ou_df['residual'] = ou_df['log_close'] - (alpha + beta * ou_df['log_close_shifted'])
    ou_df['z_score'] = (ou_df['residual'] - ou_df['residual'].mean()) / ou_df['residual'].std()

    df['z_score'] = ou_df['z_score']
    df['momentum'] = df['close'] - df['close'].shift(3)

    signal_list = []
    last_signal_idx = -cooldown

    for i, row in df.iterrows():
        if pd.isna(row['z_score']) or pd.isna(row['momentum']):
            signal = 'hold'
        elif (row['z_score'] < -1.2 and row['momentum'] > 0 and (i - last_signal_idx) > cooldown):
            signal = 'buy'
            last_signal_idx = i
        elif (row['z_score'] > 1.2 and row['momentum'] < 0 and (i - last_signal_idx) > cooldown):
            signal = 'sell'
            last_signal_idx = i
        else:
            signal = 'hold'
        signal_list.append(signal)

    df['signal'] = signal_list
    return df

# === FETCH DATA ===
def get_latest_data(instrument, granularity):
    r = InstrumentsCandles(instrument=instrument, params={"granularity": granularity, "count": COUNT})
    response = client.request(r)
    candles = response['candles']
    df = pd.DataFrame({
        "time": [c["time"] for c in candles],
        "complete": [c["complete"] for c in candles],
        "volume": [c["volume"] for c in candles],
        "open": [float(c["mid"]["o"]) for c in candles],
        "high": [float(c["mid"]["h"]) for c in candles],
        "low": [float(c["mid"]["l"]) for c in candles],
        "close": [float(c["mid"]["c"]) for c in candles]
    })

    df['time'] = pd.to_datetime(df['time'])
    df = df[df['complete'] == True]
    df['volume_color'] = df.apply(lambda row: 'green' if row['close'] >= row['open'] else 'red', axis=1)
    df['sma'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma'] + 2 * df['std']
    df['lower_band'] = df['sma'] - 2 * df['std']

    # Support/Resistance
    lookback = 300
    df['support'] = np.nan
    df['resistance'] = np.nan
    support_idx = argrelextrema(df['close'].values, np.less_equal, order=lookback)[0]
    resistance_idx = argrelextrema(df['close'].values, np.greater_equal, order=lookback)[0]
    df.loc[df.iloc[support_idx].index, 'support'] = df['close'].iloc[support_idx]
    df.loc[df.iloc[resistance_idx].index, 'resistance'] = df['close'].iloc[resistance_idx]

    df = add_ou_signals(df)
    return df

# === PLOT ===
def create_figure(df, indicators, theme, instrument):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name='Candles'
    ))

    if 'signals' in indicators:
        for label, color, symbol in [('buy', 'green', 'triangle-up'), ('sell', 'red', 'triangle-down')]:
            sigs = df[df['signal'] == label]
            fig.add_trace(go.Scatter(
                x=sigs['time'], y=sigs['close'], mode='markers',
                marker=dict(color=color, size=10, symbol=symbol),
                name=f'{label.title()} Signal'
            ))

    if 'bollinger' in indicators:
        fig.add_trace(go.Scatter(x=df['time'], y=df['upper_band'], mode='lines', name='Upper Band'))
        fig.add_trace(go.Scatter(x=df['time'], y=df['sma'], mode='lines', name='SMA'))
        fig.add_trace(go.Scatter(x=df['time'], y=df['lower_band'], mode='lines', name='Lower Band'))

    if 's_r' in indicators:
        fig.add_trace(go.Scatter(
            x=df[df['support'].notna()]['time'], y=df[df['support'].notna()]['support'],
            mode='markers', marker=dict(color='blue', symbol='x'), name='Support'
        ))
        fig.add_trace(go.Scatter(
            x=df[df['resistance'].notna()]['time'], y=df[df['resistance'].notna()]['resistance'],
            mode='markers', marker=dict(color='orange', symbol='x'), name='Resistance'
        ))

    fig.update_layout(
        title=f'Live OU Chart - {instrument}',
        xaxis_rangeslider_visible=False,
        template=theme,
        height=800,
        uirevision='constant'
    )
    return fig

# === DASH APP ===
app = dash.Dash(__name__)
server = app.server  # For Render deployment

app.layout = html.Div([
    html.H1("📈 OU Mean Reversion Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.Label("Instrument"),
            dcc.Dropdown(
                id='instrument-dropdown',
                options=[{'label': i, 'value': i} for i in [
                    'UK100_GBP', 'DE30_EUR', 'SPX500_USD', 'NAS100_USD',
                    'EUR_USD', 'USD_JPY', 'GBP_USD', 'XAU_USD'
                ]],
                value=DEFAULT_INSTRUMENT,
                style={'width': '180px'}
            )
        ], style={'display': 'inline-block', 'marginRight': '20px'}),

        html.Div([
            html.Label("Granularity"),
            dcc.Dropdown(
                id='granularity-dropdown',
                options=[{'label': l, 'value': v} for l, v in [
                    ('5 sec', 'S5'), ('10 sec', 'S10'), ('15 sec', 'S15'),
                    ('30 sec', 'S30'), ('1 min', 'M1'), ('2 min', 'M2'),
                    ('4 min', 'M4'), ('5 min', 'M5'), ('10 min', 'M10'),
                    ('15 min', 'M15'), ('30 min', 'M30'), ('1 hour', 'H1'),
                    ('2 hours', 'H2'), ('4 hours', 'H4'), ('1 day', 'D'),
                    ('1 week', 'W'), ('1 month', 'M')
                ]],
                value=DEFAULT_GRANULARITY,
                style={'width': '150px'}
            )
        ], style={'display': 'inline-block', 'marginRight': '20px'}),

        html.Div([
            html.Label("Theme"),
            dcc.Dropdown(
                id='theme-toggle',
                options=[
                    {'label': 'Dark', 'value': 'plotly_dark'},
                    {'label': 'Light', 'value': 'plotly_white'}
                ],
                value='plotly_dark',
                style={'width': '140px'}
            )
        ], style={'display': 'inline-block', 'marginRight': '20px'}),

        html.Div([
            html.Label("Indicators"),
            dcc.Checklist(
                id='indicator-toggle',
                options=[
                    {'label': 'Bollinger Bands', 'value': 'bollinger'},
                    {'label': 'OU Buy/Sell Signals', 'value': 'signals'},
                    {'label': 'Support/Resistance', 'value': 's_r'}
                ],
                value=['bollinger', 'signals', 's_r'],
                labelStyle={'display': 'block'}
            )
        ], style={'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'marginBottom': '20px', 'paddingLeft': '20px'}),

    dcc.Graph(id='live-candle-chart', style={'height': '85vh'}),

    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0)
])

@app.callback(
    Output('live-candle-chart', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('indicator-toggle', 'value'),
     Input('granularity-dropdown', 'value'),
     Input('theme-toggle', 'value'),
     Input('instrument-dropdown', 'value')]
)
def update_chart(n, indicators, granularity, theme, instrument):
    df = get_latest_data(instrument, granularity)
    return create_figure(df, indicators, theme, instrument)

# === RUN ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
