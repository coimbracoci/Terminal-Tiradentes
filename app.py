import os
import hashlib
from datetime import date
import time
import requests
from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

SPTRANS_TOKEN = os.getenv("SPTRANS_TOKEN", "").strip().strip('"').strip("'")

app = Flask(__name__)
BASE_URL = "http://api.olhovivo.sptrans.com.br/v2.1"

# Whitelist estrita: apenas as 27 linhas do Terminal Cidade Tiradentes são aceitas
LINHAS_PERMITIDAS = {
    "3013-10", "3019-10", "3064-10", "3064-41", "312N-10", "3539-10",
    "3785-10", "3787-10", "3789-10", "4004-10", "4005-10", "4017-10",
    "4018-10", "407L-10", "407N-10", "407P-10", "4086-10", "4092-10",
    "4093-10", "4210-10", "4313-10", "N403-11", "N406-11", "N435-11",
    "N436-11", "N437-11", "N441-11"
}

sptrans_session = requests.Session()
autenticado = False

# Cache em memória para proteger seu token SPTrans contra múltiplos acessos simultâneos
CACHE_GPS = {}
CACHE_TTL = 15  # segundos


def garantir_login():
    global autenticado
    if autenticado:
        return True
    if not SPTRANS_TOKEN:
        raise ValueError("SPTRANS_TOKEN não configurado no servidor.")

    resp = sptrans_session.post(
        f"{BASE_URL}/Login/Autenticar",
        params={"token": SPTRANS_TOKEN},
        timeout=10
    )
    resp.raise_for_status()
    autenticado = resp.json() is True
    return autenticado


@app.after_request
def adicionar_cabecalhos_seguranca(response):
    # Protege contra Clickjacking (impede que coloquem seu site dentro de um iframe malicioso)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Impede o navegador de adivinhar tipos de arquivo perigosos
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


VISITAS_STATS = {
    "inicio_servidor": time.strftime("%d/%m/%Y às %H:%M"),
    "total_aberturas": 0,
    "visitantes_unicos_hoje": set(),
    "data_atual": date.today().isoformat(),
}


def registrar_visita(req):
    hoje = date.today().isoformat()
    if VISITAS_STATS["data_atual"] != hoje:
        VISITAS_STATS["data_atual"] = hoje
        VISITAS_STATS["visitantes_unicos_hoje"].clear()

    VISITAS_STATS["total_aberturas"] += 1

    # Gera um identificador anônimo (hash) para contar visitante único no dia sem salvar IP bruto
    ip = req.headers.get("X-Forwarded-For", req.remote_addr or "anon").split(",")[0].strip()
    ua = req.headers.get("User-Agent", "")
    visitor_hash = hashlib.sha256(f"{hoje}:{ip}:{ua}".encode()).hexdigest()[:16]
    VISITAS_STATS["visitantes_unicos_hoje"].add(visitor_hash)


@app.route("/api/visitas")
def visitas():
    return jsonify({
        "aberturas": VISITAS_STATS["total_aberturas"],
        "unicos_hoje": len(VISITAS_STATS["visitantes_unicos_hoje"]),
        "desde": VISITAS_STATS["inicio_servidor"]
    })


@app.route("/")
def index():
    registrar_visita(request)
    return send_file(os.path.join(BASE_DIR, "index.html"))


@app.route("/api/olhovivo")
def olhovivo():
    global autenticado
    linha_filtro = request.args.get("linha", "").strip().upper()
    sentido_filtro = request.args.get("sentido", "").strip()

    # 1. Bloqueia qualquer linha fora do Terminal Cidade Tiradentes ou sentido inválido
    if linha_filtro not in LINHAS_PERMITIDAS:
        return jsonify({"error": "Linha não autorizada ou inválida."}), 400
    if sentido_filtro not in {"1", "2"}:
        return jsonify({"error": "Sentido inválido (use 1 ou 2)."}), 400

    # 2. Verifica se já existe resposta recente no cache (menos de 15s)
    chave_cache = f"{linha_filtro}:{sentido_filtro}"
    agora = time.time()
    if chave_cache in CACHE_GPS:
        dados_salvos, timestamp = CACHE_GPS[chave_cache]
        if agora - timestamp < CACHE_TTL:
            return jsonify({"vehicles": dados_salvos, "cached": True})

    try:
        if not garantir_login():
            return jsonify({"error": "Falha de autenticação com a SPTrans."}), 401

        termo = linha_filtro.split("-")[0]
        r_busca = sptrans_session.get(
            f"{BASE_URL}/Linha/Buscar",
            params={"termosBusca": termo},
            timeout=10
        )

        if r_busca.status_code == 401:
            autenticado = False
            garantir_login()
            r_busca = sptrans_session.get(
                f"{BASE_URL}/Linha/Buscar",
                params={"termosBusca": termo},
                timeout=10
            )

        r_busca.raise_for_status()
        linhas_encontradas = r_busca.json()

        vehicles = []
        for item in linhas_encontradas:
            letreiro_completo = f"{item.get('lt')}-{item.get('tl')}"
            sl = str(item.get("sl", ""))

            if letreiro_completo == linha_filtro and sl == sentido_filtro:
                cl = item["cl"]
                destino = item.get("tp") if sl == "1" else item.get("ts")

                r_pos = sptrans_session.get(
                    f"{BASE_URL}/Posicao/Linha",
                    params={"codigoLinha": cl},
                    timeout=10
                )
                r_pos.raise_for_status()
                dados_pos = r_pos.json()

                for v in dados_pos.get("vs", []):
                    vehicles.append({
                        "linha": linha_filtro,
                        "sentido": sl,
                        "p": v.get("p"),
                        "py": v.get("py"),
                        "px": v.get("px"),
                        "ta": v.get("ta"),
                        "destino": destino or ""
                    })

        # Salva no cache por 15 segundos
        CACHE_GPS[chave_cache] = (vehicles, agora)
        return jsonify({"vehicles": vehicles})

    except Exception:
        # Não vaza detalhes internos do servidor (stack trace) para o usuário
        return jsonify({"error": "Serviço temporariamente indisponível."}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)