"""The colony must exist before it can grow."""
from multicolony import World
w = World.create(num_colonies=3, seed=42)
assert len(w.colonies) == 3
