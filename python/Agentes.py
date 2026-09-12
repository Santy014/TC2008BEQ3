import heapq
import random 

class Pathfinder:
    @staticmethod
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def a_star_search(start, goal, board, fire_manager, carrying_victim=False):
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while frontier:
            _, current = heapq.heappop(frontier)

            if current == goal:
                break
                
            for dx, dy in directions:
                next_pos = (current[0] + dx, current[1] + dy)
                
                if not (0 <= next_pos[0] <= board.width + 1 and 0 <= next_pos[1] <= board.height + 1):
                    continue
                    
                # Validar muros y calcular costo de abrir puertas o ROMPER MUROS
                edge_key = board._get_edge_key(current, next_pos)
                boundary_cost = 0
                if edge_key in board.boundaries:
                    boundary = board.boundaries[edge_key]
                    if boundary.type == "wall" and boundary.hp > 0:
                        # Cuesta 2 AP dar un golpe de hacha. Si tiene 2 HP, romperlo totalmente cuesta 4 AP.
                        boundary_cost = boundary.hp * 2
                    if boundary.type == "door" and boundary.hp > 0 and not boundary.is_open:
                        boundary_cost = 1 # Considerar costo de abrir puerta
                        
                # Calcular costo REAL de movimiento vs Fuego
                state = fire_manager.get_state(next_pos)
                if state == 2:
                    # Cuesta 2 AP apagarlo + el costo de dar el paso (1 normal, 2 si lleva víctima)
                    move_cost = 4 if carrying_victim else 3 
                else:
                    # Vacío o Humo (El humo es seguro de pisar)
                    move_cost = 2 if carrying_victim else 1
                    
                new_cost = cost_so_far[current] + move_cost + boundary_cost
                
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + Pathfinder.heuristic(next_pos, goal)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
                    
        if goal not in came_from:
            return None
            
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

class Agent:
    def __init__(self, id, start_pos, modo="inteligente"):
        self.id = id
        self.pos = start_pos
        self.ap = 4
        self.saved_ap = 0
        self.carrying_victim = False
        self.is_knocked_down = False
        self.modo = modo # <-- Almacenamos el modo (inteligente o aleatorio)
        
    def reset_turn(self):
        total_ap = self.ap + self.saved_ap
        self.current_ap = min(total_ap, 8)
        self.saved_ap = 0

    def extinguish(self, target_pos, fire_manager):
        state = fire_manager.get_state(target_pos)
        if state == 1 and self.current_ap >= 1:
            fire_manager.set_state(target_pos, 0)
            self.current_ap -= 1
            return True
        elif state == 2:
            if self.current_ap >= 2:
                fire_manager.set_state(target_pos, 0) # Apagar por completo
                self.current_ap -= 2
                return True
            elif self.current_ap == 1:
                fire_manager.set_state(target_pos, 1) # Reducir a humo táctico (1 AP)
                self.current_ap -= 1
                return True
        return False

    # Nnuevo enrutador para el turno principal
    def execute_turn(self, game):
        """Llama a la estrategia correspondiente según el modo del agente."""
        if self.modo == "aleatorio":
            self.execute_strategy_random(game)
        else:
            self.execute_strategy_smart(game)

    def execute_strategy_random(self, game):
        """ESTRATEGIA ALEATORIA: El agente toma decisiones al azar respetando AP y obstáculos."""
        print(f"  [🎲] Agente {self.id} inicia en {self.pos} con {self.current_ap} AP (Modo Aleatorio).")
        
        while self.current_ap > 0:
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            random.shuffle(directions) # Aleatoriza el orden de evaluación de las casillas vecinas
            moved_or_acted = False
            
            for dx, dy in directions:
                next_step = (self.pos[0] + dx, self.pos[1] + dy)
                
                # 1. Validar límites del tablero
                if not (0 <= next_step[0] <= game.board.width + 1 and 0 <= next_step[1] <= game.board.height + 1):
                    continue
                
                # 2. Interacción con Muros y Puertas
                edge_key = game.board._get_edge_key(self.pos, next_step)
                if edge_key in game.board.boundaries:
                    boundary = game.board.boundaries[edge_key]
                    
                    if boundary.type == "wall" and boundary.hp > 0:
                        if self.current_ap >= 2:
                            game.board.interact_with_boundary(self.pos, next_step, action="damage")
                            self.current_ap -= 2
                            print(f"    -> Hachazo en muro hacia {next_step}. (HP: {boundary.hp}, AP: {self.current_ap})")
                            moved_or_acted = True
                            break
                        continue # No tiene AP para romperlo, intenta otra dirección
                        
                    elif boundary.type == "door" and boundary.hp > 0 and not boundary.is_open:
                        if self.current_ap >= 1:
                            boundary.is_open = True
                            self.current_ap -= 1
                            print(f"    -> Abrió puerta hacia {next_step}. (AP: {self.current_ap})")
                            moved_or_acted = True
                            break
                        continue # No tiene AP para abrirla
                
                # 3. Interacción con el Fuego
                state = game.fire_manager.get_state(next_step)
                if state == 2:
                    if self.current_ap >= 2:
                        self.extinguish(next_step, game.fire_manager)
                        print(f"    -> Apagó fuego en {next_step}. (AP: {self.current_ap})")
                        moved_or_acted = True
                        break
                    continue # Es fuego y no puede apagarlo, no puede caminar ahí
                
                # 4. Movimiento hacia casilla válida (Vacía o con Humo)
                move_cost = 2 if self.carrying_victim else 1
                if self.current_ap >= move_cost:
                    self.current_ap -= move_cost
                    self.pos = next_step
                    print(f"    -> Movimiento a {next_step}. (AP: {self.current_ap})")
                    
                    # REVELACIÓN MID-TURN Y PREVENCIÓN DE SUICIDIO
                    was_carrying = self.carrying_victim
                    game.check_poi_reveal(self)
                    game.check_rescues(self)
                    
                    if was_carrying and not self.carrying_victim:
                        print(f"    -> ¡Dejó a la víctima! Terminando turno para reorganizarse.")
                        break
                        
                    moved_or_acted = True
                    break # Rompe el ciclo for para iniciar una nueva acción con sus AP restantes
            
            # Si el for termina sin haber hecho NADA (atrapado o sin AP para las opciones disponibles)
            if not moved_or_acted:
                print(f"    -> Atrapado o sin AP suficiente para acciones válidas. Guardando AP.")
                break

    def execute_strategy_smart(self, game):
        """ESTRATEGIA INTELIGENTE AVANZADA: Anti-enjambre, Fuego y Uso de Hacha."""
        print(f"  [🧠] Agente {self.id} inicia en {self.pos} con {self.current_ap} AP.")
        
        while self.current_ap > 0:
            best_path = None
            best_cost = float('inf')
            
            # 1. Si lleva víctima, la prioridad absoluta es salir
            if self.carrying_victim:
                goals = [(6, 0), (3, 7), (0, 3), (9, 4)]
                for g in goals:
                    path = Pathfinder.a_star_search(self.pos, g, game.board, game.fire_manager, True)
                    if path is not None and len(path) < best_cost: 
                        best_cost = len(path)
                        best_path = path
            else:
                # 2. Buscar POIs, pero EVITANDO EL ENJAMBRE
                for poi in game.active_pois.keys():
                    path = Pathfinder.a_star_search(self.pos, poi, game.board, game.fire_manager, False)
                    if path is None: continue
                    my_dist = len(path)
                    
                    # ¿Soy el bombero más cercano a este POI?
                    is_closest = True
                    for other in game.agents:
                        if other.id != self.id and not other.carrying_victim:
                            other_path = Pathfinder.a_star_search(other.pos, poi, game.board, game.fire_manager, False)
                            if other_path is not None:
                                if len(other_path) < my_dist or (len(other_path) == my_dist and other.id < self.id):
                                    is_closest = False
                                    break
                    
                    if is_closest and my_dist < best_cost:
                        best_cost = my_dist
                        best_path = path
                
                # 3. MODO BOMBERO: Si los POIs están cubiertos, apagar el fuego más cercano
                if best_path is None:
                    fires = [pos for pos, state in game.fire_manager.cells.items() if state == 2]
                    for f in fires:
                        # ANTI-ENJAMBRE TAMBIÉN PARA EL FUEGO
                        is_closest = True
                        my_dist_fire = Pathfinder.heuristic(self.pos, f)
                        for other in game.agents:
                            if other.id != self.id and not other.carrying_victim:
                                if Pathfinder.heuristic(other.pos, f) < my_dist_fire:
                                    is_closest = False
                                    break
                                    
                        if not is_closest: continue
                        
                        path = Pathfinder.a_star_search(self.pos, f, game.board, game.fire_manager, False)
                        if path is not None and len(path) < best_cost:
                            best_cost = len(path)
                            best_path = path
                            
            if best_path is None:
                print(f"    -> Atrapado o sin objetivo claro. Guardando AP.")
                break
                
            # Si ya estamos sobre el objetivo (longitud 0)
            if len(best_path) == 0:
                was_carrying = self.carrying_victim
                game.check_poi_reveal(self)
                game.check_rescues(self)
                if not self.carrying_victim: 
                    break # Terminó con su objetivo actual, sale para reevaluar
                continue
                
            next_step = best_path[0]
            
            # 4. EXTINCIÓN OPORTUNISTA (Prevención de daño lateral)
            if not self.carrying_victim:
                extinguished_nearby = False
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    adj = (self.pos[0] + dx, self.pos[1] + dy)
                    if game.fire_manager.get_state(adj) == 2 and self.current_ap >= 2:
                        if game.board.can_move(self.pos, adj):
                            self.extinguish(adj, game.fire_manager)
                            print(f"    -> 🧯 Prevención: Apagó fuego adyacente en {adj}. (AP: {self.current_ap})")
                            extinguished_nearby = True
                            break
                if extinguished_nearby:
                    continue # Reevaluar entorno post-extinción
            
            # 5. INTERACCIÓN Y MOVIMIENTO
            edge_key = game.board._get_edge_key(self.pos, next_step)
            if edge_key in game.board.boundaries:
                boundary = game.board.boundaries[edge_key]
                # Evaluar si hay un MURO en el camino
                if boundary.type == "wall" and boundary.hp > 0:
                    if self.current_ap >= 2:
                        game.board.interact_with_boundary(self.pos, next_step, action="damage")
                        self.current_ap -= 2
                        print(f"    -> 🪓 Usó el hacha en el muro hacia {next_step}. (HP restante: {boundary.hp}, AP: {self.current_ap})")
                        continue # Vuelve a evaluar, si el muro sigue vivo (HP 1), dará otro hachazo en el próximo loop.
                    else: break
                
                # Evaluar si hay una PUERTA cerrada en el camino
                elif boundary.type == "door" and boundary.hp > 0 and not boundary.is_open:
                    if self.current_ap >= 1:
                        boundary.is_open = True
                        self.current_ap -= 1
                        print(f"    -> 🚪 Abrió puerta hacia {next_step}. (AP: {self.current_ap})")
                        continue 
                    else: break
            
            state = game.fire_manager.get_state(next_step)
            if state == 2:
                if self.current_ap >= 2:
                    self.extinguish(next_step, game.fire_manager)
                    print(f"    -> 🧯 Apagó obstáculo de fuego en {next_step}. (AP: {self.current_ap})")
                    continue
                else: break
                    
            move_cost = 2 if self.carrying_victim else 1
            if self.current_ap >= move_cost:
                self.current_ap -= move_cost
                self.pos = next_step
                print(f"    -> 🏃 Caminó a {next_step}. (AP: {self.current_ap})")
                
                # REVELACIÓN MID-TURN Y PREVENCIÓN DE SUICIDIO
                was_carrying = self.carrying_victim
                game.check_poi_reveal(self)
                game.check_rescues(self)
                
                if was_carrying and not self.carrying_victim:
                    print(f"    -> 🏥 ¡Dejó a la víctima a salvo! Terminando turno para reorganizarse.")
                    break
            else:
                break

    def end_turn(self):
        self.saved_ap = min(self.current_ap, 4)
        self.current_ap = 0