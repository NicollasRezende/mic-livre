# Redução de ruído opcional

O áudio básico funciona sem DeepFilterNet e sem Micstream. Para habilitar redução neural de ruído, use uma biblioteca C e um modelo compatíveis do projeto aberto [Rikorose/DeepFilterNet](https://github.com/Rikorose/DeepFilterNet), sob MIT/Apache-2.0.

A biblioteca deve exportar `df_create`, `df_get_frame_length`, `df_process_frame`, `df_set_atten_lim`, `df_set_post_filter_beta` e `df_free`. Usamos a [API C pública](https://github.com/Rikorose/DeepFilterNet/blob/main/libDF/src/capi.rs), com áudio mono a 48 kHz e quadros de 480 amostras. Nem todo pacote Python chamado `libdf` oferece essa API C.

Instale/compile os componentes seguindo as instruções do projeto de origem e coloque o par compatível em:

```text
~/.local/share/mic-livre/deepfilter/libdf.so
~/.local/share/mic-livre/deepfilter/DeepFilterNet3_onnx.tar.gz
```

`XDG_DATA_HOME` é respeitado. Também são procurados `/usr/local/lib/libdf.so` e `/usr/local/share/deepfilternet/DeepFilterNet3_onnx.tar.gz`. Para outros locais:

```sh
MICLIVRE_DF_LIB=/caminho/libdf.so \
MICLIVRE_DF_MODEL=/caminho/DeepFilterNet3_onnx.tar.gz \
./abrir-pc.sh
```

Como compatibilidade com computadores que já têm esses componentes abertos instalados, também reconhecemos o par em `/usr/lib/micstream/libdf.so` e `/usr/share/micstream/DeepFilterNet3_onnx.tar.gz`. Essa instalação não é necessária nem recomendada como requisito para usar Mic Livre.

Os componentes nativos não são baixados automaticamente nem incluídos no repositório. Use somente biblioteca e modelo compatíveis de origem confiável: a biblioteca é carregada no processo de áudio.

O filtro foi exercitado com o par compatível instalado no computador de desenvolvimento. O teste `test_noise_integration.py` processa áudio real pela API C e volta ao bypass. A qualidade perceptual deve ser comparada no seu aparelho. O filtro pode alterar a voz e introduzir atraso; ele fica desligado por padrão.
