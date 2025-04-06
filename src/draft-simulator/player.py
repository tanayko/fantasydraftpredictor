class Player:
    def __init__(self, name: str, position: str, college: str, rating: float):
        self.name = name
        self.position = position
        self.college = college
        self.rating = rating
        self.drafted = False
        self.drafted_by = None
        
    def __str__(self):
        return f"{self.name} ({self.position}, {self.college}) - Rating: {self.rating}"
