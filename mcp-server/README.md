# Lavička Memory MCP Server

MCP server pro Claude Desktop / VS Code. Umožňuje pracovat s pamětí NPC.

## Instalace

```bash
npm install
npm run build
```

## Konfigurace

### Claude Desktop

Uprav `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lavicka-memory": {
      "command": "node",
      "args": ["C:\\cesta\\k\\mcp-server\\dist\\index.js"]
    }
  }
}
```

### VS Code (Cline/Claude Dev)

V nastavení rozšíření přidej MCP server.

## Nástroje

### pamet_hledej_osobu
Hledá osobu v paměti.

```json
{
  "npc_id": "babicka_vlasta",
  "osoba_id": "delnik_franta"
}
```

### pamet_uloz_osobu
Uloží vzpomínku.

```json
{
  "npc_id": "babicka_vlasta",
  "osoba_id": "delnik_franta",
  "popis": "chlap v montérkách",
  "jmeno": "Franta",
  "dojem": "sympatický, bodrý",
  "temata": ["práce", "rodina"],
  "fakta": ["pracuje na stavbě"],
  "emoce_intenzita": 0.6
}
```

### pamet_vztah
Získá vztah.

### pamet_aktualizuj_vztah
Aktualizuje vztah.

```json
{
  "osoba_a": "babicka_vlasta",
  "osoba_b": "delnik_franta",
  "faze": "znami",
  "tykani": false,
  "sympatie_zmena": 0.1
}
```

### pamet_decay
Aplikuje zapomínání.

### pamet_seznam
Vypíše paměť NPC.
