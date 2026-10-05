"""Visitor-facing names stay capitalized, and the preview link can open a new tab.

Player keys in seeds, marts, and games.js stay lowercase. The scorecard
index, viewer, and PNG header print Erin and Jordan. DAC 0.21 escapes HTML
in text widgets, so the Top-tab preview gets target=_blank from the proxy
script rather than from the markdown.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_proxy():
    path = REPO / "dashboard" / "scripts" / "newtab_proxy.py"
    spec = importlib.util.spec_from_file_location("newtab_proxy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_export():
    path = REPO / "dashboard" / "scripts" / "export_scorecards.py"
    spec = importlib.util.spec_from_file_location("export_scorecards", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_number_cards_title_player_fields():
    """Vega uses the field name as the accessible name on the big numbers.

    A missing title is what the live Top tab announced as erin_wins.
    Game-number tooltips stay titled Game. Scorecard links stay Scorecard.
    """
    import re

    dashboard = (REPO / "dashboard" / "yahtzee.yml").read_text()
    pattern = re.compile(r"\{[^{}\n]*field:\s*((?:erin|jordan)_[A-Za-z0-9_]+)[^{}\n]*\}")
    found = list(pattern.finditer(dashboard))
    assert found, "expected player field encodings"
    for match in found:
        field = match.group(1)
        blob = match.group(0)
        if field.endswith("_game_seq"):
            assert "title: Game" in blob, blob
            continue
        if field.endswith("_url"):
            assert "title: Scorecard" in blob, blob
            assert "title: Erin" not in blob and "title: Jordan" not in blob
            continue
        who = "Erin" if field.startswith("erin_") else "Jordan"
        assert f"title: {who}" in blob, blob


def test_scorecard_pages_capitalize_winner_names():
    index = (REPO / "dashboard" / "scorecards" / "index.html").read_text()
    viewer = (REPO / "dashboard" / "scorecards" / "viewer.html").read_text()
    assert '<td>${displayName(g.winner)}</td>' in index
    assert '<td>${g.winner}</td>' not in index
    assert "g.winner" in index  # search haystack stays the lowercase key
    assert "function displayName(key)" in index
    assert 'if (key === "erin") return "Erin";' in index
    assert 'if (key === "jordan") return "Jordan";' in index
    assert "const w = displayName(game.winner);" in viewer
    assert 'game.winner === "tie"' not in viewer
    export = (REPO / "dashboard" / "scripts" / "export_scorecards.py").read_text()
    assert 'f"winner {display_winner(game[\'winner\'])}' in export
    assert 'f"winner {game[\'winner\']}' not in export
    names = _load_export()
    assert names.display_winner("erin") == "Erin"
    assert names.display_winner("jordan") == "Jordan"
    assert names.display_winner("tie") == "tie"


def test_newtab_script_targets_only_the_preview():
    script = (REPO / "dashboard" / "pub_map" / "newtab.js").read_text()
    assert 'anchor.target = "_blank"' in script
    assert 'anchor.rel = "noopener"' in script
    assert '!== "/pub_map.html"' in script
    assert '"/pub_map/preview."' in script
    assert "querySelector(\"img\")" in script
    proxy = _load_proxy()
    html = b"<html><body><p>hi</p></body></html>"
    injected = proxy.inject_newtab(html, b"console.log(1)")
    assert injected.endswith(b"</body></html>")
    assert b"<script>/* pub-map-newtab */console.log(1)</script></body>" in injected
    assert proxy.inject_newtab(injected, b"console.log(2)") == injected
    assert proxy.inject_newtab(b"<p>no body tag</p>", b"x") == b"<p>no body tag</p>"


def test_deploy_puts_proxy_on_8321_and_dac_on_8322():
    rebuild = (REPO / "scripts" / "yahtzee-rebuild.sh").read_text()
    workflow = (REPO / ".github" / "workflows" / "deploy-vps.yml").read_text()
    caddy = (REPO / "scripts" / "Caddyfile.local").read_text()
    for text in (rebuild, workflow):
        assert "newtab_proxy.py --listen 127.0.0.1:8321 --upstream 127.0.0.1:8322" in text
        assert "s/--port 8321/--port 8322/" in text
        assert "yahtzee-newtab-proxy" in text
    assert "reverse_proxy 127.0.0.1:8321" in caddy
    dashboard = (REPO / "dashboard" / "yahtzee.yml").read_text()
    assert "[![Pub map](/pub_map/preview.svg)](/pub_map.html)" in dashboard
