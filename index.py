import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json

app = Flask(__name__)
app.secret_key = 'vhl_secret_key_2026_adminBHL_2026'
app.config['DATABASE'] = 'vhl_database.db'

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Администраторы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Команды
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Игроки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            number INTEGER,
            position TEXT,
            team_id INTEGER,
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    ''')
    
    # Матчи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            team1_id INTEGER NOT NULL,
            team2_id INTEGER NOT NULL,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            date_time TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            period INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team1_id) REFERENCES teams (id),
            FOREIGN KEY (team2_id) REFERENCES teams (id)
        )
    ''')
    
    # Голы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY,
            match_id INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            period INTEGER,
            time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем стандартного админа
    cursor.execute("SELECT * FROM admins WHERE username = 'adminBHL'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin2026BHL')
        cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", 
                      ('adminBHL', hashed_pw))
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# ==================== HTML ШАБЛОНЫ ====================
BASE_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ВХЛ - Восточная хоккейная лига</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Arial', sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
        }
        
        .header {
            background: #111111;
            padding: 20px 0;
            border-bottom: 3px solid #ffffff;
            text-align: center;
        }
        
        .logo {
            font-size: 36px;
            font-weight: bold;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 3px;
        }
        
        .subtitle {
            font-size: 18px;
            color: #cccccc;
            margin-top: 10px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        
        .section-title {
            font-size: 28px;
            color: #ffffff;
            margin-bottom: 30px;
            text-align: center;
            padding-bottom: 10px;
            border-bottom: 2px solid #ffffff;
        }
        
        .matches-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 50px;
        }
        
        .match-card {
            background: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .match-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(255, 255, 255, 0.1);
            border-color: #ffffff;
        }
        
        .match-status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 15px;
            text-transform: uppercase;
        }
        
        .status-scheduled { background: #666666; color: white; }
        .status-live { 
            background: #ff0000; 
            color: white;
            animation: pulse 1.5s infinite;
        }
        .status-period { background: #ff9900; color: white; }
        .status-finished { background: #333333; color: #cccccc; }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .teams {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 20px 0;
        }
        
        .team {
            text-align: center;
            flex: 1;
            cursor: pointer;
        }
        
        .team:hover .team-name {
            color: #ffffff;
        }
        
        .team-name {
            font-size: 20px;
            font-weight: bold;
            color: #eeeeee;
            margin-bottom: 5px;
        }
        
        .team-city {
            font-size: 14px;
            color: #999999;
        }
        
        .vs {
            font-size: 18px;
            color: #ffffff;
            font-weight: bold;
            margin: 0 20px;
        }
        
        .score {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            color: #ffffff;
        }
        
        .match-time {
            text-align: center;
            color: #999999;
            font-size: 14px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #333333;
        }
        
        .match-controls {
            margin-top: 15px;
            text-align: center;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            margin: 3px;
            font-weight: bold;
            text-transform: uppercase;
            transition: all 0.3s;
        }
        
        .btn-start { background: #00aa00; color: white; }
        .btn-start:hover { background: #00cc00; }
        
        .btn-pause { background: #ff9900; color: white; }
        .btn-pause:hover { background: #ffaa00; }
        
        .btn-resume { background: #0099ff; color: white; }
        .btn-resume:hover { background: #00aaff; }
        
        .btn-finish { background: #ff0000; color: white; }
        .btn-finish:hover { background: #ff3333; }
        
        .btn-delete { background: #990000; color: white; }
        .btn-delete:hover { background: #cc0000; }
        
        .btn-score { background: #6666ff; color: white; }
        .btn-score:hover { background: #8888ff; }
        
        .btn-goal { background: #00cc00; color: white; }
        .btn-goal:hover { background: #00ee00; }
        
        .footer {
            background: #111111;
            padding: 40px 0;
            margin-top: 50px;
            border-top: 3px solid #ffffff;
        }
        
        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .footer-logo {
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
        }
        
        .login-btn {
            padding: 12px 30px;
            background: transparent;
            color: #ffffff;
            border: 2px solid #ffffff;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .login-btn:hover {
            background: #ffffff;
            color: #000000;
        }
        
        .logout-btn {
            padding: 12px 30px;
            background: #ff0000;
            color: #ffffff;
            border: none;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .logout-btn:hover {
            background: #cc0000;
        }
        
        /* Модальные окна */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal-content {
            background: #1a1a1a;
            padding: 30px;
            border-radius: 10px;
            border: 2px solid #ffffff;
            width: 90%;
            max-width: 400px;
        }
        
        .modal-title {
            color: #ffffff;
            margin-bottom: 20px;
            text-align: center;
            font-size: 24px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            color: #cccccc;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        .form-input {
            width: 100%;
            padding: 12px;
            background: #333333;
            border: 1px solid #666666;
            border-radius: 5px;
            color: #ffffff;
            font-size: 16px;
        }
        
        .form-select {
            width: 100%;
            padding: 12px;
            background: #333333;
            border: 1px solid #666666;
            border-radius: 5px;
            color: #ffffff;
            font-size: 16px;
        }
        
        .modal-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .btn-confirm {
            flex: 1;
            padding: 12px;
            background: #00aa00;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .btn-cancel {
            flex: 1;
            padding: 12px;
            background: #666666;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
        }
        
        /* Форма входа */
        .login-form {
            max-width: 400px;
            margin: 100px auto;
            background: #1a1a1a;
            padding: 40px;
            border-radius: 10px;
            border: 2px solid #ffffff;
        }
        
        .login-title {
            color: #ffffff;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }
        
        .error {
            color: #ff6666;
            text-align: center;
            margin-bottom: 20px;
            padding: 10px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 5px;
        }
        
        /* Админ панель */
        .admin-panel {
            background: #1a1a1a;
            padding: 30px;
            border-radius: 10px;
            border: 2px solid #ffffff;
            margin-top: 30px;
        }
        
        .admin-section {
            margin-bottom: 40px;
        }
        
        .admin-title {
            color: #ffffff;
            font-size: 22px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333333;
        }
        
        /* Состав команды */
        .squad-modal {
            max-width: 500px;
        }
        
        .player-card {
            background: #333333;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .player-info {
            flex: 1;
        }
        
        .player-name {
            font-weight: bold;
            font-size: 16px;
            color: #ffffff;
        }
        
        .player-details {
            color: #999999;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .player-stats {
            text-align: right;
            color: #00cc00;
            font-weight: bold;
        }
        
        .no-players {
            text-align: center;
            color: #999999;
            padding: 20px;
        }
    </style>
</head>
<body>
    <!-- Хедер -->
    <header class="header">
        <div>
            <div class="logo">ВХЛ</div>
            <div class="subtitle">Восточная хоккейная лига</div>
        </div>
    </header>

    <!-- Основной контент -->
    <main class="container">
        {{ content|safe }}
    </main>

    <!-- Футер -->
    <footer class="footer">
        <div class="footer-content">
            <div class="footer-logo">ВХЛ</div>
            {{ login_button|safe }}
        </div>
    </footer>

    <!-- Модальные окна -->
    <div id="modals">
        {{ modals|safe }}
    </div>

    <script>
        {{ script|safe }}
    </script>
</body>
</html>'''

# ==================== РОУТЫ ====================
@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем матчи
    cursor.execute('''
        SELECT m.*, 
               t1.name as team1_name, t1.city as team1_city,
               t2.name as team2_name, t2.city as team2_city
        FROM matches m
        LEFT JOIN teams t1 ON m.team1_id = t1.id
        LEFT JOIN teams t2 ON m.team2_id = t2.id
        ORDER BY m.date_time DESC
    ''')
    matches = cursor.fetchall()
    
    conn.close()
    
    # Создаем HTML для матчей
    matches_html = '<h2 class="section-title">Расписание матчей ВХЛ</h2>'
    
    if matches:
        matches_html += '<div class="matches-grid">'
        for match in matches:
            status_class = f"status-{match['status']}"
            status_text = {
                'scheduled': 'Запланирован',
                'live': 'В прямом эфире',
                'period': 'Перерыв',
                'finished': 'Завершен'
            }.get(match['status'], match['status'])
            
            team1_name = match['team1_name'] or f"Команда #{match['team1_id']}"
            team2_name = match['team2_name'] or f"Команда #{match['team2_id']}"
            team1_city = match['team1_city'] or ''
            team2_city = match['team2_city'] or ''
            
            matches_html += f'''
            <div class="match-card" id="match-{match['id']}">
                <div class="match-status {status_class}">{status_text}</div>
                
                <div class="teams">
                    <div class="team" onclick="showTeamSquad({match['team1_id']}, '{team1_name}')">
                        <div class="team-name">{team1_name}</div>
                        <div class="team-city">{team1_city}</div>
                    </div>
                    
                    <div class="vs">VS</div>
                    
                    <div class="team" onclick="showTeamSquad({match['team2_id']}, '{team2_name}')">
                        <div class="team-name">{team2_name}</div>
                        <div class="team-city">{team2_city}</div>
                    </div>
                </div>
                
                <div class="score">
                    {match['score1']} : {match['score2']}
                </div>
                
                <div class="match-time">
                    {match['date_time']}
                    {f'<br>Период: {match["period"]}' if match['status'] in ['live', 'period'] else ''}
                </div>
            '''
            
            # Кнопки управления для админа
            if session.get('admin_logged_in'):
                matches_html += '<div class="match-controls">'
                
                if match['status'] == 'scheduled':
                    matches_html += f'''
                    <button onclick="startMatch({match['id']})" class="btn btn-start">Старт</button>
                    '''
                elif match['status'] == 'live':
                    matches_html += f'''
                    <button onclick="pauseMatch({match['id']})" class="btn btn-pause">Перерыв</button>
                    <button onclick="finishMatch({match['id']})" class="btn btn-finish">Завершить</button>
                    <button onclick="showScoreModal({match['id']})" class="btn btn-score">Счет</button>
                    <button onclick="showGoalModal({match['id']})" class="btn btn-goal">Гол</button>
                    '''
                elif match['status'] == 'period':
                    matches_html += f'''
                    <button onclick="resumeMatch({match['id']})" class="btn btn-resume">Продолжить</button>
                    <button onclick="finishMatch({match['id']})" class="btn btn-finish">Завершить</button>
                    '''
                
                matches_html += f'''
                <button onclick="deleteMatch({match['id']})" class="btn btn-delete">Удалить</button>
                </div>
                '''
            
            matches_html += '</div>'
        
        matches_html += '</div>'
    else:
        matches_html += '<p style="text-align: center; color: #999999; font-size: 18px;">Матчи еще не добавлены</p>'
    
    # Кнопка входа/выхода
    if session.get('admin_logged_in'):
        login_button = '<a href="/logout" class="logout-btn">Выйти</a>'
    else:
        login_button = '<a href="/admin/login" class="login-btn">Войти в админ-панель</a>'
    
    # Модальные окна
    modals = '''
    <div id="scoreModal" class="modal">
        <div class="modal-content">
            <h3 class="modal-title">Изменить счет</h3>
            <form id="scoreForm">
                <input type="hidden" id="scoreMatchId">
                <div class="form-group">
                    <label class="form-label">Счет команды 1</label>
                    <input type="number" id="score1" class="form-input" min="0" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Счет команды 2</label>
                    <input type="number" id="score2" class="form-input" min="0" required>
                </div>
                <div class="modal-buttons">
                    <button type="button" onclick="updateScore()" class="btn-confirm">Сохранить</button>
                    <button type="button" onclick="closeModal('scoreModal')" class="btn-cancel">Отмена</button>
                </div>
            </form>
        </div>
    </div>
    
    <div id="goalModal" class="modal">
        <div class="modal-content">
            <h3 class="modal-title">Добавить гол</h3>
            <form id="goalForm">
                <input type="hidden" id="goalMatchId">
                <div class="form-group">
                    <label class="form-label">Команда</label>
                    <select id="goalTeamId" class="form-select" required>
                        <option value="">Выберите команду</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Игрок</label>
                    <select id="goalPlayerId" class="form-select" required>
                        <option value="">Выберите игрока</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Период</label>
                    <input type="number" id="goalPeriod" class="form-input" min="1" max="4" value="1" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Время (мм:сс)</label>
                    <input type="text" id="goalTime" class="form-input" placeholder="10:30" required>
                </div>
                <div class="modal-buttons">
                    <button type="button" onclick="addGoal()" class="btn-confirm">Добавить</button>
                    <button type="button" onclick="closeModal('goalModal')" class="btn-cancel">Отмена</button>
                </div>
            </form>
        </div>
    </div>
    
    <div id="squadModal" class="modal">
        <div class="modal-content squad-modal">
            <h3 id="squadModalTitle" class="modal-title">Состав команды</h3>
            <div id="squadPlayers"></div>
            <div class="modal-buttons">
                <button type="button" onclick="closeModal('squadModal')" class="btn-cancel">Закрыть</button>
            </div>
        </div>
    </div>
    '''
    
    # JavaScript
    script = '''
    // Функции управления матчами
    function startMatch(matchId) {
        if (confirm('Начать матч?')) {
            fetch('/api/match/start/' + matchId, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Ошибка: ' + data.error);
                }
            });
        }
    }
    
    function pauseMatch(matchId) {
        fetch('/api/match/pause/' + matchId, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    
    function resumeMatch(matchId) {
        fetch('/api/match/resume/' + matchId, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    
    function finishMatch(matchId) {
        if (confirm('Завершить матч?')) {
            fetch('/api/match/finish/' + matchId, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Ошибка: ' + data.error);
                }
            });
        }
    }
    
    function deleteMatch(matchId) {
        if (confirm('Удалить матч?')) {
            fetch('/api/match/delete/' + matchId, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Ошибка: ' + data.error);
                }
            });
        }
    }
    
    // Модальные окна
    function showModal(modalId) {
        document.getElementById(modalId).style.display = 'flex';
    }
    
    function closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }
    
    function showScoreModal(matchId) {
        document.getElementById('scoreMatchId').value = matchId;
        showModal('scoreModal');
    }
    
    function showGoalModal(matchId) {
        document.getElementById('goalMatchId').value = matchId;
        
        // Загружаем команды
        fetch('/api/match/' + matchId + '/teams')
            .then(response => response.json())
            .then(data => {
                const select = document.getElementById('goalTeamId');
                select.innerHTML = '<option value="">Выберите команду</option>';
                data.teams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team.id;
                    option.textContent = team.name;
                    select.appendChild(option);
                });
                
                // При изменении команды загружаем игроков
                select.onchange = function() {
                    const teamId = this.value;
                    fetch('/api/team/' + teamId + '/players')
                        .then(response => response.json())
                        .then(players => {
                            const playerSelect = document.getElementById('goalPlayerId');
                            playerSelect.innerHTML = '<option value="">Выберите игрока</option>';
                            players.forEach(player => {
                                const option = document.createElement('option');
                                option.value = player.id;
                                option.textContent = player.name + ' (#' + player.number + ')';
                                playerSelect.appendChild(option);
                            });
                        });
                };
            });
        
        showModal('goalModal');
    }
    
    function showTeamSquad(teamId, teamName) {
        document.getElementById('squadModalTitle').textContent = 'Состав: ' + teamName;
        
        fetch('/api/team/' + teamId + '/players')
            .then(response => response.json())
            .then(players => {
                const squad = document.getElementById('squadPlayers');
                squad.innerHTML = '';
                
                if (players.length === 0) {
                    squad.innerHTML = '<div class="no-players">Игроки не добавлены</div>';
                } else {
                    players.forEach(player => {
                        const playerCard = document.createElement('div');
                        playerCard.className = 'player-card';
                        playerCard.innerHTML = `
                            <div class="player-info">
                                <div class="player-name">${player.name}</div>
                                <div class="player-details">№${player.number} | ${player.position}</div>
                            </div>
                            <div class="player-stats">
                                Голы: ${player.goals}<br>
                                Передачи: ${player.assists}
                            </div>
                        `;
                        squad.appendChild(playerCard);
                    });
                }
                
                showModal('squadModal');
            });
    }
    
    function updateScore() {
        const matchId = document.getElementById('scoreMatchId').value;
        const score1 = document.getElementById('score1').value;
        const score2 = document.getElementById('score2').value;
        
        fetch('/api/match/update_score/' + matchId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                score1: parseInt(score1),
                score2: parseInt(score2)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    
    function addGoal() {
        const matchId = document.getElementById('goalMatchId').value;
        const teamId = document.getElementById('goalTeamId').value;
        const playerId = document.getElementById('goalPlayerId').value;
        const period = document.getElementById('goalPeriod').value;
        const time = document.getElementById('goalTime').value;
        
        fetch('/api/match/add_goal/' + matchId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                team_id: parseInt(teamId),
                player_id: parseInt(playerId),
                period: parseInt(period),
                time: time
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    '''
    
    return render_template_string(
        BASE_HTML,
        content=matches_html,
        login_button=login_button,
        modals=modals,
        script=script
    )

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Проверяем логин и пароль
        if username == 'adminBHL' and password == 'admin2026BHL':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        
        # Форма с ошибкой
        login_form = f'''
        <div class="login-form">
            <h2 class="login-title">Вход в админ-панель</h2>
            <div class="error">Неверный логин или пароль</div>
            <form method="POST" action="/admin/login">
                <div class="form-group">
                    <label class="form-label">Логин</label>
                    <input type="text" name="username" class="form-input" value="{username or ''}" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Пароль</label>
                    <input type="password" name="password" class="form-input" required>
                </div>
                <button type="submit" class="btn-confirm" style="width: 100%;">Войти</button>
            </form>
            <div style="text-align: center; margin-top: 20px;">
                <a href="/" style="color: #cccccc;">← Вернуться на сайт</a>
            </div>
        </div>
        '''
        
        return render_template_string(
            BASE_HTML,
            content=login_form,
            login_button='<a href="/admin/login" class="login-btn">Войти в админ-панель</a>',
            modals='',
            script=''
        )
    
    # GET запрос - показать форму входа
    login_form = '''
    <div class="login-form">
        <h2 class="login-title">Вход в админ-панель</h2>
        <form method="POST" action="/admin/login">
            <div class="form-group">
                <label class="form-label">Логин</label>
                <input type="text" name="username" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Пароль</label>
                <input type="password" name="password" class="form-input" required>
            </div>
            <button type="submit" class="btn-confirm" style="width: 100%;">Войти</button>
        </form>
        <div style="text-align: center; margin-top: 20px;">
            <a href="/" style="color: #cccccc;">← Вернуться на сайт</a>
        </div>
    </div>
    '''
    
    return render_template_string(
        BASE_HTML,
        content=login_form,
        login_button='<a href="/admin/login" class="login-btn">Войти в админ-панель</a>',
        modals='',
        script=''
    )

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем команды
    cursor.execute('SELECT * FROM teams ORDER BY name')
    teams = cursor.fetchall()
    
    conn.close()
    
    # Формируем админ-панель
    teams_options = ''
    for team in teams:
        teams_options += f'<option value="{team["id"]}">{team["name"]} ({team["city"]})</option>'
    
    admin_content = f'''
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 class="section-title">Панель администратора</h2>
        <p style="color: #cccccc; margin-bottom: 20px;">Управление матчами и командами</p>
    </div>
    
    <div class="admin-panel">
        <div class="admin-section">
            <h3 class="admin-title">Создать матч</h3>
            <form id="createMatchForm" onsubmit="event.preventDefault(); createMatch();">
                <div class="form-group">
                    <label class="form-label">Команда 1</label>
                    <select id="team1_id" class="form-select" required>
                        <option value="">Выберите команду</option>
                        {teams_options}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Команда 2</label>
                    <select id="team2_id" class="form-select" required>
                        <option value="">Выберите команду</option>
                        {teams_options}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Дата и время</label>
                    <input type="datetime-local" id="match_datetime" class="form-input" required>
                </div>
                <button type="submit" class="btn-confirm" style="width: 100%;">Создать матч</button>
            </form>
        </div>
        
        <div class="admin-section">
            <h3 class="admin-title">Создать команду</h3>
            <form id="createTeamForm" onsubmit="event.preventDefault(); createTeam();">
                <div class="form-group">
                    <label class="form-label">Название команды</label>
                    <input type="text" id="team_name" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Город</label>
                    <input type="text" id="team_city" class="form-input" required>
                </div>
                <button type="submit" class="btn-confirm" style="width: 100%;">Создать команду</button>
            </form>
        </div>
        
        <div class="admin-section">
            <h3 class="admin-title">Добавить игрока</h3>
            <form id="createPlayerForm" onsubmit="event.preventDefault(); createPlayer();">
                <div class="form-group">
                    <label class="form-label">Команда</label>
                    <select id="player_team_id" class="form-select" required>
                        <option value="">Выберите команду</option>
                        {teams_options}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Имя игрока</label>
                    <input type="text" id="player_name" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Номер</label>
                    <input type="number" id="player_number" class="form-input" min="1" max="99" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Позиция</label>
                    <select id="player_position" class="form-select" required>
                        <option value="Нападающий">Нападающий</option>
                        <option value="Защитник">Защитник</option>
                        <option value="Вратарь">Вратарь</option>
                    </select>
                </div>
                <button type="submit" class="btn-confirm" style="width: 100%;">Добавить игрока</button>
            </form>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/" class="btn-cancel" style="display: inline-block; text-decoration: none; padding: 12px 30px;">← Вернуться на сайт</a>
        </div>
    </div>
    '''
    
    admin_script = '''
    function createMatch() {
        const team1_id = document.getElementById('team1_id').value;
        const team2_id = document.getElementById('team2_id').value;
        const date_time = document.getElementById('match_datetime').value;
        
        if (team1_id === team2_id) {
            alert('Выберите разные команды!');
            return;
        }
        
        fetch('/api/match/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                team1_id: parseInt(team1_id),
                team2_id: parseInt(team2_id),
                date_time: date_time
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Матч успешно создан!');
                location.reload();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    
    function createTeam() {
        const name = document.getElementById('team_name').value;
        const city = document.getElementById('team_city').value;
        
        fetch('/api/team/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                city: city
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Команда успешно создана!');
                location.reload();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    
    function createPlayer() {
        const team_id = document.getElementById('player_team_id').value;
        const name = document.getElementById('player_name').value;
        const number = document.getElementById('player_number').value;
        const position = document.getElementById('player_position').value;
        
        fetch('/api/player/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                team_id: parseInt(team_id),
                name: name,
                number: parseInt(number),
                position: position
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Игрок успешно добавлен!');
                document.getElementById('player_name').value = '';
                document.getElementById('player_number').value = '';
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
    '''
    
    return render_template_string(
        BASE_HTML,
        content=admin_content,
        login_button='<a href="/logout" class="logout-btn">Выйти</a>',
        modals='',
        script=admin_script
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==================== API РОУТЫ ====================
@app.route('/api/match/start/<int:match_id>', methods=['POST'])
def api_start_match(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE matches SET status = "live", period = 1 WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/pause/<int:match_id>', methods=['POST'])
def api_pause_match(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE matches SET status = "period" WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/resume/<int:match_id>', methods=['POST'])
def api_resume_match(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE matches SET status = "live" WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/finish/<int:match_id>', methods=['POST'])
def api_finish_match(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE matches SET status = "finished" WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/delete/<int:match_id>', methods=['POST'])
def api_delete_match(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM matches WHERE id = ?', (match_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/update_score/<int:match_id>', methods=['POST'])
def api_update_score(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    data = request.get_json()
    score1 = data.get('score1', 0)
    score2 = data.get('score2', 0)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE matches SET score1 = ?, score2 = ? WHERE id = ?', 
                  (score1, score2, match_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/add_goal/<int:match_id>', methods=['POST'])
def api_add_goal(match_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    data = request.get_json()
    team_id = data.get('team_id')
    player_id = data.get('player_id')
    period = data.get('period', 1)
    time = data.get('time', '00:00')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Добавляем гол
    cursor.execute('''
        INSERT INTO goals (match_id, team_id, player_id, period, time)
        VALUES (?, ?, ?, ?, ?)
    ''', (match_id, team_id, player_id, period, time))
    
    # Обновляем счет
    cursor.execute('SELECT team1_id, team2_id, score1, score2 FROM matches WHERE id = ?', (match_id,))
    match = cursor.fetchone()
    
    if match:
        if match['team1_id'] == team_id:
            new_score1 = match['score1'] + 1
            new_score2 = match['score2']
        else:
            new_score1 = match['score1']
            new_score2 = match['score2'] + 1
        
        cursor.execute('UPDATE matches SET score1 = ?, score2 = ? WHERE id = ?', 
                      (new_score1, new_score2, match_id))
        
        # Обновляем статистику игрока
        cursor.execute('UPDATE players SET goals = goals + 1 WHERE id = ?', (player_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/create', methods=['POST'])
def api_create_match():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    data = request.get_json()
    team1_id = data.get('team1_id')
    team2_id = data.get('team2_id')
    date_time = data.get('date_time')
    
    if team1_id == team2_id:
        return jsonify({'success': False, 'error': 'Выберите разные команды'})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO matches (team1_id, team2_id, date_time, status)
        VALUES (?, ?, ?, 'scheduled')
    ''', (team1_id, team2_id, date_time))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/team/create', methods=['POST'])
def api_create_team():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    data = request.get_json()
    name = data.get('name')
    city = data.get('city')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO teams (name, city)
        VALUES (?, ?)
    ''', (name, city))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/player/create', methods=['POST'])
def api_create_player():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    data = request.get_json()
    team_id = data.get('team_id')
    name = data.get('name')
    number = data.get('number')
    position = data.get('position')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (team_id, name, number, position)
        VALUES (?, ?, ?, ?)
    ''', (team_id, name, number, position))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/match/<int:match_id>/teams')
def api_get_match_teams(match_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t1.id as team1_id, t1.name as team1_name,
               t2.id as team2_id, t2.name as team2_name
        FROM matches m
        LEFT JOIN teams t1 ON m.team1_id = t1.id
        LEFT JOIN teams t2 ON m.team2_id = t2.id
        WHERE m.id = ?
    ''', (match_id,))
    
    match = cursor.fetchone()
    conn.close()
    
    if match:
        teams = [
            {'id': match['team1_id'], 'name': match['team1_name'] or f"Команда #{match['team1_id']}"},
            {'id': match['team2_id'], 'name': match['team2_name'] or f"Команда #{match['team2_id']}"}
        ]
        return jsonify({'teams': teams})
    
    return jsonify({'teams': []})

@app.route('/api/team/<int:team_id>/players')
def api_get_team_players(team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, number, position, goals, assists
        FROM players
        WHERE team_id = ?
        ORDER BY number
    ''', (team_id,))
    
    players = cursor.fetchall()
    conn.close()
    
    players_list = []
    for player in players:
        players_list.append({
            'id': player['id'],
            'name': player['name'],
            'number': player['number'],
            'position': player['position'],
            'goals': player['goals'],
            'assists': player['assists']
        })
    
    return jsonify(players_list)

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    # Создаем базу данных
    if not os.path.exists(app.config['DATABASE']):
        init_db()
        print("=" * 50)
        print("База данных создана!")
        print("=" * 50)
        print("Данные для входа:")
        print("Логин: adminBHL")
        print("Пароль: admin2026BHL")
        print("=" * 50)
        print("Сайт доступен: http://localhost:5000")
        print("Админ-панель: http://localhost:5000/admin/login")
        print("=" * 50)
    

    app.run(debug=True, host='0.0.0.0', port=5000)
