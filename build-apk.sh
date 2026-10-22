#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

fail() { echo "Erro: $*" >&2; exit 1; }
# Use the caller's JDK, then javac from PATH. No developer-specific paths.
if [[ -n "${JAVA_HOME:-}" ]]; then
  build_java_home="$JAVA_HOME"
else
  javac_path="$(command -v javac || true)"
  [[ -n "$javac_path" ]] || fail 'JDK não encontrado. Instale Java 17+ e configure JAVA_HOME.'
  build_java_home="$(dirname "$(dirname "$(readlink -f "$javac_path")")")"
fi
[[ -x "$build_java_home/bin/javac" ]] || fail 'JAVA_HOME não aponta para um JDK com javac.'
export JAVA_HOME="$build_java_home"
export PATH="$JAVA_HOME/bin:$PATH"

sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
[[ -d "$sdk" ]] || fail 'SDK Android não encontrado. Configure ANDROID_HOME; consulte docs/BUILD.md.'
sdk="$(cd "$sdk" && pwd)"
tools="$sdk/build-tools/${ANDROID_BUILD_TOOLS:-35.0.0}"
jar="$sdk/platforms/android-${ANDROID_PLATFORM:-36}/android.jar"
[[ -f "$jar" ]] || fail "Plataforma ausente: $jar"
for executable in aapt d8 zipalign apksigner; do
  [[ -x "$tools/$executable" ]] || fail "Build-tool ausente: $tools/$executable"
done
command -v zip >/dev/null || fail 'Instale o utilitário zip.'
mkdir -p build dist
build_work="$(mktemp -d "$PWD/build/apk.XXXXXX")"
trap 'rm -rf "$build_work"' EXIT
mkdir -p "$build_work/classes" "$build_work/dex" "$build_work/tests"

javac --release 8 -Xlint:-options -d "$build_work/tests" android/src/br/com/miclivre/Wire.java tests/WireTest.java
java -cp "$build_work/tests" WireTest
javac --release 8 -Xlint:-options -d "$build_work/tests" android/src/br/com/miclivre/SampleEncoder.java tests/GainTest.java
java -cp "$build_work/tests" GainTest
javac -source 8 -target 8 -Xlint:-options -classpath "$jar" -d "$build_work/classes" android/src/br/com/miclivre/*.java
"$tools/aapt" package -f -M android/AndroidManifest.xml -S android/res -I "$jar" -F "$build_work/unsigned.apk"
mapfile -d '' class_files < <(find "$build_work/classes" -name '*.class' -print0)
"$tools/d8" --lib "$jar" --min-api 26 --output "$build_work/dex" "${class_files[@]}"
(cd "$build_work/dex" && zip -q ../unsigned.apk classes.dex)
"$tools/zipalign" -f 4 "$build_work/unsigned.apk" "$build_work/aligned.apk"

# The local development password is intentionally public; this is not a production key.
keystore="${MICLIVRE_KEYSTORE:-$PWD/build/development.p12}"
export MICLIVRE_KEYSTORE_PASSWORD="${MICLIVRE_KEYSTORE_PASSWORD:-miclivre-dev}"
key_alias="${MICLIVRE_KEY_ALIAS:-miclivre}"
if [[ ! -f "$keystore" ]]; then
  [[ -z "${MICLIVRE_KEYSTORE:-}" ]] || fail 'A chave de assinatura indicada não existe.'
  keytool -genkeypair -keystore "$keystore" -storetype PKCS12 \
    -storepass:env MICLIVRE_KEYSTORE_PASSWORD -keypass:env MICLIVRE_KEYSTORE_PASSWORD \
    -alias "$key_alias" -keyalg RSA -keysize 2048 -validity 3650 \
    -dname 'CN=Mic Livre Development' >/dev/null 2>&1
fi
"$tools/apksigner" sign --ks "$keystore" --ks-key-alias "$key_alias" \
  --ks-pass env:MICLIVRE_KEYSTORE_PASSWORD --out dist/mic-livre.apk "$build_work/aligned.apk"
"$tools/apksigner" verify --verbose dist/mic-livre.apk
echo 'APK criado: dist/mic-livre.apk'
