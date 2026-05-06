# enum is the way to define a fixed set of names that cant be changed 
import enum
class Names(enum.Enum):
    RED = 'red'


print(Names.RED)





class Priority(enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

# Access
print(Priority.HIGH.value)  # 3
print(Priority.HIGH.name)   # "HIGH"