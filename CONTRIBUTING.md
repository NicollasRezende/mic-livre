# Contribuir

Mic Livre é gratuito, sem anúncios e licenciado sob GPL-3.0-only. Qualquer pessoa pode clonar, testar, modificar e abrir uma contribuição. O repositório oficial é mantido por revisão: ter acesso ao código não dá permissão de escrita na branch `main`.

1. Faça um fork e crie uma branch para sua mudança.
2. Explique o problema e mantenha a alteração focada.
3. Execute `python3 -m unittest discover -s tests -v`. Se alterar Android, execute também `./build-apk.sh` com SDK e JDK configurados.
4. Abra um Pull Request para `main`. No GitLab, o processo equivalente se chama Merge Request.
5. Um mantenedor revisa a contribuição. Corrija os comentários e aguarde a aprovação e os checks antes do merge.

As regras de proteção preparadas neste projeto exigem uma aprovação, testes Python, build Android e resolução das conversas. Administradores mantêm a possibilidade de intervenção. Elas só são aplicadas ao GitHub quando a publicação termina com sucesso.

Não inclua credenciais, chaves de assinatura, endereços de dispositivos, gravações pessoais nem caminhos da sua máquina. Os APKs em `apk/` são atualizados pelos mantenedores ao publicar uma versão; contribua com código-fonte, não com um APK modificado.

Ao enviar código, você autoriza sua distribuição sob GPL-3.0-only. Preserve os avisos de autoria e as licenças de componentes externos. Não copie código proprietário nem introduza anúncios, cobrança obrigatória, telemetria ou dependência de conta no aplicativo oficial.

Teste manual recomendado: pareamento, microfone virtual, ganho/mute, desconexão, reconexão e captura com a tela apagada. Informe aparelho, versão Android e distribuição Linux, removendo informações pessoais dos logs.
