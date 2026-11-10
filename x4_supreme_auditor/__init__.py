# ==============================================================================
# X4: Foundations (v8.0+) - Supreme Command & Empire Intelligence Terminal
# Version: V1.7.7 Enterprise - Supreme Intelligence Edition
# Zero external dependencies: 100% standard Python 3.8+ (expat, json, gzip, webbrowser)
# ==============================================================================

__version__ = "1.7.7"

from .constants import *  # noqa: F401,F403
from .utils import prettify, esc, num, classify_ship, gear_parts, gear_category, ammo_class
from .gamedata import GameData, Namer
from .models import TradeTransaction, CompletedTrade, Ship, BuildStorage, Station
from .parser import SaveParser
from .analytics import (
    process_trade_analytics, compute_trade_intelligence, compute_logistics_intelligence,
    compute_derelict_valuation, compute_empire_health, build_commander_briefing,
    compute_market_intelligence,
)
from .dossier import table, build_dossier
from .terminal import generate_command_terminal_html
from .cli import find_game_dir, find_default_save, main
