# ROADMAP — Dublagem PT-BR para Star Fox 64 (Starship)

> Plano vivo. Atualize na mesma alteração que avança ou muda o escopo.

## Objetivo

Entregar uma dublagem completa em português brasileiro para Star Fox 64
(port Starship) cobrindo as **722 linhas de voz** catalogadas em
`ptbr_audio/lines.csv`, com texto pt-BR casando com cada fala dublada,
distribuído como pacote drop-in para Windows.

## Status atual (2026-05-10)

- **106 / 722 linhas completas** (~15%) — fim a fim: gravadas, roteadas no
  manifesto, texto do balão batendo, validadas em jogo.
- **Corneria 61/61 ✅** — primeira missão totalmente dublada.
- Demais missões com progresso: **Meteo 20/42**, **Sector Y 1/38**,
  **Intro 1/7**, **Misc 23/102**.
- Personagens com mais falas dubladas: Slippy 31, Peppy 26, Falco 16,
  Fox 14, Granga 9, Attack Carrier Captain 6.
- 165 linhas têm `script_pt` escrito (pronto para gravar); 113 já têm `.wav`
  no disco.
- Toda a infraestrutura de áudio + texto está validada e escala sem novo
  trabalho de engenharia. Adicionar uma linha = 3 edições de dados (sem
  rebuild).

## Arquitetura (resumo)

Dois canais paralelos, ambos data-driven:

### Áudio
`Audio_PlayVoice(msgId)` é interceptado em `src/audio/audio_general.c`. O
intercept lê o `voice_manifest.txt` (carregado no primeiro `Audio_PlayVoice`)
e, para cada `msgId` listado, ou suprime o despacho do seq player ou
deixa rodar parcialmente para preservar o clique do rádio
(`letSeqRunForMsgIds`). Em paralelo, agenda o `.wav` pt-BR via Win32
`PlaySoundA(SND_ASYNC)` com 13 frames de delay, para o clique tocar
*antes* da voz dublada.

`audio_playback.c::Audio_NoteInitForLayer` colabora silenciando as notas
de conteúdo de voz que viriam depois do clique+fonema, evitando que a
voz em inglês toque por baixo da dublagem.

`msgId`s fora do manifesto seguem o caminho original do seq — todas as
demais vozes do jogo (e BGM/SFX de cutscene) continuam funcionando.

### Texto
`tools/dub/pack_text_o2r.py` lê `ptbr_audio/lines.csv` direto, codifica
cada `script_pt` na tabela de glifos do SF64 (acentos removidos — a fonte
não tem diacríticos; `\n` literal vira glifo de quebra de linha) e gera
`mods/SF64-DubPT-BR.o2r`. Esse `.o2r` sobrescreve as entradas
`ast_radio/gMsg_ID_<n>` de cada linha.

### Por que não substituir as samples no engine
A abordagem óbvia (empacotar PCM pt-BR em `.o2r` sobrescrevendo as samples
originais) foi prototipada e descartada. Três bloqueios:

1. **Multi-note dispatch:** o seq dispara várias notas de
   "phoneme replacement" por linha; mesmo com dedup, retomadas
   fragmentam o WAV em `Que…Que bom…Que…`.
2. **Mismatch de duração:** as notas do seq são agendadas para ~250 ms;
   gravações de 5+ s ficam cortadas.
3. **Crash do `sample_3310`:** sobrescrever a sample de `fontId=1 inst=7`
   trava o Starship — causa raiz não identificada após várias tentativas.

O seq player foi desenhado para fonemas ADPCM curtos; fazê-lo tocar PCM de
sentença completa exige reescrever o bytecode da sequence — fora de escopo.
O intercept cura o problema antes dessa complexidade rodar.

## Fluxo por linha

Para cada linha nova:

1. **Mapeie o `msgId`.** Se for chatter de rádio, normalmente o `msgId`
   já está em `lines.csv`. Para descobrir novos: `tools/dub/dump_messages.py`
   ou `fprintf(stderr, "msgId=%d", msgId)` temporário no topo de
   `Audio_PlayVoice` + replay.
2. **Escreva `script_pt`** em `ptbr_audio/lines.csv`. Respeite os limites
   do balão (rádio: 3 linhas × 19 chars; diálogo do General Pepper:
   4 linhas × 25 chars). Use `\n` literal para quebras.
3. **Grave o `.wav`** (32 kHz, mono, 16-bit PCM) em
   `ptbr_audio/<personagem>/<msgId>_<nome_curto>.wav`.
4. **Adicione no manifesto** (`ptbr_audio/voice_manifest.txt`):
   ```
   <msgId> | <letSeqRun> | ptbr_audio/<personagem>/<wav>
   ```
   - `letSeqRun = msgId` para chatter de rádio (preserva o clique).
   - `letSeqRun = -` para narrações, holograma do Pepper, cutscenes —
     nada de seq, ou a voz EN vaza por cima.
5. **Espelhe** `ptbr_audio/` para `build/x64/Release/ptbr_audio/`.
6. **Reempacote** o texto: `python tools/dub/pack_text_o2r.py`.
7. **Cheque órfãos:** `python tools/dub/find_orphan_wavs.py`.
8. **Teste em jogo.** Quando passar, marque `is_complete=yes` na linha
   correspondente do CSV.

## Próximos passos

### Curto prazo
- Concluir Meteo (faltam 22/42) e Sector Y (faltam 37/38).
- Gravar as 165 linhas que já têm `script_pt` mas não têm `.wav`.
- Definir voz para personagens ainda sem dublagem (Wolf, Leon, Pigma,
  Andrew, Bill, Katt, Andross, NPCs).
- Cortar uma release v0.2 com Corneria + Misc do Slippy completos.

### Médio prazo
- Fechar tradução (`script_pt`) das 557 linhas restantes.
- Gravar todo o resto da campanha — ordem sugerida segue a sequência
  natural de missões: Sector X, Aquas, Zoness, Macbeth, Solar, Bolse,
  Fortuna, Katina, Area 6, Sector Z, Titania, Venom 1, Venom 2.

### Distribuição
- Bundle pronto via `tools/dub/make_release.py`. Templates em
  `release-templates/README.md` e `release-templates/CREDITS.md`.
- Atualmente Windows-only enquanto o intercept usa `PlaySoundA`.

## Pendências de engenharia

### Áudio cross-platform (bloqueio para Linux/macOS)
`PlaySoundA` é Win32-only. Caminho recomendado: integrar com o backend
de áudio do `libultraship` (`AudioPlayerSDL.cpp` ou equivalente) — uma
única saída SDL compartilhada com a BGM, integração com volume mestre,
eventos de fade. Alternativa rápida: `SDL_mixer` (~5 linhas), sem
integração com o mixer do jogo.

### Hot-reload do manifesto (nice-to-have)
O manifesto carrega uma vez no primeiro `Audio_PlayVoice`. Uma tecla de
debug (ex.: F8) que recarregasse `voice_manifest.txt` aceleraria sessões
de gravação. ~20 linhas em `audio_general.c`.

### Patches do engine que valem upstream
- Os dois fixes em `audio_synthesis.c` descobertos durante a prova de
  conceito (typo `cmd++`/`aList++` na linha 1076; underflow `size_t` em
  `bytesToRead` na linha 1070, no caminho `CODEC_S16`) — independem da
  dublagem.
- A própria infraestrutura de manifesto + intercept de `Audio_PlayVoice` —
  é genérica e serviria para qualquer dublagem futura (espanhol, francês,
  legendas em japonês, etc.).

## Limitações conhecidas

| Item | Impacto |
|---|---|
| `PlaySoundA` é Win32-only | Builds Linux/macOS precisam de outro caminho |
| Uma WAV concorrente | `PlaySoundA` toca uma sample por vez; voz não dublada disparada durante uma dublada corta a anterior. Aceitável para cutscenes |
| Fonte do SF64 sem acentos | Texto em `script_pt` perde diacríticos no pack |
| Crash `sample_3310` | Bloqueia o caminho de substituição direta de sample (irrelevante para o intercept atual) |

## Referência rápida

### Arquivos principais
- `ptbr_audio/lines.csv` — inventário mestre (722 linhas, 8 colunas).
- `ptbr_audio/voice_manifest.txt` — roteamento `msgId → wav` (manual).
- `ptbr_audio/<personagem>/*.wav` — gravações pt-BR.
- `tools/dub/pack_text_o2r.py` — empacota texto a partir do CSV.
- `tools/dub/find_orphan_wavs.py` — alerta sobre `.wav` sem entrada
  no manifesto.
- `tools/dub/dump_messages.py` — descodifica entradas `gMsg_ID_<n>` de
  um `.o2r` para texto, útil para descobrir `msgId`s e validar pack.
- `tools/dub/make_release.py` — empacota o bundle final.
- `release-templates/README.md` + `release-templates/CREDITS.md` —
  textos do release zip.
- `src/audio/audio_general.c::Audio_PlayVoice` — intercept + carregador
  do manifesto.
- `src/audio/audio_playback.c::Audio_NoteInitForLayer` — supressão das
  notas de voz residuais.

### Caminhos do engine que ajudam
- `src/audio/audio_general.c:1850-1925` — `Audio_PlayVoice`,
  `Audio_UpdateVoice`, `Audio_GetCurrentVoice`.
- `src/engine/fox_message.c:6-22` — `Message_IdFromPtr` (msgPtr → msgId).
- `src/engine/fox_radio.c:128, 618` — disparo de voz pelo `Message_IdFromPtr`.
- `src/overlays/ovl_menu/fox_map.c:2583` — `Audio_PlayVoice(3)` explícito
  (cutscene do Pepper).
- `assets/yaml/us/rev1/ast_radio.yaml:101` — `gMsgLookup` (780 entradas).
- `tools/textconv.py:3-9` — tabela de glifos do SF64.

### Recursos externos
- Starship upstream: <https://github.com/HarbourMasters/Starship>
- Discord: <https://discord.com/invite/shipofharkinian>
