import random
# Importaciones habilitadas
from Mapa import Board
from Fuego import FireManager
from Agentes import Agent

class GameManager:
    def __init__(self, board_width=8, board_height=6, modo="inteligente"):
        # Inicializamos los sistemas base
        self.board = Board(board_width, board_height)
        self.fire_manager = FireManager(self.board)
        self.modo = modo # Guardamos el modo seleccionado
        
        self.agents = []
        self.turn_count = 0
        
        # Condiciones de victoria / derrota
        self.victims_rescued = 0
        self.victims_lost = 0
        self.structural_damage = 0  # Max 24
        
        # Puntos de Interes (10 victimas, 5 falsas alarmas)
        self.poi_pool = ["Victim"] * 10 + ["FalseAlarm"] * 5
        random.shuffle(self.poi_pool)
        self.active_pois = {}  # {(x, y): "type", "revealed"}
        
        self.game_over = False
        self.win = False

    def setup_game(self):
        """Configura el escenario inicial del Family Game."""
        # 1. Colocar 6 agentes afuera del edificio (esparcidos en las 4 entradas)
        spawn_points = [(0, 3), (9, 4), (6, 0), (3, 7), (0, 3), (9, 4)]
        for i in range(6):
            # Transmitimos el modo configurado al agente
            self.agents.append(Agent(id=i+1, start_pos=spawn_points[i], modo=self.modo)) 
            
        # 2. Setup Inicial del mapa
        # ---MUROS EXTERIORES ---
        for x in range(1, 9):
            if x != 6: self.board.add_boundary((x, 1), (x, 0), "wall") # Superior (Hueco en x=6)
            if x != 3: self.board.add_boundary((x, 6), (x, 7), "wall") # Inferior (Hueco en x=3)
        for y in range(1, 7):
            if y != 3: self.board.add_boundary((1, y), (0, y), "wall") # Izquierdo (Hueco en y=3)
            if y != 4: self.board.add_boundary((8, y), (9, y), "wall") # Derecho (Hueco en y=4)
        # ---MUROS EXTERIORES ---
        # Horizontales internos
        for x in [3, 4, 5, 6, 7]:
            self.board.add_boundary((x, 3), (x, 4), "wall") # Muro horizontal interno
        self.board.add_boundary((8, 3), (8, 2), "door") # Puerta
        for x in [1, 2, 3, 5, 6, 7, 8]:
            self.board.add_boundary((x, 4), (x, 5), "wall") # Muro horizontal interno
        self.board.add_boundary((4, 4), (4, 5), "door") # Puerta
        # Verticales internos
        self.board.add_boundary((3, 1), (4, 1), "door") 
        self.board.add_boundary((3, 2), (4, 2), "wall") 
        self.board.add_boundary((5, 1), (6, 1), "wall") 
        self.board.add_boundary((5, 2), (6, 2), "door") 
        self.board.add_boundary((2, 3), (3, 3), "door") 
        self.board.add_boundary((2, 4), (3, 4), "wall") 
        self.board.add_boundary((6, 3), (7, 3), "wall") 
        self.board.add_boundary((6, 4), (7, 4), "door") 
        self.board.add_boundary((5, 5), (6, 5), "wall")
        self.board.add_boundary((5, 6), (6, 6), "door")
        self.board.add_boundary((7, 5), (8, 5), "wall") 
        self.board.add_boundary((7, 6), (8, 6), "door")
        
        # 3. Setup de fuegos iniciales
        fuegos_iniciales = [(2,2), (2,3), (3,2), (3,3), (4,3), (5,3), (4,4), (6,5), (7,5), (6,6)]
        for pos in fuegos_iniciales:
            self.fire_manager.set_state(pos, 2) # 2 = Fuego
        
        # 4. Colocar 3 POIs iniciales
        self.replenish_pois()

    def replenish_pois(self):
        """Mantiene siempre 3 POIs en el tablero, lanzando dados aleatorios."""
        while len(self.active_pois) < 3 and len(self.poi_pool) > 0:
            target_pos = (random.randint(1, 8), random.randint(1, 6))
            
            # Regla: No colocar donde ya hay fuego 
            if self.fire_manager.get_state(target_pos) > 0:
                continue
            if target_pos in self.active_pois:
                continue
                
            # Extraer de la bolsa
            poi_type = self.poi_pool.pop()
            self.active_pois[target_pos] = {"type": poi_type, "revealed": False}
            print(f"Nuevo POI (Secreto) colocado en {target_pos}")

    def check_poi_reveal(self, agent):
        """Verifica si el agente pisa un POI para revelarlo."""
        if agent.pos in self.active_pois and not self.active_pois[agent.pos]["revealed"]:
            poi = self.active_pois[agent.pos]
            poi["revealed"] = True
            
            if poi["type"] == "FalseAlarm":
                print(f"Agente {agent.id} encontro una Falsa Alarma en {agent.pos}!")
                del self.active_pois[agent.pos] # Se descarta
            else:
                print(f"Agente {agent.id} encontro una VICTIMA en {agent.pos}!")
                # Si el agente tiene las manos libres, la carga automaticamente
                if not agent.carrying_victim:
                    agent.carrying_victim = True
                    print(f"  -> Agente {agent.id} ha cargado a la victima en su espalda!")
                    del self.active_pois[agent.pos]

    def check_rescues(self, agent):
        """Verifica si el agente salio de la casa con una victima para rescatarla."""
        if agent.carrying_victim:
            # Si esta en el perimetro exterior (X <= 0 o >= 9, Y <= 0 o >= 7)
            if not (1 <= agent.pos[0] <= self.board.width and 1 <= agent.pos[1] <= self.board.height):
                agent.carrying_victim = False
                self.victims_rescued += 1
                print(f"\n*** EL AGENTE {agent.id} HA RESCATADO A UNA VICTIMA! (Total: {self.victims_rescued}/7) ***\n")

    def check_fire_casualties(self):
        """Verifica si el fuego alcanzo a alguna victima o derribo a un agente (Knock Down)."""
        pois_to_remove = []
        for pos, poi in self.active_pois.items():
            if self.fire_manager.get_state(pos) == 2: # Si hay fuego
                if poi["type"] == "Victim":
                    self.victims_lost += 1
                    print(f"Una victima ha muerto en {pos}! Total perdidas: {self.victims_lost}")
                pois_to_remove.append(pos)
                
        for pos in pois_to_remove:
            del self.active_pois[pos]
            
        # Revisar Knock Downs de agentes
        for agent in self.agents:
            if self.fire_manager.get_state(agent.pos) == 2:
                agent.is_knocked_down = True
                if agent.carrying_victim:
                    agent.carrying_victim = False
                    self.victims_lost += 1
                    print(f"Agente {agent.id} derribado! Perdio a la victima que cargaba.")
                
                # Mover agente a la ambulancia MAS CERCANA
                best_pos = (0, 0)
                best_dist = float('inf')
                for safe_x, safe_y in [(0, 3), (9, 4), (6, 0), (3, 7)]:
                    dist = abs(agent.pos[0] - safe_x) + abs(agent.pos[1] - safe_y)
                    if dist < best_dist:
                        best_dist = dist
                        best_pos = (safe_x, safe_y)
                        
                agent.pos = best_pos 
                print(f"Agente {agent.id} derribado y llevado a la ambulancia en {best_pos}.")

    def check_win_loss(self):
        """Verifica si la simulacion ha terminado."""
        # Calcular el dano estructural actual (Fichas de dano en muros)
        dano_actual = 0
        for boundary in self.board.boundaries.values():
            if boundary.type == "wall":
                dano_actual += (2 - boundary.hp)
        self.structural_damage = dano_actual

        if self.victims_rescued >= 7:
            self.game_over = True
            self.win = True
            print("VICTORIA! 7 Victimas rescatadas.")
        
        elif self.victims_lost >= 4:
            self.game_over = True
            self.win = False
            print("DERROTA! 4 Victimas perdidas.")
            
        elif self.structural_damage >= 24:
            self.game_over = True
            self.win = False
            print("DERROTA! El edificio ha colapsado (24 danos).")

    def play_turn(self):
        """Ejecuta un ciclo completo de la simulacion."""
        if self.game_over: return
        
        self.turn_count += 1
        print(f"\n--- INICIO DEL TURNO {self.turn_count} ---")
        
        for agent in self.agents:
            if self.game_over: break
            
            print(f"\nTurno de Agente {agent.id}")
            agent.reset_turn()
            
            # ACTIVAR ESTRATEGIA (Usa el enrutador que evalua si es aleatorio o inteligente):
            agent.execute_turn(self)
             
            # Checkeos de estado pos-movimiento
            self.check_poi_reveal(agent)
            self.check_rescues(agent)
            
            agent.end_turn()
            
            # 2. Fase de Fuego (Advance Fire) - Ocurre DESPUES de cada agente
            self.fire_manager.propagate_turn()
            self.check_fire_casualties()
            
            # 3. Fase de Reponer POIs
            self.replenish_pois()
            
            # Revisar condiciones de fin de juego
            self.check_win_loss()
            
        # Imprimir el mapa al final de la ronda completa
        self.render_console()

    def render_console(self):
        """Renderizador simple ASCII para debugear antes de tener Unity."""
        print("\nEstado Actual del Tablero:")
        width = self.board.width
        height = self.board.height
        
        for y in range(1, height + 1):
            row = ""
            for x in range(1, width + 1):
                char = "." # Vacio
                
                estado = self.fire_manager.get_state((x, y))
                if estado == 1: char = "h" # Humo
                elif estado == 2: char = "F" # Fuego
                
                if (x, y) in self.active_pois:
                    char = "?" if not self.active_pois[(x, y)]["revealed"] else "V"
                    
                for agent in self.agents:
                    if agent.pos == (x, y):
                        char = str(agent.id) # Reemplaza el texto con el ID del bombero
                
                row += char + " "
            print(row)
        print(f"Victimas [Rescatadas: {self.victims_rescued}/7 | Perdidas: {self.victims_lost}/4]")
        print(f"Dano Estructural: {self.structural_damage}/24\n")

# Para probar rapidamente en la terminal de Python:
if __name__ == "__main__":
    # Puedes cambiar "aleatorio" por "inteligente" para alternar la logica
    game = GameManager(modo="aleatorio")
    game.setup_game()
    print("ESTADO INICIAL:")
    game.render_console()
    
    # BUCLE PRINCIPAL QUE CORRE HASTA GANAR O PERDER
    while not game.game_over:
        game.play_turn()
        
    print("\n==========================================")
    print("--- FIN DE LA SIMULACION ---")
    if game.win:
        print(f"LOS BOMBEROS GANARON! {game.victims_rescued} victimas rescatadas.")
    else:
        print(f"DERROTA. Victimas perdidas: {game.victims_lost}/4.")
    print("==========================================")