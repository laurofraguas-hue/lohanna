#!/bin/bash
# gerar_todos.sh — regenera os 10 painéis a partir das fontes. Idempotente.
set -e
cd "$(dirname "$0")"

MOTIVO_DIVINOPOLIS="Neste município a coluna Votos_Candidato está em escala incompatível com o setor censitário: a mediana é de 387 votos por setor (contra 3 a 18 nos outros nove municípios) e o máximo, 747, se aproxima do eleitorado inteiro de um setor. As colunas Q1/Q2/Q3_Votos_Base estão na mesma escala inflada, o que indica que o bloco de votos do arquivo foi gerado em outra granularidade. Aguarda regeração do arquivo ou reconstrução a partir do TSE 2022 por seção."

# município | candidato | nº de urna 2024 | flags
gerar(){ echo "── $2 / $1"; python3 gerar_painel.py --municipio "$1" --candidato "$2" "${@:3}" | sed 's/^/   /'; }

gerar "Uberlândia"           "Fabão"                    --numero 43123
gerar "Belo Horizonte"       "Sara Vitral"              --numero 18018
gerar "São João Del-Rei"     "Sinara Campos"            --numero 43123
gerar "Divinópolis"          "Kell Silva"               --numero 43500 --suprimir-votos22 "$MOTIVO_DIVINOPOLIS"
gerar "Betim"                "Professor Gabriel Mendes" --sem-2024
gerar "Pará de Minas"        "Irene Melo Franco"        --sem-2024
gerar "Lagoa Santa"          "Marcelo Monteiro"         --sem-2024
gerar "Mariana"              "Pedro Sousa"              --sem-2024
gerar "Conselheiro Lafaiete" "Damires Rinarlly"         --sem-2024
gerar "Curvelo"              "Douglas Verissimo"        --sem-2024

echo
for f in dados/DATA_*.json; do python3 montar_painel.py --data "$f" | sed 's/^/   /'; done
