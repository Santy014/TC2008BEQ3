import random

class FireManager:
    def __init__(self, board):
        self.board = board
        self.cells = {} 

    def get_state(self, pos):
        return self.cells.get(pos, 0)

    def set_state(self, pos, state):
        self.cells[pos] = state

    def propagate_turn(self):
        """Función principal (Advance Fire)."""
        target_pos = (random.randint(1, 8), random.randint(1, 6))
        self._resolve_impact(target_pos)
        self._resolve_flashovers()

    def _resolve_impact(self, pos):
        current_state = self.get_state(pos)
        if current_state == 0:
            self.set_state(pos, 1) # Humo
        elif current_state == 1:
            self.set_state(pos, 2) # Fuego
        elif current_state == 2:
            print(f"\n ¡EXPLOSIÓN EN {pos}! La onda expansiva se propaga.")
            self._trigger_explosion(pos)

    def _trigger_explosion(self, origin):
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dx, dy in directions:
            current_pos = origin
            while True:
                next_pos = (current_pos[0] + dx, current_pos[1] + dy)
                
                # LÍMITES: La onda sale del mapa y se disipa
                if not (1 <= next_pos[0] <= self.board.width and 1 <= next_pos[1] <= self.board.height):
                    break 
                
                # REVISAR OBSTÁCULOS (Muros y Puertas)
                edge_key = self.board._get_edge_key(current_pos, next_pos)
                if edge_key in self.board.boundaries:
                    boundary = self.board.boundaries[edge_key]
                    
                    if boundary.type == "wall" and boundary.hp > 0:
                        boundary.hp -= 1
                        print(f"  -> Muro estructural entre {current_pos} y {next_pos} dañado (HP: {boundary.hp})")
                        break # El muro detiene la onda
                        
                    elif boundary.type == "door" and boundary.hp > 0:
                        if boundary.is_open:
                            boundary.hp = 0
                            boundary.is_open = False
                            print(f"  -> ¡Puerta ABIERTA entre {current_pos} y {next_pos} DESTRUIDA por onda expansiva!")
                            # La regla dice que si está abierta se destruye pero NO detiene la onda. Sigue el bucle.
                        else:
                            boundary.hp = 0
                            print(f"  -> ¡Puerta CERRADA entre {current_pos} y {next_pos} DESTRUIDA por onda expansiva!")
                            break # La puerta cerrada SÍ detiene la onda
                
                # RESOLVER IMPACTO EN LA CELDA
                next_state = self.get_state(next_pos)
                if next_state == 0:
                    self.set_state(next_pos, 2)
                    break # Fuego en vacío detiene la onda
                elif next_state == 1:
                    self.set_state(next_pos, 2)
                    break # Fuego en humo detiene la onda
                elif next_state == 2:
                    current_pos = next_pos # Shockwave! Viaja a través del fuego sin detenerse

    def _resolve_flashovers(self):
        """Regla de Flashover: Reacción en cadena de humo adyacente a fuego."""
        while True:
            changes = {}
            for pos, state in self.cells.items():
                if state == 1: # Humo
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        neighbor = (pos[0] + dx, pos[1] + dy)
                        if self.get_state(neighbor) == 2 and self.board.can_move(pos, neighbor):
                            changes[pos] = 2
                            break
            # Si no hubo nuevos fuegos en esta iteración, la reacción en cadena termina
            if not changes:
                break
                
            for pos, new_state in changes.items():
                print(f"  -> FLASHOVER: El humo en {pos} se convirtió en fuego.")
                self.set_state(pos, new_state)