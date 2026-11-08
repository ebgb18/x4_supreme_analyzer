# 🛰️ X4: Foundations — Supreme Command & Empire Intelligence Terminal

> **High-performance streaming savegame auditor and interactive tactical web terminal for *X4: Foundations* (v7.0 / v8.0+).**  
> *Zero external dependencies — pure Python 3.8+ standard library.*

---

## ⚡ What is it?

**X4 Supreme Command Terminal** is an enterprise-grade empire auditor and visualization suite for Egosoft's *X4: Foundations*. It streams and parses massive `.xml` or compressed `.xml.gz` save files in seconds without memory bloat, generating both a comprehensive **Grand-Tactical Markdown Dossier** and an **interactive, offline HTML5 Tactical Radar Terminal**.

Whether you are managing a 500+ ship war fleet, debugging stalled station logistics, tracking down abandoned Timelines derelicts, or skimming excess dividends from corporate accounts, this tool gives you complete strategic visibility.

---

## 🚀 Key Features

* **🛰️ Standalone HTML5 Tactical Radar & Viewport**
  * Sector-by-sector and galaxy-wide 2D radar with live coordinate projection.
  * Real-time pan, zoom, click-to-inspect target telemetry, and layer filtering (Stations, Warships, Civilian Hulls, Hostiles, Derelicts, and Jump Gates).

* **⚔️ Live War Room & 30s Tactical Window**
  * Live combat engagement triage with intelligent friendly-fire and dock-collider filtering.
  * Galactic Threat Matrix calculating exact gate-hop proximity to Xenon capitals (I, K, H).
  * Marine boarding assault power evaluation with accurate 0–15 skill rating scaling.

* **💰 Commercial Trade & Ledger Analyzer (Nexus Mod 1801 Parity)**
  * Reconstructs full buy/sell trade cycles from the save logbook.
  * Realized net profit leaderboards, external NPC margins, hold utilization %, and commodity cash-cow rankings.
  * Inactive trader alert for stalled or blacklisted freighters.

* **🏭 Industrial Diagnostics & Storage Choke Matrix**
  * Container, Solid, and Liquid storage saturation percentages with critical choke alerts (>92%).
  * End-to-end production starvation tracking (flags depleted inputs before factories stall).
  * Workforce habitat ceilings, efficiency bonuses, and food/medical supply autonomy timers.
  * Logical overview audit: trade rules, manual vs. auto pricing, and buy/sell slider thresholds.

* **🏗️ Station Construction & Build Storage Logistics**
  * Tracks station expansion queues, assigned construction builders, and missing build storage wares.
  * Shipyard and Wharf slipway queues with customer faction, progress, and remaining build time.

* **🔍 Derelict & Data Vault Reconnaissance**
  * Exact sector-relative 3D coordinates for all unowned/abandoned hulls (including rare Timelines ships like the Xenon H, Sapporo, and Kuraokami).
  * Data Vault and Erlking blueprint vault locator with lock/seal status.

* **💎 Empire Balance Sheet & Corporate Treasury Skimmer**
  * Full net worth calculation (personal purse + station capital + ship assets + real estate + ware stockpiles).
  * Recommends safe dividend skimming thresholds per station while preserving operational reserves.

---

## 🛠️ Zero Dependencies / Requirements

* **Python 3.8+** (Uses only built-in standard libraries: `xml.parsers.expat`, `gzip`, `json`, `webbrowser`, etc.).
* No `pip install` required.
* Compatible with vanilla, DLCs (*Cradle of Humanity*, *Tides of Avarice*, *Kingdom End*, *Timelines*), and modded saves.

---

## 💻 Quick Start

### Basic Run (Auto-detects latest save):
```bash
python x4_supreme_auditor_1_7_4.py
```

### Specify Save File:
```bash
python x4_supreme_auditor_1_7_4.py "C:\Users\You\Documents\Egosoft\X4\12345678\save\save_001.xml.gz"
```

### Command-Line Arguments:
```text
  save                  Path to .xml or .xml.gz save file (auto-detected if omitted)
  --game-dir PATH       Path to unpacked game files / extensions for canonical name parsing
  --out PATH            Output path for the Markdown dossier (default: x4_master_empire_dossier.md)
  --html PATH           Output path for the HTML terminal (default: x4_command_terminal.html)
  --no-browser          Do not automatically pop up the terminal in your default browser
```
```

---

### Key Tags / Topics for the Repo
`x4-foundations` `x4` `savegame-parser` `egosoft` `tactical-radar` `space-sim` `python` `data-visualization` `economy-analyzer`