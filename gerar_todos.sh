#!/bin/bash
# gerar_todos.sh — regenera os 10 painéis a partir das fontes. Idempotente.
#
# Pré-requisito (uma vez por sessão, ver PROGRESSO.md):
#   gdown dos .zip do TSE para dados/bruto/
#   python3 filtrar_bruto.py --ano 2024 && python3 filtrar_bruto.py --ano 2022
#   python3 geo_locais.py --ano 2024   && python3 geo_locais.py --ano 2022
#   python3 agregar_2024.py            && python3 agregar_2022.py
#   python3 preparar_malhas.py   (malha de bairros dos 10, a partir dos setores)
set -e
cd "$(dirname "$0")"

# município | candidato | nº de urna 2024 | flags
gerar(){ echo "── $2 / $1"; python3 gerar_painel.py --municipio "$1" --candidato "$2" "${@:3}" | sed 's/^/   /'; }

gerar "Uberlândia"           "Fabão"                    --numero 43123
gerar "Belo Horizonte"       "Sara Vitral"              --numero 18018
gerar "São João Del-Rei"     "Sinara Campos"            --numero 43123
gerar "Divinópolis"          "Kell Silva"               --numero 43500
gerar "Pará de Minas"        "Irene Melo Franco"        --numero 43222
gerar "Lagoa Santa"          "Marcelo Monteiro"         --numero 43000
gerar "Mariana"              "Pedro Sousa"              --numero 43444
gerar "Conselheiro Lafaiete" "Damires Rinarlly"         --numero 43633
gerar "Curvelo"              "Douglas Verissimo"        --numero 43050
# Gabriel Mendes não disputou 2024: painel de camada única, a seção de 2024 é omitida.
gerar "Betim"                "Professor Gabriel Mendes" --sem-2024

echo
for f in dados/DATA_*.json; do python3 montar_painel.py --data "$f" | sed 's/^/   /'; done
