# ==============================================================================
# GAME DATA LOADER & NAMER
# ==============================================================================
import html
import os
import re

from .constants import (
    REF_REGEX, SECTOR_REGEX, BUILTIN_SECTORS, BUILTIN_SHIP_NAMES, BUILTIN_WARE_NAMES,
    BUILTIN_WARE_VOLUMES, AVERAGE_WARE_PRICES, FALLBACK_PROD_CONSUMPTION,
)
from .utils import prettify

class GameData:
    def __init__(self, game_dir):
        self.dir = game_dir
        self.index, self.sources, self.text = {}, [], {}
        self.wares, self.ware_volumes, self.ware_recipes, self.sector_name_tags = {}, {}, {}, {}
        self.macro_cache, self.ok = {}, False
        self.gear_macro_paths = {}
        if game_dir and os.path.isdir(game_dir):
            self._build()

    def _index_folder(self, src, folder):
        if not os.path.isdir(folder): return
        self.sources.append((src, folder))
        try:
            cats = sorted(f for f in os.listdir(folder) if f.endswith(".cat") and "_sig" not in f)
        except OSError: return
        for c in cats:
            dat = os.path.join(folder, c[:-4] + ".dat")
            if not os.path.exists(dat): continue
            off = 0
            try:
                with open(os.path.join(folder, c), "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        p = line.rstrip("\r\n").rsplit(" ", 3)
                        if len(p) != 4: continue
                        try: size = int(p[1])
                        except ValueError: continue
                        self.index.setdefault(p[0].lower(), {})[src] = (dat, off, size)
                        off += size
            except OSError: pass

    def read_all(self, rel):
        rel = rel.replace("\\", "/").lower()
        out = []
        for src, folder in self.sources:
            loose = os.path.join(folder, *rel.split("/"))
            if os.path.isfile(loose):
                try:
                    with open(loose, "rb") as fh: out.append(fh.read())
                except OSError: pass
                continue
            e = self.index.get(rel, {}).get(src)
            if e:
                try:
                    with open(e[0], "rb") as fh:
                        fh.seek(e[1])
                        out.append(fh.read(e[2]))
                except OSError: pass
        return [b.decode("utf-8", "replace") for b in out]

    def _build(self):
        self._index_folder("base", self.dir)
        ext = os.path.join(self.dir, "extensions")
        if os.path.isdir(ext):
            for d in sorted(os.listdir(ext)):
                sub = os.path.join(ext, d)
                if os.path.isdir(sub): self._index_folder(d, sub)

        # Index loose gear macro files by macro name (base + extensions)
        for src, folder in self.sources:
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    if not f.endswith("_macro.xml"):
                        continue
                    macro = f[:-len(".xml")].lower()
                    rel = os.path.relpath(os.path.join(root, f), folder).replace("\\", "/").lower()
                    self.gear_macro_paths.setdefault(macro, (src, rel))

        for txt in self.read_all("t/0001-l044.xml"):
            for pm in re.finditer(r'<page\s+id="(\d+)"[^>]*>(.*?)</page>', txt, re.S):
                p_id = pm.group(1)
                for tm in re.finditer(r'<t\s+id="(\d+)"[^>]*>(.*?)</t>', pm.group(2), re.S):
                    self.text[(p_id, tm.group(1))] = html.unescape(tm.group(2))

        for txt in self.read_all("libraries/mapdefaults.xml"):
            for m in re.finditer(r'<dataset\s+macro="([a-zA-Z0-9_]+_sector[0-9_]*macro)"', txt):
                seg = txt[m.end():m.end() + 900]
                n = re.search(r'<identification[^>]*?\bname="([^"]+)"', seg)
                if n: self.sector_name_tags[m.group(1).lower()] = n.group(1)

        for txt in self.read_all("libraries/wares.xml"):
            for wm in re.finditer(r'<ware\b([^>]*)>(.*?)</ware>', txt, re.S):
                attrs, body = wm.group(1), wm.group(2)
                i = re.search(r'\bid="([^"]+)"', attrs)
                n = re.search(r'\bname="([^"]+)"', attrs)
                v = re.search(r'\bvolume="([^"]+)"', attrs)
                if not i: continue
                wid = i.group(1).lower()
                if n: self.wares[wid] = n.group(1)
                if v:
                    try: self.ware_volumes[wid] = float(v.group(1))
                    except ValueError: pass

                for prod in re.finditer(r'<production\b([^>]*)>(.*?)</production>', body, re.S):
                    p_attrs, p_body = prod.group(1), prod.group(2)
                    t_match = re.search(r'\btime="([^"]+)"', p_attrs)
                    if not t_match: continue
                    try: cycle_time = float(t_match.group(1))
                    except ValueError: continue
                    if cycle_time <= 0: continue
                    m_match = re.search(r'\bmethod="([^"]+)"', p_attrs)
                    method = m_match.group(1).lower() if m_match else "default"
                    cycles_per_hr = 3600.0 / cycle_time
                    inputs = {}
                    pri_match = re.search(r'<primary>(.*?)</primary>', p_body, re.S)
                    scan_body = pri_match.group(1) if pri_match else p_body
                    for in_ware in re.finditer(r'<ware\b([^>]*)>', scan_body):
                        iw_attrs = in_ware.group(1)
                        w_id = re.search(r'\bware="([^"]+)"', iw_attrs)
                        w_amt = re.search(r'\bamount="([^"]+)"', iw_attrs)
                        if w_id and w_amt:
                            try: inputs[w_id.group(1).lower()] = float(w_amt.group(1)) * cycles_per_hr
                            except ValueError: pass
                    if inputs:
                        self.ware_recipes[(wid, method)] = inputs
                        if wid not in self.ware_recipes: self.ware_recipes[wid] = inputs
        self.ok = bool(self.text)

    def resolve(self, raw, depth=0):
        if not raw: return ""
        def sub(m):
            t = self.text.get((m.group(1), m.group(2)))
            if t is None:
                if (m.group(1), m.group(2)) == ("20102", "1011"): t = "Trade Station"
                elif (m.group(1), m.group(2)) == ("20102", "2011"): t = "Defence Platform"
                elif (m.group(1), m.group(2)) == ("20102", "3001"): t = "Headquarters"
            if t is None: return m.group(0)
            return self.resolve(t, depth + 1) if depth < 8 else t

        s = REF_REGEX.sub(sub, raw)
        s = re.sub(r"\s*\\?\([^()]*\\?\)\s*", " ", s)
        parts = s.split()
        if len(parts) >= 2 and len(parts) % 2 == 0:
            half = len(parts) // 2
            if parts[:half] == parts[half:]: parts = parts[:half]
        return " ".join(parts).strip()

    def ship_macro_name(self, macro):
        if macro in self.macro_cache: return self.macro_cache[macro]
        res = None
        parts = macro.split("_")
        if self.ok and len(parts) > 3 and parts[2] in ("xs", "s", "m", "l", "xl"):
            for txt in reversed(self.read_all(f"assets/units/size_{parts[2]}/macros/{macro}.xml")):
                m = re.search(r'<identification[^>]*?\bname="([^"]+)"', txt)
                if m:
                    r = self.resolve(m.group(1))
                    if r and not REF_REGEX.search(r):
                        res = r
                        break
        self.macro_cache[macro] = res
        return res

    def gear_macro_name(self, macro):
        """Resolve a gear macro (weapon/turret/shield/engine/missile) to its display name."""
        if not macro:
            return None
        m_lower = macro.lower()
        if m_lower in self.macro_cache:
            return self.macro_cache[m_lower]
        res = None
        if self.ok:
            entry = self.gear_macro_paths.get(m_lower)
            if entry:
                src, rel = entry
                for txt in reversed(self.read_all(rel)):
                    m = re.search(r'<identification[^>]*?\bname="([^"]+)"', txt)
                    if m:
                        r = self.resolve(m.group(1))
                        if r and not REF_REGEX.search(r):
                            res = r
                            break
        self.macro_cache[m_lower] = res
        return res

class Namer:
    def __init__(self, gd=None, overrides=None):
        self.gd, self.ov = gd, overrides or {}

    def text(self, raw):
        if not raw: return ""
        return self.gd.resolve(raw) if (self.gd and self.gd.ok) else raw

    def sector(self, macro):
        if not macro: return "Unknown / Transit"
        m_lower = macro.lower()
        if m_lower in self.ov: return self.ov[m_lower]
        m = SECTOR_REGEX.search(m_lower)
        if self.gd and self.gd.ok:
            tag = self.gd.sector_name_tags.get(m_lower)
            if not tag and m: tag = "{20004,%d}" % (int(m.group(1)) * 10000 + int(m.group(2)) * 10 + 1)
            if tag:
                r = self.gd.resolve(tag)
                if r and not REF_REGEX.search(r): return r
        if m:
            key = (int(m.group(1)), int(m.group(2)))
            if key in BUILTIN_SECTORS: return BUILTIN_SECTORS[key]
            return f"Cluster {key[0]} / Sector {key[1]:02d}"
        return prettify(m_lower.replace("cluster_", "").replace("sector_", "").replace("_macro", ""))

    def gear(self, macro):
        """Resolve a gear macro to its display name, falling back to prettified macro."""
        m_lower = (macro or "").lower()
        if not m_lower:
            return "Unknown Gear"
        if self.gd and self.gd.ok:
            r = self.gd.gear_macro_name(m_lower)
            if r:
                return r
        clean = re.sub(r"^(weapon|turret|shield|engine|missile|missilelauncher|missileturret|thruster)_", "", m_lower)
        clean = clean.replace("_macro", "")
        return prettify(clean)

    def ship(self, macro):
        m_lower = (macro or "").lower()
        if m_lower in self.ov: return self.ov[m_lower]
        if self.gd and self.gd.ok:
            r = self.gd.ship_macro_name(m_lower)
            if r: return r
        if m_lower in BUILTIN_SHIP_NAMES: return BUILTIN_SHIP_NAMES[m_lower]
        clean = re.sub(r"^ship_|_macro$", "", m_lower)
        parts = [p.capitalize() for p in clean.split("_") if p not in ["01", "02", "03", "a", "b", "c"]]
        return " ".join(parts) if parts else prettify(clean)

    def ware(self, wid):
        wid_lower = wid.lower()
        if self.gd and self.gd.ok and wid_lower in self.gd.wares:
            r = self.gd.resolve(self.gd.wares[wid_lower])
            if r and not REF_REGEX.search(r): return r
        if wid_lower in BUILTIN_WARE_NAMES: return BUILTIN_WARE_NAMES[wid_lower]
        return prettify(wid_lower)

    def volume(self, wid):
        wid_lower = wid.lower()
        if self.gd and self.gd.ok and wid_lower in self.gd.ware_volumes:
            return self.gd.ware_volumes[wid_lower]
        return BUILTIN_WARE_VOLUMES.get(wid_lower, 10.0)

    def price(self, wid):
        return AVERAGE_WARE_PRICES.get(wid.lower(), 150.0)

    def module_inputs(self, macro):
        m = macro.lower().replace("_macro", "")
        parts = m.split("_")
        race = parts[1] if len(parts) > 1 and parts[0] == "prod" else ""
        target_ware = parts[2] if len(parts) > 2 and parts[0] == "prod" else m
        race_to_method = {"ter": "terran", "tel": "teladi", "bor": "boron", "spl": "split", "arg": "default", "par": "default", "gen": "default"}
        method = race_to_method.get(race, "default")
        if self.gd and (target_ware, method) in self.gd.ware_recipes:
            return self.gd.ware_recipes[(target_ware, method)]
        if (target_ware, method) in FALLBACK_PROD_CONSUMPTION:
            return FALLBACK_PROD_CONSUMPTION[(target_ware, method)]
        if self.gd and target_ware in self.gd.ware_recipes:
            return self.gd.ware_recipes[target_ware]
        return FALLBACK_PROD_CONSUMPTION.get((target_ware, "default"), {})

