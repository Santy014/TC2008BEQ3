class Boundary:
    def __init__(self, boundary_type="wall"):
        self.type = boundary_type  # "wall", "door"
        
        self.hp = 2 if boundary_type == "wall" else 1 
        self.is_open = False # Solo aplica si es "door"

class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.boundaries = {}  # Aquí guardamos los muros y puertas

    def _get_edge_key(self, pos1, pos2):
        """
        Ordenar las coordenadas garantiza que ir de A->B sea exactamente el mismo muro que ir de B->A.
        """
        return tuple(sorted((pos1, pos2)))

    def add_boundary(self, pos1, pos2, boundary_type="wall"):
        """Añade un muro o puerta entre dos coordenadas."""
        key = self._get_edge_key(pos1, pos2)
        self.boundaries[key] = Boundary(boundary_type)

    def can_move(self, pos1, pos2):
        """Revisa si un agente puede caminar de pos1 a pos2."""
        key = self._get_edge_key(pos1, pos2)
        
        # Si no hay un obstáculo registrado entre estas dos celdas, el paso es libre
        if key not in self.boundaries:
            return True 

        boundary = self.boundaries[key]
        
        # Si es un muro, solo se puede pasar si sus puntos de vida son 0
        if boundary.type == "wall" and boundary.hp <= 0:
            return True
            
        # Si es una puerta, se puede pasar si está abierta o destruida
        if boundary.type == "door" and (boundary.is_open or boundary.hp <= 0):
            return True

        return False # El paso está bloqueado

    def interact_with_boundary(self, pos1, pos2, action="damage"):
        """Permite a los agentes interactuar con los muros y puertas."""
        key = self._get_edge_key(pos1, pos2)
        
        if key in self.boundaries:
            boundary = self.boundaries[key]
            
            if action == "damage" and boundary.hp > 0:
                boundary.hp -= 1
                
            elif action == "toggle_door" and boundary.type == "door":
                # Solo podemos abrir/cerrar si no está destruida
                if boundary.hp > 0: 
                    boundary.is_open = not boundary.is_open