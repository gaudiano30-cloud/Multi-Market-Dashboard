from dash import Dash, html, dcc, Input, Output
# dcc = dash core component
import plotly.express as px


app = Dash(__name__)
df = px.data.gapminder()

app.layout = html.Div([
    html.H1("Interactive Dashboard"),
    dcc.Dropdown(
        id="country",
        options=[
            {"label": c, "value": c}
            for c in df["country"].unique()
        ],
        value="Germany"
    ),

    dcc.Graph(id="my-graph")
])



@app.callback(
    Output("my-graph", "figure"),
    Input("country", "value")
)
def update_graph(selected_country):

    filtered_df = df[
        df["country"] == selected_country
    ]

    fig = px.line(
        filtered_df,
        x="year",
        y="gdpPercap",
        title=f"GDP per capita - {selected_country}"
    )

    return fig


if __name__ == "__main__":
    app.run(debug=True)



