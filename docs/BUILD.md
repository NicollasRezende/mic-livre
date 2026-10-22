# Compilar Android

Você não precisa compilar para usar: um APK assinado acompanha `apk/`. Compilar é útil para desenvolver ou instalar sua própria versão.

Requisitos gratuitos: Linux, JDK 17 ou superior, `zip`, Android SDK platform 36 e build-tools 35.0.0. Instale as ferramentas pela documentação oficial do [Android SDK](https://developer.android.com/tools). Se `sdkmanager` já estiver no PATH:

```sh
sdkmanager 'platforms;android-36' 'build-tools;35.0.0'
export ANDROID_HOME="$HOME/Android/Sdk"
./build-apk.sh
```

O script usa `JAVA_HOME`, se configurado; senão encontra o JDK pelo `javac` no PATH. O SDK é procurado em `ANDROID_HOME`, `ANDROID_SDK_ROOT` ou `~/Android/Sdk`. Ajuste esses valores à sua instalação. Não há caminhos pessoais no projeto.

O script roda sete verificações Java, compila as classes, gera DEX, empacota recursos, alinha e assina `dist/mic-livre.apk`. Não baixa dependências durante o build e não usa Gradle. Os APKs têm minSdk 26 (Android 8), targetSdk 35 e são compilados com platform 36.

Uma chave de desenvolvimento é criada em `build/development.p12`. Ela e a pasta de build são ignoradas pelo Git. A senha local `miclivre-dev` é pública por intenção e não deve ser usada como segredo de produção. Guarde sua chave para atualizar sua própria instalação.

Sua chave gerada não será a chave do APK oficial. O Android pode exigir desinstalar o APK oficial antes de instalar uma build sua, apagando suas preferências. As builds de CI também usam chaves de desenvolvimento próprias.

Mantenedores podem configurar uma chave existente por variáveis de ambiente:

```sh
export MICLIVRE_KEYSTORE=/caminho/seguro/assinatura.p12
export MICLIVRE_KEY_ALIAS=miclivre
# Defina MICLIVRE_KEYSTORE_PASSWORD no seu ambiente, sem incluí-la no Git.
./build-apk.sh
```

O build usa a senha via ambiente, não como texto interpolado na linha de comando. Não publique o keystore nem acrescente secrets às contribuições.
