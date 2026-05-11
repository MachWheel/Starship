# SF64 — Dublagem em Português Brasileiro

**Versão: v{{VERSION}} (WIP / preview)**

Mod de dublagem em português brasileiro para Star Fox 64 no port Starship.

> **Aviso:** Esta é uma versão preview. Apenas parte das falas está dublada;
> as demais continuam tocando em inglês. O progresso atual está descrito em
> [`CREDITS.md`](CREDITS.md) e detalhado em
> [`ptbr_audio/lines.csv`](https://github.com/MachWheel/Starship/blob/main/ptbr_audio/lines.csv)
> no repositório do projeto.

---

### Pré-requisitos

- Windows 10 ou 11 (64 bits).
- Uma instalação funcional do Starship com sua própria `sf64.o2r` gerada a partir
  da sua ROM (US 1.0 ou US 1.1) — esta release **não inclui** assets do jogo.

### Instalação

1. Faça backup do seu `Starship.exe` atual (opcional).
2. Extraia este zip dentro da pasta do seu Starship.
3. Quando perguntado, sobrescreva o `Starship.exe` e mescle a pasta `mods/`.
4. Inicie `Starship.exe`.

### Verificação

Inicie o briefing da fase Corneria pelo mapa. Você deve ouvir o General Pepper
e o Fox falando em português brasileiro, com o som de estática do rádio
preservado, e o texto na tela deve coincidir com a fala. As demais falas já
dubladas tocam ao longo das missões Corneria e Meteo.

### Falas dubladas nesta versão

Ainda em preview. A lista canônica está em
[`ptbr_audio/lines.csv`](https://github.com/MachWheel/Starship/blob/main/ptbr_audio/lines.csv)
(coluna `is_complete=yes`). Falas não dubladas continuam tocando em inglês,
mas o texto do balão pode aparecer em português quando o `script_pt` da linha
já estiver escrito.

### Arquivos incluídos

| Arquivo | Função |
|---|---|
| `Starship.exe` | Build do Starship com os hooks de dublagem |
| `ptbr_audio/voice_manifest.txt` | Manifesto de voz (roteamento `msgId → wav`) |
| `ptbr_audio/<personagem>/*.wav` | Gravações pt-BR das falas |
| `mods/SF64-DubPT-BR.o2r` | Texto traduzido para os balões de rádio |
| `LICENSE-libultraship.txt` | Licença MIT do libultraship (obrigatória na redistribuição) |
| `CREDITS.md` | Créditos completos de tradução, elenco e licenças |

### Créditos e licenças

- Créditos completos em [`CREDITS.md`](CREDITS.md).
- Starship: CC0 1.0 Universal (domínio público).
- libultraship: MIT — ver [`LICENSE-libultraship.txt`](LICENSE-libultraship.txt).

### Fonte

- Este fork: <https://github.com/MachWheel/Starship>
- Upstream: <https://github.com/HarbourMasters/Starship>
