# Arquitetura e protocolo v1

Android captura PCM; `MicService` envia dados em TCP. `ReceiverService` autentica, agrupa quadros de até 10 ms, aplica o DSP escolhido e alimenta um sink PulseAudio temporário com uma fonte remapeada. GTK e CLI compartilham o mesmo serviço e configurações. Não é necessário um servidor externo.

## Conexão TCP

Porta padrão: 45871, configurável. Cliente envia 16 bytes:

| Bytes | Campo |
| --- | --- |
| 0–3 | ASCII `MLV1` |
| 4–9 | Código de seis dígitos ASCII |
| 10–13 | Sample rate uint32 big-endian: 48000 |
| 14 | Canais uint8: 1 |
| 15 | Bits uint8: 16 |

O receptor responde `OKAY` quando a sessão está pronta. Conexões inválidas são fechadas e podem receber `FAIL`; o cliente não deve depender desse erro explícito.

Cada quadro começa com comprimento uint16 big-endian, seguido do PCM s16le. Tamanhos válidos: 2 a 960 bytes, pares. Quadros menores são agrupados no PC para o DSP. Não há codec com perdas, FEC, criptografia ou protocolo de reconexão nesta versão. A versão 0.2 mantém compatibilidade com o cliente 0.1.

## Descoberta UDP

O celular envia para UDP 45872 o texto `MICLIVRE_DISCOVER_V1 ` seguido de nonce ASCII alfanumérico/hífen, entre 6 e 48 caracteres. O PC responde em unicast com JSON:

```json
{"magic":"MICLIVRE1","nonce":"nonce-do-cliente","name":"meu-pc","port":45871,"busy":false,"version":"0.2.1"}
```

O cliente verifica magic, nonce e faixa de porta, ignora respostas malformadas e deduplica IP/porta. O código de pareamento não entra no anúncio. Essa descoberta identifica candidatos; não autentica o computador nem substitui uma rede confiável.

## DSP e encerramento

O caminho sem efeitos preserva os bytes PCM. Filtro de graves, DeepFilterNet, ganho e mute são opcionais. Saturação usa clamp, nunca wraparound. O processamento roda numa thread própria; as configurações são snapshots imutáveis.

Parar o receptor desbloqueia a conexão, encerra o playback e remove os módulos criados por ele. Escritas na saída e chamadas `pactl` têm timeout. O Android fecha socket, captura, efeitos e wake lock ao terminar a sessão. Metadados de nível/processamento não são uma medição da latência total.
