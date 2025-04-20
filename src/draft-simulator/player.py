class Player:
    def __init__(self, name: str, position: str, team: str):
        self.name = name
        self.position = position
        self.team = team
        self.drafted = False
        self.drafted_by = None

    def __str__(self):
        return f"{self.name} ({self.position}, {self.team})"
