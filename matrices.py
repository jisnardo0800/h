turnos = [["Libre" for _ in range(5)] for _ in range(7)]

def mostrar_turnos():
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    print("Turnos de la semana:")
    for i, dia in enumerate(dias):
        print(f"{dia}: {turnos[i]}")

def reservar_turno(dia, horario, nombre):
    if turnos[dia][horario] == "Libre":
        turnos[dia][horario] = nombre
        print("Turno reservado con éxito.")
    else:
        print("Ese horario ya está ocupado.")

mostrar_turnos()
reservar_turno(2, 2, "Juan Pérez")
mostrar_turnos()
