import os
import webbrowser
import threading
import requests
from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv

# Carrega o .env exatamente da pasta onde o app.py está salvo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

SPTRANS_TOKEN = os.getenv("SPTRANS_TOKEN", "").strip().strip('"').strip("'")
print(f"[DEBUG .ENV] Arquivo: {ENV_PATH} | Encontrado? {os.path.exists(ENV_PATH)} | Tamanho do token: {len(SPTRANS_TOKEN)} caracteres")

app = Flask(__name__)
BASE_URL = "http://api.olhovivo.sptrans.com.br/v2.1"

sptrans_session = requests.Session()
autenticado = False


def garantir_login():
    global autenticado
    if autenticado:
        return True
    if not SPTRANS_TOKEN:
        raise ValueError(f"SPTRANS_TOKEN vazio ou ausente em: {ENV_PATH}")

    resp = sptrans_session.post(
        f"{BASE_URL}/Login/Autenticar",
        params={"token": SPTRANS_TOKEN},
        timeout=10
    )
    resp.raise_for_status()
    autenticado = resp.json() is True
    return autenticado


@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))


@app.route("/api/olhovivo")
def olhovivo():
    global autenticado
    linha_filtro = request.args.get("linha", "").strip()
    sentido_filtro = request.args.get("sentido", "").strip()

    try:
        if not garantir_login():
            return jsonify({"error": "Token recusado pela SPTrans (verifique o valor no .env)."}), 401

        # 1. Busca os códigos internos (cl) da linha pelo letreiro base (ex: "4313-10" -> "4313")
        termo = linha_filtro.split("-")[0]
        r_busca = sptrans_session.get(
            f"{BASE_URL}/Linha/Buscar",
            params={"termosBusca": termo},
            timeout=10
        )

        # Renova o cookie caso a sessão da SPTrans tenha expirado
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

            # Filtra exatamente a linha e o sentido clicado (1 = Ida, 2 = Volta)
            if letreiro_completo == linha_filtro and (not sentido_filtro or sl == sentido_filtro):
                cl = item["cl"]
                destino = item.get("tp") if sl == "1" else item.get("ts")

                # 2. Consulta o GPS real apenas daquele sentido (cl)
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

        print(f"[SPTrans] Linha {linha_filtro} (Sentido {sentido_filtro}): {len(vehicles)} ônibus reais encontrados.")
        return jsonify({"vehicles": vehicles})

    except Exception as e:
        print(f"[ERRO SPTrans] {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)