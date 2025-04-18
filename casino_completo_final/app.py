import json
import os
import random
from flask import Flask, render_template, request, redirect, session, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # clave secreta para sesiones (cambiar en producción)

# Define conjuntos de números rojos y negros para la ruleta (0 es verde)
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# Archivo local para almacenar usuarios
USER_DATA_FILE = 'users.json'

def load_users():
    """Carga los datos de usuarios desde el archivo JSON."""
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, 'r') as f:
            data = json.load(f)
            # Si la estructura es una lista, convertir a dict
            if isinstance(data, list):
                users = {}
                for u in data:
                    if 'username' in u:
                        users[u['username']] = {
                            "password": u.get("password", ""),
                            "balance": u.get("balance", 1000)
                        }
                return users
            elif isinstance(data, dict):
                return data
            else:
                return {}
    except json.JSONDecodeError:
        return {}

def save_users(users):
    """Guarda los datos de usuarios en el archivo JSON."""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f)

@app.route('/')
def index():
    # Redirige a menú si está autenticado, si no, a login
    if 'username' in session:
        return redirect(url_for('menu'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        if username in users and users[username]['password'] == password:
            # Inicio de sesión exitoso
            session['username'] = username
            session['balance'] = users[username].get('balance', 1000)
            return redirect(url_for('menu'))
        else:
            error = "Nombre de usuario o contraseña incorrectos."
            return render_template('login.html', error=error)
    else:
        # Si ya está logueado, ir al menú directamente
        if 'username' in session:
            return redirect(url_for('menu'))
        return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Validación básica
        if not username or not password:
            error = "Por favor ingrese un nombre de usuario y contraseña."
            return render_template('registro.html', error=error)
        users = load_users()
        if username in users:
            error = "El nombre de usuario ya existe. Elija otro."
            return render_template('registro.html', error=error)
        # Registrar nuevo usuario
        users[username] = {"password": password, "balance": 1000}
        save_users(users)
        # Redirigir a la página de login después de registro exitoso
        return redirect(url_for('login'))
    else:
        if 'username' in session:
            return redirect(url_for('menu'))
        return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/menu')
def menu():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    balance = session.get('balance', 0)
    return render_template('menu.html', username=username, balance=balance)

@app.route('/ruleta')
def ruleta():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    balance = session.get('balance', 0)
    # Pasamos también los números rojos y negros para colorear el tablero en la plantilla
    return render_template('ruleta.html', username=username, balance=balance,
                        red_numbers=list(RED_NUMBERS), black_numbers=list(BLACK_NUMBERS))

@app.route('/ruleta/spin', methods=['POST'])
def ruleta_spin():
    if 'username' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json()
    if not data or 'bets' not in data:
        return jsonify({"error": "No hay apuestas"}), 400
    bets = data['bets']
    if not bets:
        return jsonify({"error": "No hay apuestas"}), 400
    # Resultado aleatorio de 0 a 36
    result = random.randint(0, 36)
    # Determinar color del resultado
    if result == 0:
        result_color = "verde"
    elif result in RED_NUMBERS:
        result_color = "rojo"
    elif result in BLACK_NUMBERS:
        result_color = "negro"
    else:
        result_color = ""
    # Calcular ganancias/pérdidas
    total_bet = 0
    total_win = 0
    for bet in bets:
        num = bet.get('number')
        amt = bet.get('amount', 0)
        if num is None or amt is None:
            continue
        total_bet += amt
        if num == result:
            # Pago 35 a 1 por acierto (ganancia neta 35 * apuesta)
            total_win += amt * 35
    current_balance = session.get('balance', 0)
    new_balance = current_balance - total_bet + total_win
    # Actualizar saldo en sesión y almacenamiento
    session['balance'] = new_balance
    users = load_users()
    username = session.get('username')
    if username and username in users:
        users[username]['balance'] = new_balance
        save_users(users)
    net_change = new_balance - current_balance
    return jsonify({
        "result": result,
        "color": result_color,
        "new_balance": new_balance,
        "net_change": net_change
    })

def calculate_hand_total(cards):
    """Calcula el valor total de una mano de blackjack dada una lista de cartas."""
    total = 0
    aces = 0
    for card in cards:
        if card == 'A':
            total += 11
            aces += 1
        elif card in ['J', 'Q', 'K']:
            total += 10
        else:
            try:
                total += int(card)
            except:
                total += 0
    # Ajustar valores de Ases si el total se pasa de 21
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

@app.route('/blackjack', methods=['GET', 'POST'])
def blackjack():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    if request.method == 'POST':
        action = request.form.get('action')
        if action is None or action == 'deal':
            # Iniciar una nueva ronda de Blackjack
            try:
                bet = int(request.form.get('bet', '0'))
            except:
                bet = 0
            if bet <= 0:
                error = "Ingrese una apuesta válida."
                return render_template('blackjack.html', username=username, balance=session.get('balance', 0), error=error)
            if bet > session.get('balance', 0):
                error = "Saldo insuficiente para esa apuesta."
                return render_template('blackjack.html', username=username, balance=session.get('balance', 0), error=error)
            # Crear y barajar un nuevo mazo de cartas
            ranks = [str(n) for n in range(2, 11)] + ['J', 'Q', 'K', 'A']
            deck = []
            for r in ranks:
                for _ in range(4):
                    deck.append(r)
            random.shuffle(deck)
            # Repartir cartas iniciales
            player_cards = [deck.pop(), deck.pop()]
            dealer_cards = [deck.pop(), deck.pop()]
            # Guardar estado del juego en la sesión
            session['bj_deck'] = deck
            session['bj_player'] = player_cards
            session['bj_dealer'] = dealer_cards
            session['bj_bet'] = bet
            session['bj_active'] = True
            # Mostrar la vista del juego (cartas del jugador y una carta del crupier visible, otra oculta)
            player_total = calculate_hand_total(player_cards)
            dealer_visible = [dealer_cards[0]]
            dealer_total = calculate_hand_total(dealer_visible)
            return render_template('blackjack.html', username=username, balance=session.get('balance', 0),
                                player_cards=player_cards, dealer_cards=dealer_visible,
                                player_total=player_total, dealer_total=dealer_total,
                                game_active=True)
        elif action == 'hit':
            # El jugador pide otra carta (Hit)
            if not session.get('bj_active'):
                return redirect(url_for('blackjack'))
            deck = session.get('bj_deck', [])
            player_cards = session.get('bj_player', [])
            dealer_cards = session.get('bj_dealer', [])
            bet = session.get('bj_bet', 0)
            if not deck or player_cards is None or dealer_cards is None or bet is None:
                # Si falta información, reiniciar juego
                return redirect(url_for('blackjack'))
            # Dar una carta adicional al jugador
            player_cards.append(deck.pop())
            session['bj_deck'] = deck
            session['bj_player'] = player_cards
            player_total = calculate_hand_total(player_cards)
            if player_total > 21:
                # El jugador se pasa de 21 (pierde automáticamente la ronda)
                balance = session.get('balance', 0)
                new_balance = balance - bet  # restar apuesta
                session['balance'] = new_balance
                users = load_users()
                if username in users:
                    users[username]['balance'] = new_balance
                    save_users(users)
                # Preparar mensaje de resultado (jugador pierde)
                outcome = f"Te pasaste de 21. Pierdes {bet} fichas."
                dealer_total = calculate_hand_total(dealer_cards)
                # Revelar las cartas del crupier porque la ronda terminó
                session.pop('bj_active', None)
                session.pop('bj_deck', None)
                session.pop('bj_player', None)
                session.pop('bj_dealer', None)
                session.pop('bj_bet', None)
                return render_template('blackjack.html', username=username, balance=new_balance,
                                    player_cards=player_cards, dealer_cards=dealer_cards,
                                    player_total=player_total, dealer_total=dealer_total,
                                    outcome=outcome, game_active=False)
            # Si el jugador no se pasó de 21, continúa el juego
            dealer_visible = [dealer_cards[0]]
            dealer_total = calculate_hand_total(dealer_visible)
            return render_template('blackjack.html', username=username, balance=session.get('balance', 0),
                                player_cards=player_cards, dealer_cards=dealer_visible,
                                player_total=player_total, dealer_total=dealer_total,
                                game_active=True)
        elif action == 'stand':
            if not session.get('bj_active'):
                return redirect(url_for('blackjack'))
            deck = session.get('bj_deck', [])
            player_cards = session.get('bj_player', [])
            dealer_cards = session.get('bj_dealer', [])
            bet = session.get('bj_bet', 0)
            if player_cards is None or dealer_cards is None:
                return redirect(url_for('blackjack'))
            # El crupier revela su carta oculta y pide cartas hasta sumar al menos 17
            dealer_total = calculate_hand_total(dealer_cards)
            while dealer_total < 17 and deck:
                dealer_cards.append(deck.pop())
                dealer_total = calculate_hand_total(dealer_cards)
            player_total = calculate_hand_total(player_cards)
            # Determinar resultado de la ronda
            outcome = ""
            balance = session.get('balance,', session.get('balance', 0))
            balance = session.get('balance', 0)  # corregir obtención de saldo actual
            new_balance = balance
            if dealer_total > 21:
                # El crupier se pasa de 21, gana el jugador
                outcome = f"¡El crupier se pasó de 21! Ganaste {bet} fichas."
                new_balance = balance + bet
            elif player_total > dealer_total:
                outcome = f"¡Ganaste! Ganaste {bet} fichas."
                new_balance = balance + bet
            elif player_total < dealer_total:
                outcome = f"El crupier gana. Pierdes {bet} fichas."
                new_balance = balance - bet
            else:
                outcome = "Empate. Recuperas tu apuesta."
                # new_balance permanece igual
            session['balance'] = new_balance
            users = load_users()
            if username in users:
                users[username]['balance'] = new_balance
                save_users(users)
            # Limpiar el estado de juego almacenado en sesión
            session.pop('bj_active', None)
            session.pop('bj_deck', None)
            session.pop('bj_player', None)
            session.pop('bj_dealer', None)
            session.pop('bj_bet', None)
            return render_template('blackjack.html', username=username, balance=new_balance,
                                player_cards=player_cards, dealer_cards=dealer_cards,
                                player_total=player_total, dealer_total=dealer_total,
                                outcome=outcome, game_active=False)
    # GET: mostrar página inicial de blackjack (formulario de apuesta)
    return render_template('blackjack.html', username=username, balance=session.get('balance', 0))
if __name__ == '__main__':
    app.run(debug=True)
