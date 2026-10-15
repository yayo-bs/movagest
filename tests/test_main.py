"""Pruebas de la página pública principal.

Comprueban que la portada responde y muestra su bienvenida.
"""

def test_inicio_responde_correctamente(cliente):
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert b"Bienvenido a MovaGest" in respuesta.data
