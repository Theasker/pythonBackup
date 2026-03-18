class Usuario:
    def __init__(self, nombre, email):
        self.nombre = nombre
        self.email = email

persona = Usuario("Carlos", "carlos@ejemplo.com")

# Acceso normal (estático)
print(persona.nombre)

# Acceso con getattr (dinámico)

print(getattr(persona, "email"))

# Esto daría error: print(persona.edad)

# Esto es seguro:
print(getattr(persona, "edad", "No especificada"))
