# TC2008B Modelación de Sistemas Multiagentes con gráficas computacionales
# Python server to interact with Unity via POST
# Adaptado para Flash Point: Fire Rescue

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json
import traceback

# Importamos tu simulador
# Asegúrate de que tu archivo principal se llame Simulacion.py en la misma carpeta
from Simulacion import GameManager 

# Creamos una instancia GLOBAL del juego para que el servidor recuerde 
# el estado entre cada petición (POST) que haga Unity.
game = GameManager()
game.setup_game()

class Server(BaseHTTPRequestHandler):
    
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') # Permite a Unity conectarse sin bloqueos de seguridad
        self.end_headers()
        
    def do_GET(self):
        # Un GET solo devuelve el estado actual sin avanzar el turno
        self._set_response()
        game_state = self.build_json_state()
        self.wfile.write(json.dumps(game_state).encode('utf-8'))

    def do_POST(self):
        self._set_response()
        
        try:
            # Si el juego no ha terminado, calculamos el siguiente turno
            if not game.game_over:
                game.play_turn()
                
            # Extraemos toda la información del tablero a un diccionario
            game_state = self.build_json_state()
            
            # Convertimos el diccionario a un string JSON y lo mandamos a Unity
            json_str = json.dumps(game_state)
            self.wfile.write(json_str.encode('utf-8'))
            
        except Exception as e:
            # Si hay un error en la simulación, que no crashee el servidor, solo avisamos
            logging.error(f"Error durante el turno: {traceback.format_exc()}")
            error_json = json.dumps({"error": str(e)})
            self.wfile.write(error_json.encode('utf-8'))

    def build_json_state(self):
        """Traduce el tablero complejo de Python a datos simples para Unity."""
        state = {
            "turn": game.turn_count,
            "game_over": game.game_over,
            "win": game.win,
            "structural_damage": game.structural_damage,
            "victims_rescued": game.victims_rescued,
            "victims_lost": game.victims_lost,
            "agents": [],
            "fires": [],
            "pois": []
        }
        
        # 1. Empaquetar Agentes
        for agent in game.agents:
            state["agents"].append({
                "id": agent.id,
                "x": agent.pos[0],
                "y": agent.pos[1],
                "carrying_victim": agent.carrying_victim,
                "is_knocked_down": agent.is_knocked_down
            })
            
        # 2. Empaquetar Fuego/Humo
        for pos, f_state in game.fire_manager.cells.items():
            if f_state > 0: # Solo enviamos celdas que no estén vacías
                state["fires"].append({
                    "x": pos[0],
                    "y": pos[1],
                    "state": f_state # 1 = Humo, 2 = Fuego
                })
                
        # 3. Empaquetar POIs (Víctimas / Falsas alarmas)
        for pos, poi in game.active_pois.items():
            state["pois"].append({
                "x": pos[0],
                "y": pos[1],
                "revealed": poi["revealed"],
                "type": poi["type"]
            })
            
        return state

def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Starting Flash Point Server on port {port}...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping Server...\n")

if __name__ == '__main__':
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()