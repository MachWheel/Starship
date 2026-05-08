# SF64 — Dublagem em Português Brasileiro

**Versão: v{{VERSION}} (WIP / preview)**

Mod de dublagem em português brasileiro para Star Fox 64 no port Starship.

> **Aviso:** Esta é uma versão preview com apenas algumas falas dubladas.
> A maioria das vozes ainda toca em inglês.

---

### Pré-requisitos

- Windows 10 ou 11 (64 bits).
- Uma instalação funcional do Starship com sua própria `sf64.o2r` gerada a partir
  da sua ROM (US 1.0 ou US 1.1) — esta release **não inclui** assets do jogo.

### Instalação A — Sobrescrever instalação existente (recomendado)

1. Faça backup do seu `Starship.exe` atual (opcional).
2. Extraia este zip dentro da pasta do seu Starship.
3. Quando perguntado, sobrescreva o `Starship.exe` e mescle a pasta `mods/`.
4. Inicie `Starship.exe`.

### Instalação B — Pasta separada

1. Extraia este zip em uma pasta nova.
2. Copie seu `sf64.o2r` (gerado a partir da sua ROM) para essa pasta.
3. Opcionalmente, copie também `config.yml` e `gamecontrollerdb.txt` da
   instalação original.
4. Inicie `Starship.exe` a partir dessa pasta.

> Em ambos os casos, **lance o Starship a partir da pasta que contém o
> `Starship.exe`** — os arquivos da dublagem são resolvidos relativos ao
> diretório de trabalho do processo, e a pasta `ptbr_audio/` (com o
> `voice_manifest.txt` e os WAVs) precisa estar ao lado do executável.

### Verificação

Inicie o briefing da fase Corneria pelo mapa. Você deve ouvir o General Pepper
e o Fox falando em português brasileiro, com o som de estática do rádio
preservado, e o texto na tela deve coincidir com a fala.

### Falas dubladas nesta versão

Apenas a abertura e algumas linhas iniciais de Corneria. A lista completa está
em `CREDITS.md`. Falas não dubladas continuam tocando em inglês.

### Arquivos incluídos

| Arquivo | Função |
|---|---|
| `Starship.exe` | Build do Starship com os hooks de dublagem |
| `ptbr_audio/` | Manifesto de voz (`voice_manifest.txt`) e gravações pt-BR |
| `mods/SF64-DubPT-BR.o2r` | Texto traduzido para as falas dubladas |

### Créditos e licenças

- Créditos completos em [`CREDITS.md`](CREDITS.md).
- Starship: CC0 1.0 Universal (domínio público).
- libultraship: MIT — ver [`LICENSE-libultraship.txt`](LICENSE-libultraship.txt).

### Fonte

- Este fork: <https://github.com/MachWheel/Starship>
- Upstream: <https://github.com/HarbourMasters/Starship>
