# Publicar o repositório oficial

Este documento é para mantenedores. Usuários não precisam de conta GitHub ou desta etapa para usar um clone público.

O script `./publicar-github.sh` usa o GitHub CLI autenticado no seu terminal para:

1. Conferir checkout limpo, branch `main`, tag `v0.2.1` e ausência de chaves rastreadas.
2. Criar `mic-livre` como repositório **público** na conta autenticada, sem sobrescrever outro `origin`.
3. Enviar o código e a tag; configurar merges por squash/rebase.
4. Proteger `main`: uma aprovação, checks `tests` e `android`, conversas resolvidas, sem force-push ou exclusão. Administradores mantêm possibilidade de intervenção.
5. Publicar o APK na release e verificar visibilidade pública, proteção, commit remoto e SHA-256 do APK publicado.
6. Mostrar os links reais retornados pelo GitHub.

Requer `git`, `gh` e acesso à rede. Para conferir o plano sem chamadas externas:

```sh
./publicar-github.sh --dry-run
```

Para publicar, depois de revisar os arquivos e executar os testes:

```sh
gh auth status
./publicar-github.sh
```

Se a autenticação não funcionar, use `gh auth login` no seu terminal. Não cole tokens em issues ou conversas. Um token com permissão para criar o repositório pode não ter permissão administrativa para proteger branches; nesse caso, o script para e preserva as etapas concluídas.

O script não torna um repo privado público, não force-pusha e não sobrescreve assets de releases. Se o nome já existir sem ser `origin` deste checkout, ele interrompe. Pode-se usar `--name outro-nome`; lembre de ajustar os links do README antes de publicar com outro nome/conta.

O APK oficial usa uma chave guardada fora do Git. O build de CI produz um APK de desenvolvimento com outra assinatura; não o substitua silenciosamente pelo oficial. Builds em `dist/` e todos os keystores estão ignorados. Os checks de GitHub Actions devem ser acompanhados na aba Actions após o push; a configuração local de CI não prova que eles já passaram remotamente.
