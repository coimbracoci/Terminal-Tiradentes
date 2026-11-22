# 🚌 Portal Terminal Cidade Tiradentes · Linhas & Olho Vivo

Aplicação web interativa para consulta das **27 linhas municipais** do **Terminal Cidade Tiradentes** (Zona Leste de São Paulo), combinando rastreamento GPS em tempo real via **API Olho Vivo (SPTrans)**, itinerários rua por rua, ranking de lotação, histórico do bairro e o **Tira** — um assistente virtual com painel de retreinamento ao vivo.

🔗 **Acesse o projeto online:** `https://seu-link-aqui.onrender.com`

---

## ✨ Funcionalidades

* **🗺️ Mapa ao Vivo (Estilo Olho Vivo SPTrans):**
  * Busca por código ou destino das linhas cadastradas no terminal.
  * Seleção de sentido (**Ida** ou **Volta**) antes de carregar o mapa.
  * Exibição da posição GPS real da frota sobre mapa interativo (**Leaflet + OpenStreetMap**) com atualização automática a cada **30 segundos**.
* **🤖 Chatbot "Tira" + Painel Dev em Tempo Real:**
  * Responde dúvidas sobre itinerários, linhas noturnas, ligações com Metrô/CPTM, ranking de lotação e história de Cidade Tiradentes.
  * **Anti-alucinação:** Pontuação ponderada com corte mínimo de confiança (*threshold*) para evitar respostas inventadas.
  * **Painel Dev:** Ajuste ao vivo dos pesos do algoritmo, correção direta de respostas com feedback negativo (`👎`) e exportação de histórico em `.csv`.
* **📋 Catálogo Completo e Itinerários:**
  * Filtro rápido por categoria (*Mais cheias*, *Metrô e trem*, *Terminais*, *Bairros* e *Noturnas*), identificação visual por área SPTrans e sistema de linhas favoritas (`localStorage`).
  * Gaveta lateral com itinerário detalhado rua por rua e opção de copiar o trajeto.
* **🌗 Interface Responsiva & Modo Escuro:**
  * Alternância entre tema claro e escuro com persistência local e adaptação para celulares e desktops.

---

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3, Flask, Requests, Python-Dotenv, Gunicorn
* **Frontend:** HTML5, CSS3 (Custom Properties / Grid / Flexbox), JavaScript (ES6+), Leaflet.js
* **APIs & Dados:** API Olho Vivo v2.1 (SPTrans), OpenStreetMap, dados públicos de operação e mobilidade urbana

---

## 📁 Estrutura do Projeto

```text
terminal-cidade-tiradentes/
├── app.py              # Servidor Flask e proxy autenticado para a API Olho Vivo
├── index.html          # Interface completa (catálogo, mapa Leaflet, chatbot Tira e Painel Dev)
├── requirements.txt    # Dependências Python para produção
├── .gitignore          # Proteção contra envio de arquivos sensíveis (.env e venv)
└── .env                # Variáveis de ambiente locais (não versionado)
