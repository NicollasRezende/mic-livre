# Mic Livre

Use seu celular Android como microfone do PC Linux, com áudio local sem compressão.
**Gratuito, código aberto e sem anúncios. Sem conta, assinatura, nuvem ou pagamento para usar.**

O código está sob **GPL-3.0-only**. Qualquer pessoa pode clonar, testar, modificar e distribuir seguindo a licença. Para alterar o projeto oficial, envie um **Pull Request** — equivalente a um Merge Request — e aguarde revisão. [Como contribuir](CONTRIBUTING.md).

## Começar

No PC Linux:

```sh
git clone https://github.com/NicollasRezende/mic-livre.git
cd mic-livre
./setup-linux.sh
./abrir-pc.sh
```

Se o verificador indicar dependências faltando, no Ubuntu, Debian ou Mint:

```sh
./setup-linux.sh --install --desktop
./abrir-pc.sh
```

Isso instala pacotes gratuitos do sistema e cria um atalho no menu. Não altera o microfone padrão nem configura um serviço que inicia com o sistema. A janela inicia o receptor quando é aberta; feche uma instância anterior antes de abrir outra.

No celular, instale o APK **já incluído neste clone**, em `apk/mic-livre-0.2.1.apk`. Não é necessário instalar SDK Android ou compilar. Transfira o arquivo ao celular e abra-o, ou, com depuração USB autorizada:

```sh
adb install -r apk/mic-livre-0.2.1.apk
```

O APK também pode ser baixado na seção **Releases** do repositório depois da publicação da versão.

## Conectar

1. Mantenha a janela do PC aberta e os dois dispositivos na mesma rede Wi-Fi.
2. No app, toque em **Buscar computadores** e escolha seu PC.
3. Digite o código de seis dígitos mostrado na janela do PC e toque em **Iniciar microfone**.
4. Permita o acesso ao microfone. No Discord, OBS ou programa de voz, selecione **Mic Livre** / `Mic_Livre` como entrada.

O microfone virtual aparece após uma conexão autenticada. O botão **Parar** no app ou na notificação encerra a captura. Mute transmite silêncio e mantém o acesso ao microfone.

Se a descoberta falhar, use **Conexão manual**: endereço IPv4 do PC, porta TCP `45871` e código mostrado na janela. `hostname -I` ajuda a encontrar o IP; evite endereços de Docker, VPN e máquinas virtuais. A descoberta usa UDP `45872`. Permita essas portas somente na rede local, se houver firewall. Redes de convidados e isolamento entre dispositivos podem bloquear conexão.

## Controles

| PC | Celular |
| --- | --- |
| Código, conexão e medidor de saída | Busca automática e conexão manual |
| Ganho de -24 a +24 dB e mute | Ganho de -12 a +24 dB e mute |
| Filtro opcional de graves a 80 Hz | Medidor e contador de saturação |
| DeepFilterNet opcional | Modos fidelidade, voz, chamada e microfone |
| Buffer de 20 a 200 ms | Captura em serviço com notificação |

Ganho, mute e filtros do PC mudam ao vivo. Reconecte o celular para aplicar buffer; reinicie o receptor para mudar a porta. A fonte do celular só muda antes de conectar.

Para preservar a captura, comece com **Fidelidade**, **ganho 0 dB** e filtros desligados. O modo tenta `UNPROCESSED` quando o aparelho declara suporte; caso contrário, usa reconhecimento de voz. O fabricante pode manter processamento interno. Aumentar ganho, frequência ou número de bits não melhora por si só o microfone do aparelho.

DeepFilterNet pode reduzir ruído, mas também alterar a voz e acrescentar atraso. Compare ligado/desligado. Ele é opcional e **não exige instalar Micstream**: [configuração independente](docs/DEEPFILTER.md). Sem ele, o restante do aplicativo continua funcionando.

## Requisitos

- PC Linux com Python 3.10+, GTK3/PyGObject e PipeWire com `pipewire-pulse`, ou PulseAudio.
- Utilitários `pactl` e `pacat`, fornecidos por `pulseaudio-utils` no Debian/Ubuntu/Mint.
- Android 8 ou superior, com microfone.
- Mesma rede local. Não há servidor externo.

Em outras distribuições, instale os pacotes equivalentes de Python, PyGObject/GTK3 e utilitários PulseAudio. A instalação automática só cobre a família Debian/Ubuntu/Mint. Windows, macOS e iOS ainda não são suportados pelo receptor/app.

## Privacidade e limites

- PCM mono 48 kHz, 16 bits, aproximadamente 768 kbit/s antes dos cabeçalhos.
- Áudio e código de pareamento **não são criptografados**. Use uma rede confiável e não exponha as portas à internet. A descoberta não divulga o código.
- Transporte TCP preserva os dados; interferência pode causar pausas e atraso. O buffer mostrado é uma configuração da saída, não uma medição do atraso total.
- Um celular por receptor. Não há reconexão automática nem descoberta pela internet.
- Sem gravação no uso normal. A opção de diagnóstico `--output` grava no arquivo que você indicar e o substitui a cada sessão.
- O serviço Android mantém a captura com notificação; restrições de bateria variam conforme o fabricante.

A versão inicial teve conexão e qualidade confirmadas pelo usuário em um Moto G34 com Linux Mint/PipeWire. Testes automatizados cobrem protocolo, DSP e configuração; build e assinatura do APK são verificados. A interface nova, descoberta automática e funcionamento com tela apagada ainda precisam de validação em mais aparelhos. Não há promessa de atraso ou melhora perceptual sem medição no dispositivo.

## Desenvolvimento

```sh
python3 -m unittest discover -s tests -v
```

Não são necessárias dependências PyPI para os testes centrais. O teste de integração DeepFilterNet é pulado quando biblioteca/modelo não estão instalados. Para compilar seu próprio APK, consulte [docs/BUILD.md](docs/BUILD.md). [Arquitetura e protocolo](docs/PROTOCOL.md).

Receptor sem janela:

```sh
./iniciar-pc.sh
./iniciar-pc.sh --help
```

Preferências do PC: `~/.config/mic-livre/settings.json`, respeitando `XDG_CONFIG_HOME`.

## Licença e contribuição

Veja [LICENSE](LICENSE), [NOTICE](NOTICE), [CONTRIBUTING.md](CONTRIBUTING.md) e [SECURITY.md](SECURITY.md).
O projeto oficial não tem anúncios, cobrança obrigatória ou recursos pagos. Licença aberta e revisão de PRs são coisas diferentes: você pode usar seu clone sem pedir permissão; a integração de mudanças no repositório oficial depende dos mantenedores.

Mic Livre é independente de Micstream e não inclui seu código proprietário. Os filtros opcionais usam a API pública do projeto aberto [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet).
