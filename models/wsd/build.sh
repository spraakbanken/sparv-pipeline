#!/usr/bin/env bash

echo "Downloading wsd models from GitHub"
wget -N https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/ALL_512_128_w10_A2_140403_ctx1.bin -P wsd/
wget -N https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/lem_cbow0_s512_w10_NEW2_ctx.bin -P wsd/
