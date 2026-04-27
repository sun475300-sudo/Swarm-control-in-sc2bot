# Phase 419: FastHTML - SC2 Dashboard
# FastHTML (Python web framework) SC2 bot management dashboard with HTMX

from fasthtml.common import (
    FastHTML,
    serve,
    Html,
    Head,
    Body,
    Title,
    Meta,
    Link,
    Script,
    Div,
    H1,
    H2,
    H3,
    P,
    Span,
    Strong,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Nav,
    A,
    Button,
    Form,
    Input,
    Select,
    Option,
    Card,
    Main,
    Header,
    Footer,
    Ul,
    Li,
    fast_app,
)
from datetime import datetime
import json

# ============================================================
# App Setup
# ============================================================

app, rt = fast_app(
    hdrs=(
        Link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
        ),
        Script(src="https://cdn.jsdelivr.net/npm/chart.js"),
    )
)

# ============================================================
# Mock Data
# ============================================================

GAME_HISTORY = [
    {
        "id": 1,
        "map": "Equilibrium LE",
        "result": "Win",
        "race": "ZvT",
        "duration": "7:03",
        "mmr": +18,
        "apm": 184,
    },
    {
        "id": 2,
        "map": "Site Delta LE",
        "result": "Loss",
        "race": "ZvP",
        "duration": "10:12",
        "mmr": -15,
        "apm": 201,
    },
    {
        "id": 3,
        "map": "Gresvan LE",
        "result": "Win",
        "race": "ZvZ",
        "duration": "4:47",
        "mmr": +21,
        "apm": 167,
    },
    {
        "id": 4,
        "map": "Goldenaura LE",
        "result": "Win",
        "race": "ZvT",
        "duration": "9:30",
        "mmr": +20,
        "apm": 195,
    },
    {
        "id": 5,
        "map": "Crimson Court LE",
        "result": "Loss",
        "race": "ZvP",
        "duration": "15:22",
        "mmr": -18,
        "apm": 220,
    },
]

BOT_STATUS = {
    "running": False,
    "mmr": 4867,
    "wins": 47,
    "losses": 23,
    "win_rate": 67.1,
    "avg_apm": 191,
    "current_map": "—",
}

# ============================================================
# Components
# ============================================================


def stat_card(title: str, value: str, color: str = "primary", sub: str = ""):
    return Div(
        Div(
            Div(Strong(title), cls="text-muted small"),
            Div(value, cls=f"fs-2 fw-bold text-{color}"),
            Div(sub, cls="text-muted small") if sub else "",
            cls="p-3",
        ),
        cls="card shadow-sm h-100",
    )


def game_row(game: dict) -> Tr:
    result_color = "success" if game["result"] == "Win" else "danger"
    mmr_str = f"+{game['mmr']}" if game["mmr"] > 0 else str(game["mmr"])
    mmr_color = "text-success" if game["mmr"] > 0 else "text-danger"
    return Tr(
        Td(str(game["id"])),
        Td(game["map"]),
        Td(Span(game["result"], cls=f"badge bg-{result_color}")),
        Td(game["race"]),
        Td(game["duration"]),
        Td(Span(mmr_str, cls=mmr_color)),
        Td(str(game["apm"])),
    )


def navbar() -> Nav:
    return Nav(
        Div(
            A("SC2 Bot Manager", cls="navbar-brand fw-bold", href="/"),
            Div(
                Ul(
                    Li(A("Dashboard", cls="nav-link", href="/")),
                    Li(A("Games", cls="nav-link", href="/games")),
                    Li(A("Stats", cls="nav-link", href="/stats")),
                    Li(A("Live", cls="nav-link", href="/live")),
                    cls="navbar-nav",
                ),
                cls="collapse navbar-collapse",
            ),
            cls="container",
        ),
        cls="navbar navbar-expand-lg navbar-dark bg-dark mb-4",
    )


# ============================================================
# Routes
# ============================================================


@rt("/")
def index():
    status = BOT_STATUS
    return Html(
        Head(Title("SC2 Bot Dashboard")),
        Body(
            navbar(),
            Div(
                H1("SC2 Bot Dashboard", cls="mb-4"),
                # Status banner
                Div(
                    (
                        Span("● OFFLINE", cls="badge bg-secondary fs-6")
                        if not status["running"]
                        else Span("● RUNNING", cls="badge bg-success fs-6")
                    ),
                    cls="mb-4",
                ),
                # Stat cards row
                Div(
                    Div(stat_card("MMR", str(status["mmr"]), "primary"), cls="col"),
                    Div(
                        stat_card(
                            "Win Rate",
                            f"{status['win_rate']}%",
                            "success",
                            f"{status['wins']}W / {status['losses']}L",
                        ),
                        cls="col",
                    ),
                    Div(
                        stat_card("Avg APM", str(status["avg_apm"]), "info"), cls="col"
                    ),
                    Div(
                        stat_card(
                            "Total Games",
                            str(status["wins"] + status["losses"]),
                            "warning",
                        ),
                        cls="col",
                    ),
                    cls="row row-cols-4 g-3 mb-4",
                ),
                # Recent games table
                H2("Recent Games", cls="mb-3"),
                Div(
                    Table(
                        Thead(
                            Tr(
                                Th("#"),
                                Th("Map"),
                                Th("Result"),
                                Th("Race"),
                                Th("Duration"),
                                Th("MMR"),
                                Th("APM"),
                            )
                        ),
                        Tbody(*[game_row(g) for g in GAME_HISTORY]),
                        cls="table table-striped table-hover",
                    ),
                    cls="table-responsive",
                ),
                # HTMX live refresh button
                Button(
                    "Refresh Status",
                    hx_get="/api/status",
                    hx_target="#status-div",
                    hx_swap="innerHTML",
                    cls="btn btn-outline-primary mt-3",
                ),
                Div(id="status-div"),
                cls="container",
            ),
        ),
    )


@rt("/games")
def games():
    return Html(
        Head(Title("Games - SC2 Bot")),
        Body(
            navbar(),
            Div(
                H1("Game History", cls="mb-4"),
                Div(
                    Table(
                        Thead(
                            Tr(
                                Th("#"),
                                Th("Map"),
                                Th("Result"),
                                Th("Race"),
                                Th("Duration"),
                                Th("MMR"),
                                Th("APM"),
                            )
                        ),
                        Tbody(*[game_row(g) for g in GAME_HISTORY]),
                        cls="table table-striped",
                    ),
                    cls="table-responsive",
                ),
                cls="container",
            ),
        ),
    )


@rt("/stats")
def stats():
    wins = sum(1 for g in GAME_HISTORY if g["result"] == "Win")
    losses = len(GAME_HISTORY) - wins
    return Html(
        Head(Title("Stats - SC2 Bot")),
        Body(
            navbar(),
            Div(
                H1("Statistics", cls="mb-4"),
                Div(
                    Div(stat_card("Total Wins", str(wins), "success"), cls="col"),
                    Div(stat_card("Total Losses", str(losses), "danger"), cls="col"),
                    Div(
                        stat_card(
                            "Win Rate", f"{wins/(wins+losses)*100:.1f}%", "primary"
                        ),
                        cls="col",
                    ),
                    cls="row row-cols-3 g-3",
                ),
                cls="container",
            ),
        ),
    )


@rt("/live")
def live():
    return Html(
        Head(Title("Live - SC2 Bot")),
        Body(
            navbar(),
            Div(
                H1("Live Game Monitor", cls="mb-4"),
                Div(
                    P("No game in progress.", cls="text-muted"),
                    # HTMX auto-refresh every 3s
                    Div(
                        hx_get="/api/live_state",
                        hx_trigger="every 3s",
                        hx_swap="innerHTML",
                        id="live-state",
                    ),
                    cls="card p-4",
                ),
                cls="container",
            ),
        ),
    )


# ============================================================
# HTMX API Endpoints
# ============================================================


@rt("/api/status")
def api_status():
    ts = datetime.now().strftime("%H:%M:%S")
    return Div(
        Span(f"Last refreshed: {ts}", cls="text-muted small"),
        Span(" | MMR: ", cls="ms-2"),
        Strong(str(BOT_STATUS["mmr"]), cls="text-primary"),
    )


@rt("/api/live_state")
def api_live_state():
    return Div(
        P("Bot is idle. Start a game to see live data.", cls="text-muted"),
        Span(
            f"Checked at {datetime.now().strftime('%H:%M:%S')}", cls="text-muted small"
        ),
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    serve(port=8000)
