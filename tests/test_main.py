def test_inicio_responde_correctamente(cliente):
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert b"Bienvenido a MovaGest" in respuesta.data
