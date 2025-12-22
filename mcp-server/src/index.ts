#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_FILE = path.join(__dirname, "..", "data", "memories.json");

// === TYPY ===

interface Osoba {
  id: string;
  popis: string;
  jmeno: string | null;
  dojem: string;
  temata: string[];
  fakta: string[];
  sila: number;
  posledni_setkani: string;
  pocet_setkani: number;
}

interface Vztah {
  id: string;
  osoba_a: string;
  osoba_b: string;
  faze: "cizinci" | "tvare" | "znami" | "pratele";
  tykani: boolean;
  sympatie: number;
  historie: string[];
}

interface NPCMemory {
  npc_id: string;
  lide: Record<string, Osoba>;
  vztahy: Record<string, Vztah>;
}

interface MemoryStore {
  npcs: Record<string, NPCMemory>;
  last_updated: string;
}

// === POMOCNÉ FUNKCE ===

function loadData(): MemoryStore {
  try {
    if (fs.existsSync(DATA_FILE)) {
      const raw = fs.readFileSync(DATA_FILE, "utf-8");
      return JSON.parse(raw);
    }
  } catch (e) {
    console.error("Chyba při načítání dat:", e);
  }
  return { npcs: {}, last_updated: new Date().toISOString() };
}

function saveData(data: MemoryStore): void {
  data.last_updated = new Date().toISOString();
  const dir = path.dirname(DATA_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), "utf-8");
}

function getNPCMemory(data: MemoryStore, npcId: string): NPCMemory {
  if (!data.npcs[npcId]) {
    data.npcs[npcId] = {
      npc_id: npcId,
      lide: {},
      vztahy: {},
    };
  }
  return data.npcs[npcId];
}

function applyDecay(data: MemoryStore): void {
  const DECAY_RATE = 0.98; // Denní decay
  const MIN_SILA = 0.05;

  for (const npcId in data.npcs) {
    const npc = data.npcs[npcId];
    const toDelete: string[] = [];

    for (const osobaId in npc.lide) {
      const osoba = npc.lide[osobaId];
      osoba.sila *= DECAY_RATE;

      if (osoba.sila < MIN_SILA) {
        toDelete.push(osobaId);
      }
    }

    for (const id of toDelete) {
      delete npc.lide[id];
    }
  }

  saveData(data);
}

function pairKey(a: string, b: string): string {
  return [a, b].sort().join("__");
}

// === MCP SERVER ===

const server = new Server(
  {
    name: "lavicka-memory",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Seznam nástrojů
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "pamet_uloz_osobu",
        description:
          "Uloží nebo aktualizuje vzpomínku na osobu. Volej po skončení rozhovoru.",
        inputSchema: {
          type: "object",
          properties: {
            npc_id: {
              type: "string",
              description: "ID NPC které si pamatuje (např. 'babicka_vlasta')",
            },
            osoba_id: {
              type: "string",
              description: "ID osoby na kterou vzpomíná (např. 'delnik_franta')",
            },
            popis: {
              type: "string",
              description: "Stručný popis osoby (např. 'chlap v montérkách, asi 50 let')",
            },
            jmeno: {
              type: "string",
              description: "Jméno pokud ho zná, jinak null",
            },
            dojem: {
              type: "string",
              description: "Celkový dojem (např. 'sympatický, trochu unavený')",
            },
            temata: {
              type: "array",
              items: { type: "string" },
              description: "O čem mluvili (např. ['práce', 'rodina', 'moře'])",
            },
            fakta: {
              type: "array",
              items: { type: "string" },
              description: "Co se dozvěděl (např. ['pracuje na stavbě', 'je rozvedený'])",
            },
            emoce_intenzita: {
              type: "number",
              description: "Jak silný byl rozhovor 0-1 (silnější = lépe si pamatuje)",
            },
          },
          required: ["npc_id", "osoba_id", "popis", "dojem"],
        },
      },
      {
        name: "pamet_hledej_osobu",
        description:
          "Hledá v paměti NPC jestli zná danou osobu podle popisu. Volej na začátku setkání.",
        inputSchema: {
          type: "object",
          properties: {
            npc_id: {
              type: "string",
              description: "ID NPC které hledá v paměti",
            },
            osoba_id: {
              type: "string",
              description: "ID osoby kterou hledá (pokud známe)",
            },
            popis: {
              type: "string",
              description: "Popis osoby pro vyhledání",
            },
          },
          required: ["npc_id"],
        },
      },
      {
        name: "pamet_aktualizuj_vztah",
        description: "Aktualizuje vztah mezi dvěma NPC.",
        inputSchema: {
          type: "object",
          properties: {
            osoba_a: {
              type: "string",
              description: "ID první osoby",
            },
            osoba_b: {
              type: "string",
              description: "ID druhé osoby",
            },
            faze: {
              type: "string",
              enum: ["cizinci", "tvare", "znami", "pratele"],
              description: "Fáze vztahu",
            },
            tykani: {
              type: "boolean",
              description: "Jestli si tykají",
            },
            sympatie_zmena: {
              type: "number",
              description: "Změna sympatií (-1 až +1)",
            },
            udalost: {
              type: "string",
              description: "Co se stalo (pro historii)",
            },
          },
          required: ["osoba_a", "osoba_b"],
        },
      },
      {
        name: "pamet_vztah",
        description: "Získá informace o vztahu mezi dvěma NPC.",
        inputSchema: {
          type: "object",
          properties: {
            osoba_a: {
              type: "string",
              description: "ID první osoby",
            },
            osoba_b: {
              type: "string",
              description: "ID druhé osoby",
            },
          },
          required: ["osoba_a", "osoba_b"],
        },
      },
      {
        name: "pamet_shrn_rozhovor",
        description:
          "Požádá o shrnutí rozhovoru pro uložení do paměti. Vrátí strukturu pro pamet_uloz_osobu.",
        inputSchema: {
          type: "object",
          properties: {
            npc_id: {
              type: "string",
              description: "ID NPC z jehož pohledu shrnout",
            },
            partner_id: {
              type: "string",
              description: "ID partnera v rozhovoru",
            },
            partner_popis: {
              type: "string",
              description: "Popis partnera",
            },
            rozhovor: {
              type: "string",
              description: "Text rozhovoru k shrnutí",
            },
          },
          required: ["npc_id", "partner_id", "partner_popis", "rozhovor"],
        },
      },
      {
        name: "pamet_decay",
        description: "Aplikuje zapomínání na všechny vzpomínky. Volej jednou za 'den'.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "pamet_seznam",
        description: "Vypíše všechny vzpomínky daného NPC.",
        inputSchema: {
          type: "object",
          properties: {
            npc_id: {
              type: "string",
              description: "ID NPC",
            },
          },
          required: ["npc_id"],
        },
      },
    ],
  };
});

// Zpracování volání nástrojů
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const data = loadData();

  try {
    switch (name) {
      // === ULOŽIT OSOBU ===
      case "pamet_uloz_osobu": {
        const npcMem = getNPCMemory(data, args.npc_id as string);
        const osobaId = args.osoba_id as string;

        const existing = npcMem.lide[osobaId];
        const emoceIntenzita = (args.emoce_intenzita as number) || 0.5;

        // Síla paměti - nová nebo posílená
        let sila = existing ? Math.min(1.0, existing.sila + 0.2) : 0.5;
        sila = Math.min(1.0, sila * (1 + emoceIntenzita * 0.3));

        npcMem.lide[osobaId] = {
          id: osobaId,
          popis: (args.popis as string) || existing?.popis || "",
          jmeno: (args.jmeno as string) || existing?.jmeno || null,
          dojem: (args.dojem as string) || existing?.dojem || "",
          temata: [
            ...new Set([
              ...(existing?.temata || []),
              ...((args.temata as string[]) || []),
            ]),
          ],
          fakta: [
            ...new Set([
              ...(existing?.fakta || []),
              ...((args.fakta as string[]) || []),
            ]),
          ],
          sila,
          posledni_setkani: new Date().toISOString(),
          pocet_setkani: (existing?.pocet_setkani || 0) + 1,
        };

        saveData(data);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  success: true,
                  message: `Vzpomínka na ${osobaId} uložena`,
                  sila: npcMem.lide[osobaId].sila,
                  pocet_setkani: npcMem.lide[osobaId].pocet_setkani,
                },
                null,
                2
              ),
            },
          ],
        };
      }

      // === HLEDAT OSOBU ===
      case "pamet_hledej_osobu": {
        const npcMem = getNPCMemory(data, args.npc_id as string);
        const osobaId = args.osoba_id as string;

        if (osobaId && npcMem.lide[osobaId]) {
          const osoba = npcMem.lide[osobaId];

          let rozpoznani: string;
          if (osoba.sila > 0.7) {
            rozpoznani = "poznam_dobre";
          } else if (osoba.sila > 0.5) {
            rozpoznani = "poznam";
          } else if (osoba.sila > 0.3) {
            rozpoznani = "povedome";
          } else {
            rozpoznani = "nejasne";
          }

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    nalezeno: true,
                    rozpoznani,
                    osoba,
                  },
                  null,
                  2
                ),
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                nalezeno: false,
                rozpoznani: "neznam",
                message: "Tuto osobu neznám",
              }),
            },
          ],
        };
      }

      // === AKTUALIZOVAT VZTAH ===
      case "pamet_aktualizuj_vztah": {
        const key = pairKey(args.osoba_a as string, args.osoba_b as string);

        // Vztahy jsou globální, ne per-NPC
        if (!data.npcs["_vztahy"]) {
          data.npcs["_vztahy"] = { npc_id: "_vztahy", lide: {}, vztahy: {} };
        }

        const vztahy = data.npcs["_vztahy"].vztahy;
        const existing = vztahy[key];

        vztahy[key] = {
          id: key,
          osoba_a: args.osoba_a as string,
          osoba_b: args.osoba_b as string,
          faze: (args.faze as Vztah["faze"]) || existing?.faze || "cizinci",
          tykani:
            args.tykani !== undefined
              ? (args.tykani as boolean)
              : existing?.tykani || false,
          sympatie: Math.max(
            -1,
            Math.min(
              1,
              (existing?.sympatie || 0) + ((args.sympatie_zmena as number) || 0)
            )
          ),
          historie: [
            ...(existing?.historie || []),
            ...(args.udalost ? [args.udalost as string] : []),
          ].slice(-10), // Max 10 položek historie
        };

        saveData(data);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  success: true,
                  vztah: vztahy[key],
                },
                null,
                2
              ),
            },
          ],
        };
      }

      // === ZÍSKAT VZTAH ===
      case "pamet_vztah": {
        const key = pairKey(args.osoba_a as string, args.osoba_b as string);

        const vztahy = data.npcs["_vztahy"]?.vztahy || {};
        const vztah = vztahy[key];

        if (vztah) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ nalezeno: true, vztah }, null, 2),
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                nalezeno: false,
                vztah: {
                  faze: "cizinci",
                  tykani: false,
                  sympatie: 0,
                  historie: [],
                },
              }),
            },
          ],
        };
      }

      // === SHRNUTÍ ROZHOVORU (pomocný) ===
      case "pamet_shrn_rozhovor": {
        // Tento tool vrací instrukce - samotné shrnutí dělá Claude
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                instrukce: `Shrň rozhovor z pohledu ${args.npc_id}. Odpověz JSON strukturou:
{
  "popis": "krátký popis osoby (jak vypadá)",
  "jmeno": "jméno pokud zaznělo, jinak null",
  "dojem": "celkový dojem z člověka",
  "temata": ["téma1", "téma2"],
  "fakta": ["co ses dozvěděl 1", "co ses dozvěděl 2"],
  "emoce_intenzita": 0.5
}

Rozhovor k shrnutí:
${args.rozhovor}`,
              }),
            },
          ],
        };
      }

      // === DECAY ===
      case "pamet_decay": {
        applyDecay(data);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                message: "Decay aplikován na všechny vzpomínky",
              }),
            },
          ],
        };
      }

      // === SEZNAM ===
      case "pamet_seznam": {
        const npcMem = getNPCMemory(data, args.npc_id as string);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  npc_id: args.npc_id,
                  pocet_lidi: Object.keys(npcMem.lide).length,
                  lide: npcMem.lide,
                },
                null,
                2
              ),
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: "text",
              text: `Neznámý nástroj: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Chyba: ${error}`,
        },
      ],
      isError: true,
    };
  }
});

// === START ===
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Lavička Memory MCP server běží");
}

main().catch(console.error);
