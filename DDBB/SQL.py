import mysql.connector

class database:
    def __init__(self):
        # Establece los detalles de conexión
        self.config = {
            'user': 'root',
            'password': 'gymtar',
            'host': '127.0.0.1',
            'database': 'gymtar',
            'raise_on_warnings': True
        }
        self.conn = None
        self.cursor = None

    def connection(self):
        try:
            # Crea una conexión a la base de datos
            self.conn = mysql.connector.connect(**self.config)
            # Crea un cursor para ejecutar consultas
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as error:
            print(f'Error al conectar a la base de datos: {error}')

    def select_name(self,id):
        # Ejecutar una consulta SELECT
        consulta = "SELECT name FROM usuarios where IdUser = %s"
        # Ejecuta la consulta con el parámetro pasado
        self.cursor.execute(consulta, (id,))
        # Obtiene los resultados
        result = self.cursor.fetchone()
        if result:
            contenido = str(result[0])
            return contenido
        else:
            return

    def disconnection(self):
        # Cierra el cursor
        self.cursor.close()
        if self.conn.is_connected():
            self.conn.close()